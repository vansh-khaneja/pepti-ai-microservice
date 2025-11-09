"""
Service for syncing peptides from Supabase to Qdrant vector database
"""
import os
import pandas as pd
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.core.config import settings
from app.utils.helpers import logger
from app.repositories.repository_manager import repository_manager


class SupabaseSyncService:
    """Service for syncing peptides from Supabase"""
    
    def __init__(self):
        self.csv_dir = Path("data")
        self.csv_dir.mkdir(exist_ok=True)
        self.current_csv = self.csv_dir / "peptides_full_info.csv"
        self.previous_csv = self.csv_dir / "peptides_full_info_previous.csv"
        self.embed_model = "text-embedding-3-large"
        self.batch_size = 50
        self.vector_dim = 3072
    
    def fetch_from_supabase(self) -> pd.DataFrame:
        """
        Extract all peptide-related information from the database.
        
        Tables to extract:
        - peptides (core table)
        - categories (linked via category_id)
        - benefits (via peptide_benefits)
        - peptide_benefits (junction table)
        - administration_methods (via peptide_protocols)
        - peptide_protocols (junction table)
        - protocol_dosages (linked to protocols)
        - dosages (linked via protocol_dosages)
        - schedules (linked via protocol_dosages)
        - protocol_dosage_benefits (junction table)
        - side_effects (via protocol_dosage_side_effects)
        - protocol_dosage_side_effects (junction table)
        """
        try:
            from supabase import create_client, Client
            
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                raise ValueError("Supabase URL and Key must be configured in environment variables")
            
            # Create Supabase client
            url = settings.SUPABASE_URL
            key = settings.SUPABASE_KEY
            supabase: Client = create_client(url, key)
            
            def safe_fetch(table: str, select_query: str = "*") -> List[Dict]:
                """Fetch a table safely; return empty list on failure"""
                try:
                    data = supabase.table(table).select(select_query).execute().data
                    logger.info(f"✅ Fetched {table}: {len(data)} rows")
                    return data
                except Exception as e:
                    logger.warning(f"⚠️ Skipped {table} due to: {e}")
                    return []
            
            logger.info("=" * 60)
            logger.info("FETCHING CORE TABLES")
            logger.info("=" * 60)
            
            # Core peptide data
            peptides = safe_fetch("peptides")
            categories = safe_fetch("categories")
            
            logger.info("=" * 60)
            logger.info("FETCHING BENEFITS & SIDE EFFECTS")
            logger.info("=" * 60)
            
            # Benefits system
            benefits = safe_fetch("benefits")
            peptide_benefits = safe_fetch("peptide_benefits")
            
            # Side effects
            side_effects = safe_fetch("side_effects")
            
            logger.info("=" * 60)
            logger.info("FETCHING PROTOCOL SYSTEM")
            logger.info("=" * 60)
            
            # Protocol system
            administration_methods = safe_fetch("administration_methods")
            peptide_protocols = safe_fetch("peptide_protocols")
            protocol_dosages = safe_fetch("protocol_dosages")
            dosages = safe_fetch("dosages")
            schedules = safe_fetch("schedules")
            
            # Protocol-specific relationships
            protocol_dosage_benefits = safe_fetch("protocol_dosage_benefits")
            protocol_dosage_side_effects = safe_fetch("protocol_dosage_side_effects")
            
            logger.info("=" * 60)
            logger.info("BUILDING COMPREHENSIVE DATASET")
            logger.info("=" * 60)
            
            # Convert to DataFrames
            df_peptides = pd.DataFrame(peptides)
            
            if df_peptides.empty:
                logger.warning("❌ No peptides found!")
                return pd.DataFrame()
            
            # === 1. MERGE CATEGORIES ===
            df_categories = pd.DataFrame(categories)
            if not df_categories.empty:
                df = df_peptides.merge(
                    df_categories, 
                    left_on="category_id", 
                    right_on="category_id", 
                    how="left", 
                    suffixes=("", "_cat")
                )
                df.rename(columns={
                    "category_name": "category",
                    "icon_cat": "category_icon",
                    "color_bg_cat": "category_color_bg",
                    "color_text_cat": "category_color_text"
                }, inplace=True)
            else:
                df = df_peptides
            
            # === 2. AGGREGATE GENERAL BENEFITS ===
            df_benefits = pd.DataFrame(benefits)
            df_peptide_benefits = pd.DataFrame(peptide_benefits)
            
            if not df_peptide_benefits.empty and not df_benefits.empty:
                # Join peptide_benefits with benefits
                pb_merged = df_peptide_benefits.merge(
                    df_benefits, 
                    left_on="benefit_id", 
                    right_on="id", 
                    how="left",
                    suffixes=("_pb", "_b")
                )
                
                # Aggregate benefits per peptide
                benefit_agg = pb_merged.groupby("peptide_id").agg({
                    "name": lambda x: " | ".join(x.dropna().astype(str)),
                    "category": lambda x: " | ".join(x.dropna().astype(str)),
                    "evidence_level": lambda x: " | ".join(x.dropna().astype(str)),
                    "general_potency": lambda x: " | ".join(x.dropna().astype(str)),
                    "description_pb": lambda x: " | ".join(x.dropna().astype(str))
                }).reset_index()
                
                benefit_agg.columns = ["peptide_id", "benefits_list", "benefit_categories", 
                                       "benefit_evidence_levels", "benefit_potencies", "benefit_descriptions"]
                
                df = df.merge(benefit_agg, left_on="id", right_on="peptide_id", how="left")
            
            # === 3. AGGREGATE PROTOCOLS ===
            df_protocols = pd.DataFrame(peptide_protocols)
            df_admin_methods = pd.DataFrame(administration_methods)
            
            if not df_protocols.empty and not df_admin_methods.empty:
                protocols_merged = df_protocols.merge(
                    df_admin_methods,
                    left_on="administration_method_id",
                    right_on="id",
                    how="left",
                    suffixes=("_prot", "_admin")
                )
                
                # Aggregate protocols per peptide
                protocol_agg = protocols_merged.groupby("peptide_id").agg({
                    "name_admin": lambda x: " | ".join(x.dropna().astype(str)),
                    "description_admin": lambda x: " | ".join(x.dropna().astype(str)),
                    "is_recommended": lambda x: " | ".join(x.astype(str))
                }).reset_index()
                
                protocol_agg.columns = ["peptide_id", "admin_methods", "admin_descriptions", "recommended_methods"]
                
                df = df.merge(protocol_agg, left_on="id", right_on="peptide_id", how="left")
                
                # === 4. AGGREGATE DOSAGES & SCHEDULES ===
                df_protocol_dosages = pd.DataFrame(protocol_dosages)
                df_dosages = pd.DataFrame(dosages)
                df_schedules = pd.DataFrame(schedules)
                
                if not df_protocol_dosages.empty:
                    # Join protocol_dosages with protocols to get peptide_id
                    dosage_chain = df_protocol_dosages.merge(
                        df_protocols[["id", "peptide_id"]],
                        left_on="protocol_id",
                        right_on="id",
                        how="left",
                        suffixes=("", "_prot_temp")
                    )
                    
                    # Add dosage details
                    if not df_dosages.empty:
                        dosage_chain = dosage_chain.merge(
                            df_dosages,
                            left_on="dosage_id",
                            right_on="id",
                            how="left",
                            suffixes=("", "_dose")
                        )
                    
                    # Add schedule details
                    if not df_schedules.empty:
                        dosage_chain = dosage_chain.merge(
                            df_schedules,
                            left_on="schedule_id",
                            right_on="id",
                            how="left",
                            suffixes=("", "_sched")
                        )
                    
                    # Aggregate dosage information per peptide
                    dosage_agg = dosage_chain.groupby("peptide_id").agg({
                        "name": lambda x: " | ".join(x.dropna().astype(str)),
                        "amount": lambda x: " | ".join(x.dropna().astype(str)),
                        "unit": lambda x: " | ".join(x.dropna().astype(str)),
                        "frequency": lambda x: " | ".join(x.dropna().astype(str)),
                        "timing": lambda x: " | ".join(x.dropna().astype(str)),
                        "duration": lambda x: " | ".join(x.dropna().astype(str))
                    }).reset_index()
                    
                    dosage_agg.columns = ["peptide_id", "dosage_names", "dosage_amounts", 
                                         "dosage_units", "frequencies", "timings", "durations"]
                    
                    df = df.merge(dosage_agg, left_on="id", right_on="peptide_id", how="left")
            
            # === 5. AGGREGATE SIDE EFFECTS ===
            df_pdse = pd.DataFrame(protocol_dosage_side_effects)
            df_side_effects = pd.DataFrame(side_effects)
            
            if not df_pdse.empty and not df_side_effects.empty and not df_protocol_dosages.empty:
                # Chain: protocol_dosage_side_effects -> protocol_dosages -> protocols -> peptides
                se_chain = df_pdse.merge(
                    df_protocol_dosages[["id", "protocol_id"]],
                    left_on="protocol_dosage_id",
                    right_on="id",
                    how="left",
                    suffixes=("_pdse", "_pd")
                )
                
                se_chain = se_chain.merge(
                    df_protocols[["id", "peptide_id"]],
                    left_on="protocol_id",
                    right_on="id",
                    how="left",
                    suffixes=("", "_prot_temp2")
                )
                
                se_chain = se_chain.merge(
                    df_side_effects,
                    left_on="side_effect_id",
                    right_on="id",
                    how="left",
                    suffixes=("", "_se")
                )
                
                # Aggregate side effects per peptide
                se_agg = se_chain.groupby("peptide_id").agg({
                    "name": lambda x: " | ".join(x.dropna().astype(str)),
                    "severity_level": lambda x: " | ".join(x.dropna().astype(str)),
                    "likelihood": lambda x: " | ".join(x.dropna().astype(str)),
                    "category": lambda x: " | ".join(x.dropna().astype(str))
                }).reset_index()
                
                se_agg.columns = ["peptide_id", "side_effects_list", "side_effect_severities", 
                                 "side_effect_likelihoods", "side_effect_categories"]
                
                df = df.merge(se_agg, left_on="id", right_on="peptide_id", how="left")
            
            # === CLEANUP ===
            # Drop duplicate peptide_id columns
            peptide_id_cols = [col for col in df.columns if col.startswith("peptide_id")]
            df.drop(columns=peptide_id_cols, errors="ignore", inplace=True)
            
            # Fill NaN values with empty strings for consistency
            df = df.fillna("")
            
            logger.info(f"✅ Final dataset shape: {df.shape}")
            logger.info(f"✅ Columns: {df.shape[1]}")
            logger.info(f"✅ Merged data: {len(df)} peptides")
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch from Supabase: {e}")
            raise
    
    def save_csv(self, df: pd.DataFrame):
        """Save DataFrame to CSV, overwriting previous version"""
        try:
            # Save new CSV (overwrites if exists)
            df.to_csv(self.current_csv, index=False)
            logger.info(f"✅ Saved CSV: {self.current_csv} with {len(df)} rows")
            
        except Exception as e:
            logger.error(f"❌ Failed to save CSV: {e}")
            raise
    
    def get_current_csv_data(self) -> pd.DataFrame:
        """Get current CSV data if it exists, for comparison"""
        try:
            if self.current_csv.exists():
                df = pd.read_csv(self.current_csv, dtype=str).fillna("")
                logger.info(f"✅ Loaded current CSV with {len(df)} rows for comparison")
                return df
            else:
                logger.info("No current CSV found")
                return pd.DataFrame()
        except Exception as e:
            logger.warning(f"⚠️ Failed to load current CSV for comparison: {e}")
            return pd.DataFrame()
    
    def find_new_peptides(self, df_old: pd.DataFrame, df_new: pd.DataFrame) -> pd.DataFrame:
        """Compare old and new DataFrames to find new peptides"""
        try:
            # If no old data (no CSV exists), database is empty - push all peptides
            if df_old.empty:
                logger.info("📦 No CSV found - database is empty. Will upload ALL peptides to Qdrant")
                logger.info(f"📦 Total peptides to upload: {len(df_new)}")
                return df_new
            
            if df_new.empty:
                logger.info("No new data to compare")
                return pd.DataFrame()
            
            # Use 'id' column for comparison (or 'name' if 'id' doesn't exist)
            id_column = "id" if "id" in df_new.columns else "name"
            
            if id_column not in df_new.columns:
                logger.warning(f"ID column '{id_column}' not found, using all rows as new")
                return df_new
            
            # Find new peptides (in new but not in old)
            new_ids = set(df_new[id_column].astype(str))
            old_ids = set(df_old[id_column].astype(str))
            new_peptide_ids = new_ids - old_ids
            
            if not new_peptide_ids:
                logger.info("✅ No new peptides found")
                return pd.DataFrame()
            
            # Filter new peptides
            df_new_peptides = df_new[df_new[id_column].astype(str).isin(new_peptide_ids)]
            logger.info(f"✅ Found {len(df_new_peptides)} new peptides")
            return df_new_peptides
            
        except Exception as e:
            logger.error(f"❌ Failed to find new peptides: {e}")
            # Return empty DataFrame on error
            return pd.DataFrame()
    
    def build_embed_text(self, row: Dict[str, Any]) -> str:
        """
        Build rich embedding text from comprehensive peptide data.
        Each field is prefixed with the peptide name for better context.
        Example: "BPC-157 Overview: ..." instead of just "Overview: ..."
        """
        parts = []
        
        # Get peptide name for prefixing
        name = row.get("name") or row.get("peptide_name") or ""
        
        # === BASIC IDENTIFIERS ===
        if name:
            parts.append(f"Name: {name}")
        
        if row.get("slug"):
            parts.append(f"{name} Slug: {row['slug']}")
        
        if row.get("synonyms"):
            parts.append(f"{name} Synonyms: {row['synonyms']}")
        
        # === CATEGORY ===
        if row.get("category"):
            parts.append(f"{name} Category: {row['category']}")
        
        # === SCIENTIFIC INFO ===
        if row.get("sequence"):
            parts.append(f"{name} Sequence: {row['sequence']}")
        
        if row.get("overview"):
            parts.append(f"{name} Overview: {row['overview']}")
        
        if row.get("mechanism_of_action"):
            parts.append(f"{name} Mechanism of Action: {row['mechanism_of_action']}")
        
        if row.get("potential_research_fields"):
            parts.append(f"{name} Research Fields: {row['potential_research_fields']}")
        
        # === CHEMICAL PROPERTIES ===
        if row.get("iupac_name"):
            parts.append(f"{name} IUPAC Name: {row['iupac_name']}")
        
        if row.get("molecular_mass"):
            parts.append(f"{name} Molecular Mass: {row['molecular_mass']}")
        
        if row.get("chemical_formula"):
            parts.append(f"{name} Chemical Formula: {row['chemical_formula']}")
        
        # === BENEFITS ===
        if row.get("benefits_list"):
            parts.append(f"{name} Benefits: {row['benefits_list']}")
        
        if row.get("benefit_categories"):
            parts.append(f"{name} Benefit Categories: {row['benefit_categories']}")
        
        if row.get("benefit_evidence_levels"):
            parts.append(f"{name} Evidence Levels: {row['benefit_evidence_levels']}")
        
        if row.get("benefit_potencies"):
            parts.append(f"{name} Potencies: {row['benefit_potencies']}")
        
        if row.get("benefit_descriptions"):
            parts.append(f"{name} Benefit Descriptions: {row['benefit_descriptions']}")
        
        # === ADMINISTRATION & PROTOCOLS ===
        if row.get("admin_methods"):
            parts.append(f"{name} Administration Methods: {row['admin_methods']}")
        
        if row.get("admin_descriptions"):
            parts.append(f"{name} Administration Details: {row['admin_descriptions']}")
        
        if row.get("recommended_methods"):
            parts.append(f"{name} Recommended Methods: {row['recommended_methods']}")
        
        # === DOSAGES & SCHEDULES ===
        if row.get("dosage_names"):
            parts.append(f"{name} Dosage Names: {row['dosage_names']}")
        
        if row.get("dosage_amounts"):
            parts.append(f"{name} Dosage Amounts: {row['dosage_amounts']}")
        
        if row.get("dosage_units"):
            parts.append(f"{name} Dosage Units: {row['dosage_units']}")
        
        if row.get("frequencies"):
            parts.append(f"{name} Frequencies: {row['frequencies']}")
        
        if row.get("timings"):
            parts.append(f"{name} Timings: {row['timings']}")
        
        if row.get("durations"):
            parts.append(f"{name} Durations: {row['durations']}")
        
        # === SIDE EFFECTS ===
        if row.get("side_effects_list"):
            parts.append(f"{name} Side Effects: {row['side_effects_list']}")
        
        if row.get("side_effect_severities"):
            parts.append(f"{name} Side Effect Severities: {row['side_effect_severities']}")
        
        if row.get("side_effect_likelihoods"):
            parts.append(f"{name} Side Effect Likelihoods: {row['side_effect_likelihoods']}")
        
        if row.get("side_effect_categories"):
            parts.append(f"{name} Side Effect Categories: {row['side_effect_categories']}")
        
        # === CITATIONS ===
        if row.get("citations"):
            parts.append(f"{name} Citations: {row['citations']}")
        
        # Join all non-empty parts into one text block
        return "\n".join(parts)
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batches - direct API call without cost tracking"""
        all_embeddings = []
        
        from app.core.config import settings
        import requests
        
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            try:
                # Direct API call to OpenAI - no cost tracking
                payload = {
                    "input": batch,
                    "model": self.embed_model
                }
                
                response = requests.post(
                    "https://api.openai.com/v1/embeddings",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    embeddings = [item["embedding"] for item in data["data"]]
                    all_embeddings.extend(embeddings)
                    logger.info(f"✅ Generated embeddings for batch {i//self.batch_size + 1} ({len(batch)} texts)")
                else:
                    raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
                
            except Exception as e:
                logger.error(f"❌ Failed to generate embeddings for batch: {e}")
                raise
        
        return all_embeddings
    
    def upload_to_qdrant(self, df_new: pd.DataFrame):
        """Upload new peptides to Qdrant"""
        try:
            if df_new.empty:
                logger.info("No new peptides to upload")
                return
            
            vector_repo = repository_manager.vector_store
            
            # Build embedding texts
            rows = df_new.to_dict(orient="records")
            texts = [self.build_embed_text(row) for row in rows]
            
            logger.info(f"🔄 Generating embeddings for {len(texts)} new peptides...")
            vectors = self.generate_embeddings_batch(texts)
            
            # Build points and upload
            from qdrant_client.models import PointStruct
            
            points = []
            for idx, (row, vector, embed_text) in enumerate(zip(rows, vectors, texts)):
                point_id = str(uuid.uuid4())
                
                # Comprehensive payload with all peptide information
                payload = {
                    # === CORE INFO ===
                    "peptide_id": row.get("id", ""),
                    "name": row.get("name", ""),
                    "slug": row.get("slug", ""),
                    "category": row.get("category", ""),
                    "category_icon": row.get("category_icon", ""),
                    
                    # === SCIENTIFIC DATA ===
                    "sequence": row.get("sequence", ""),
                    "synonyms": row.get("synonyms", ""),
                    "overview": row.get("overview", ""),
                    "mechanism_of_action": row.get("mechanism_of_action", ""),
                    "potential_research_fields": row.get("potential_research_fields", ""),
                    
                    # === CHEMICAL PROPERTIES ===
                    "iupac_name": row.get("iupac_name", ""),
                    "molecular_mass": row.get("molecular_mass", ""),
                    "chemical_formula": row.get("chemical_formula", ""),
                    "two_d_structure_photo": row.get("two_d_structure_photo", ""),
                    
                    # === BENEFITS ===
                    "benefits_list": row.get("benefits_list", ""),
                    "benefit_categories": row.get("benefit_categories", ""),
                    "benefit_evidence_levels": row.get("benefit_evidence_levels", ""),
                    "benefit_potencies": row.get("benefit_potencies", ""),
                    "benefit_descriptions": row.get("benefit_descriptions", ""),
                    
                    # === ADMINISTRATION ===
                    "admin_methods": row.get("admin_methods", ""),
                    "admin_descriptions": row.get("admin_descriptions", ""),
                    "recommended_methods": row.get("recommended_methods", ""),
                    
                    # === DOSAGES & SCHEDULES ===
                    "dosage_names": row.get("dosage_names", ""),
                    "dosage_amounts": row.get("dosage_amounts", ""),
                    "dosage_units": row.get("dosage_units", ""),
                    "frequencies": row.get("frequencies", ""),
                    "timings": row.get("timings", ""),
                    "durations": row.get("durations", ""),
                    
                    # === SIDE EFFECTS ===
                    "side_effects_list": row.get("side_effects_list", ""),
                    "side_effect_severities": row.get("side_effect_severities", ""),
                    "side_effect_likelihoods": row.get("side_effect_likelihoods", ""),
                    "side_effect_categories": row.get("side_effect_categories", ""),
                    
                    # === METADATA ===
                    "citations": row.get("citations", ""),
                    "created_at": row.get("created_at", ""),
                    "updated_at": row.get("updated_at", ""),
                    
                    # === EMBEDDING TEXT ===
                    "embedding_text": embed_text,
                }
                
                # Remove empty fields to keep payload clean
                payload = {k: v for k, v in payload.items() if v and v != ""}
                
                points.append(PointStruct(id=point_id, vector=vector, payload=payload))
            
            # Upload in smaller chunks with retry logic
            upsert_chunk = 20  # Reduced chunk size to avoid timeouts
            max_retries = 3
            base_retry_delay = 2  # seconds
            
            import time
            for i in range(0, len(points), upsert_chunk):
                chunk = points[i:i + upsert_chunk]
                chunk_num = i//upsert_chunk + 1
                total_chunks = (len(points) + upsert_chunk - 1) // upsert_chunk
                
                # Retry logic for each chunk
                retry_delay = base_retry_delay
                for attempt in range(1, max_retries + 1):
                    try:
                        # Use wait=False for faster uploads (non-blocking)
                        # The data will be eventually consistent
                        vector_repo.client.upsert(
                            collection_name=vector_repo.collection_name,
                            points=chunk,
                            wait=False  # Non-blocking for faster uploads
                        )
                        logger.info(f"✅ Uploaded chunk {chunk_num}/{total_chunks} ({len(chunk)} peptides)")
                        break  # Success, move to next chunk
                    except Exception as e:
                        if attempt == max_retries:
                            logger.error(f"❌ Failed to upload chunk {chunk_num} after {max_retries} attempts: {e}")
                            raise
                        else:
                            logger.warning(f"⚠️ Upload attempt {attempt}/{max_retries} failed for chunk {chunk_num}, retrying in {retry_delay}s...")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
            
            logger.info(f"✅ Successfully uploaded {len(points)} new peptides to Qdrant")
            
        except Exception as e:
            logger.error(f"❌ Failed to upload to Qdrant: {e}")
            raise
    
    def get_qdrant_peptide_names(self) -> set:
        """Get all peptide names from Qdrant collection"""
        try:
            vector_repo = repository_manager.vector_store
            names = vector_repo.get_all_peptide_names()
            return names
        except Exception as e:
            logger.warning(f"⚠️ Failed to get Qdrant peptide names: {e}")
            return set()
    
    def startup_sync_verify(self):
        """
        Startup sync verification: 
        1. Fetch data from Supabase and create CSV
        2. Extract peptide names from Supabase data
        3. Extract peptide names from Qdrant (by scrolling through all points)
        4. Find peptides in Supabase but not in Qdrant
        5. Push only missing peptides to Qdrant
        This only runs at startup
        """
        try:
            logger.info("=" * 60)
            logger.info("🚀 STARTUP SYNC VERIFICATION")
            logger.info("=" * 60)
            
            # Step 1: Fetch data from Supabase
            logger.info("📥 Step 1: Fetching data from Supabase...")
            df_new = self.fetch_from_supabase()
            
            if df_new.empty:
                logger.warning("⚠️ No peptides found in Supabase")
                return
            
            # Step 2: Save to CSV
            logger.info("💾 Step 2: Saving data to CSV...")
            self.save_csv(df_new)
            
            # Step 3: Extract peptide names from Supabase
            supabase_names = set()
            if "name" in df_new.columns:
                supabase_names = set(df_new["name"].dropna().astype(str).str.strip())
            else:
                logger.warning("⚠️ 'name' column not found in Supabase data")
                return
            
            logger.info(f"📊 Step 3: Supabase contains {len(supabase_names)} unique peptide names")
            
            # Step 4: Extract peptide names from Qdrant
            logger.info("📊 Step 4: Extracting peptide names from Qdrant...")
            qdrant_names = self.get_qdrant_peptide_names()
            logger.info(f"📊 Qdrant contains {len(qdrant_names)} unique peptide names")
            
            # Step 5: Find missing peptides (in Supabase but not in Qdrant)
            missing_names = supabase_names - qdrant_names
            
            # Step 6: Find extra peptides (in Qdrant but not in Supabase)
            extra_names = qdrant_names - supabase_names
            
            logger.info("=" * 60)
            logger.info(f"📊 Name Comparison:")
            logger.info(f"   Supabase: {len(supabase_names)} peptides")
            logger.info(f"   Qdrant: {len(qdrant_names)} peptides")
            logger.info(f"   Missing in Qdrant: {len(missing_names)} peptides")
            logger.info(f"   Extra in Qdrant: {len(extra_names)} peptides")
            logger.info("=" * 60)
            
            # Step 7: Delete extra peptides from Qdrant (if any)
            if extra_names:
                logger.warning(f"⚠️ Found {len(extra_names)} peptides in Qdrant that are not in Supabase")
                logger.info(f"📋 Extra peptides to delete: {', '.join(list(extra_names)[:10])}{'...' if len(extra_names) > 10 else ''}")
                
                vector_repo = repository_manager.vector_store
                deleted_count = vector_repo.delete_by_names(extra_names)
                logger.info(f"🗑️ Deleted {deleted_count} extra peptides from Qdrant")
            
            # Step 8: Upload missing peptides to Qdrant (if any)
            if not missing_names:
                if not extra_names:
                    logger.info("✅ All peptides are in sync! No changes needed.")
                else:
                    logger.info("✅ Cleanup completed. All Supabase peptides are in Qdrant.")
                return
            
            logger.warning(f"⚠️ Found {len(missing_names)} peptides in Supabase that are missing in Qdrant")
            logger.info(f"📋 Missing peptides: {', '.join(list(missing_names)[:10])}{'...' if len(missing_names) > 10 else ''}")
            
            # Filter DataFrame to only include missing peptides
            df_missing = df_new[df_new["name"].astype(str).str.strip().isin(missing_names)]
            
            logger.info(f"🔄 Pushing {len(df_missing)} missing peptides to Qdrant...")
            
            # Upload only missing peptides
            self.upload_to_qdrant(df_missing)
            
            logger.info("✅ Sync completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Startup sync verification failed: {e}")
            raise
    
    def sync_peptides(self):
        """
        Main sync function: fetch from Supabase, compare with Qdrant, and upload missing peptides
        Uses direct name comparison with Qdrant instead of CSV comparison for reliability
        """
        try:
            logger.info("🔄 Starting peptide sync from Supabase...")
            
            # Step 1: Fetch new data from Supabase
            logger.info("📥 Step 1: Fetching data from Supabase...")
            df_new = self.fetch_from_supabase()
            
            if df_new.empty:
                logger.warning("⚠️ No peptides found in Supabase")
                return
            
            # Step 2: Extract peptide names from Supabase
            supabase_names = set()
            if "name" in df_new.columns:
                supabase_names = set(df_new["name"].dropna().astype(str).str.strip())
            else:
                logger.warning("⚠️ 'name' column not found in Supabase data")
                return
            
            logger.info(f"📊 Step 2: Supabase contains {len(supabase_names)} unique peptide names")
            
            # Step 3: Extract peptide names from Qdrant (direct comparison)
            logger.info("📊 Step 3: Extracting peptide names from Qdrant...")
            qdrant_names = self.get_qdrant_peptide_names()
            logger.info(f"📊 Qdrant contains {len(qdrant_names)} unique peptide names")
            
            # Step 4: Find missing peptides (in Supabase but not in Qdrant)
            missing_names = supabase_names - qdrant_names
            
            # Step 5: Find extra peptides (in Qdrant but not in Supabase)
            extra_names = qdrant_names - supabase_names
            
            logger.info("=" * 60)
            logger.info(f"📊 Name Comparison:")
            logger.info(f"   Supabase: {len(supabase_names)} peptides")
            logger.info(f"   Qdrant: {len(qdrant_names)} peptides")
            logger.info(f"   Missing in Qdrant: {len(missing_names)} peptides")
            logger.info(f"   Extra in Qdrant: {len(extra_names)} peptides")
            logger.info("=" * 60)
            
            # Step 6: Save CSV for reference (but don't use it for comparison)
            logger.info("💾 Step 6: Saving data to CSV for reference...")
            self.save_csv(df_new)
            
            # Step 7: Delete extra peptides from Qdrant (if any)
            if extra_names:
                logger.warning(f"⚠️ Found {len(extra_names)} peptides in Qdrant that are not in Supabase")
                logger.info(f"📋 Extra peptides to delete: {', '.join(list(extra_names)[:10])}{'...' if len(extra_names) > 10 else ''}")
                
                vector_repo = repository_manager.vector_store
                deleted_count = vector_repo.delete_by_names(extra_names)
                logger.info(f"🗑️ Deleted {deleted_count} extra peptides from Qdrant")
            
            # Step 8: Upload missing peptides to Qdrant (if any)
            if not missing_names:
                if not extra_names:
                    logger.info("✅ All peptides are in sync! No changes needed.")
                else:
                    logger.info("✅ Cleanup completed. All Supabase peptides are in Qdrant.")
                return
            
            logger.info(f"🔄 Found {len(missing_names)} peptides in Supabase that are missing in Qdrant")
            logger.info(f"📋 Missing peptides: {', '.join(list(missing_names)[:10])}{'...' if len(missing_names) > 10 else ''}")
            
            # Filter DataFrame to only include missing peptides
            df_missing = df_new[df_new["name"].astype(str).str.strip().isin(missing_names)]
            
            logger.info(f"🔄 Uploading {len(df_missing)} missing peptides to Qdrant...")
            self.upload_to_qdrant(df_missing)
            
            logger.info("✅ Peptide sync completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Peptide sync failed: {e}")
            raise

