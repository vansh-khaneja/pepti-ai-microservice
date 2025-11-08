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
        """Fetch and merge data from Supabase tables"""
        try:
            from supabase import create_client, Client
            
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                raise ValueError("Supabase URL and Key must be configured in environment variables")
            
            # Create Supabase client exactly like the working code
            url = settings.SUPABASE_URL
            key = settings.SUPABASE_KEY
            supabase: Client = create_client(url, key)
            
            def safe_fetch(table: str) -> List[Dict]:
                """Fetch a table safely; return empty list on failure"""
                try:
                    data = supabase.table(table).select("*").execute().data
                    logger.info(f"✅ Fetched {table}: {len(data)} rows")
                    return data
                except Exception as e:
                    logger.warning(f"⚠️ Skipped {table} due to: {e}")
                    return []
            
            # Fetch tables
            peptides = safe_fetch("peptides")
            categories = safe_fetch("categories")
            benefits = safe_fetch("benefits")
            peptide_benefits = safe_fetch("peptide_benefits")
            trending = safe_fetch("trending")
            
            # Convert to DataFrames
            df_peptides = pd.DataFrame(peptides)
            df_categories = pd.DataFrame(categories)
            df_benefits = pd.DataFrame(benefits)
            df_peptide_benefits = pd.DataFrame(peptide_benefits)
            df_trending = pd.DataFrame(trending)
            
            # Merge category info
            if not df_categories.empty:
                df = df_peptides.merge(
                    df_categories, 
                    left_on="category_id", 
                    right_on="category_id", 
                    how="left", 
                    suffixes=("", "_category")
                )
            else:
                df = df_peptides
            
            # Add trending info
            if not df_trending.empty:
                df = df.merge(
                    df_trending, 
                    left_on="id", 
                    right_on="peptide_id", 
                    how="left", 
                    suffixes=("", "_trending")
                )
            
            # Add benefits if available
            if not df_peptide_benefits.empty and not df_benefits.empty:
                benefit_map = df_peptide_benefits.merge(
                    df_benefits, 
                    left_on="benefit_id", 
                    right_on="id", 
                    how="left"
                )
                benefit_grouped = benefit_map.groupby("peptide_id")["name"].apply(
                    lambda x: "; ".join(x)
                ).reset_index().rename(columns={"name": "benefits"})
                df = df.merge(
                    benefit_grouped, 
                    left_on="id", 
                    right_on="peptide_id", 
                    how="left"
                )
            
            # Clean up duplicate columns
            df.drop(columns=["peptide_id"], errors="ignore", inplace=True)
            
            # Fill NaN values with empty strings for consistency
            df = df.fillna("")
            
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
        """Build embedding text from peptide row"""
        parts = []
        
        # Name / identifiers
        name = row.get("name") or row.get("peptide_name") or ""
        if name:
            parts.append(f"Name: {name}")
        if row.get("synonyms"):
            parts.append(f"{name} Synonyms: {row['synonyms']}")
        
        # Sequence info
        if row.get("sequence"):
            parts.append(f"{name} Sequence: {row['sequence']}")
        
        # Scientific / descriptive info
        if row.get("overview"):
            parts.append(f"{name} Overview: {row['overview']}")
        if row.get("mechanism_of_action"):
            parts.append(f"{name} Mechanism of Action: {row['mechanism_of_action']}")
        if row.get("potential_research_fields"):
            parts.append(f"{name} Potential Research Fields: {row['potential_research_fields']}")
        
        # Chemical properties
        if row.get("iupac_name"):
            parts.append(f"{name} IUPAC Name: {row['iupac_name']}")
        if row.get("molecular_mass"):
            parts.append(f"{name} Molecular Mass: {row['molecular_mass']}")
        if row.get("chemical_formula"):
            parts.append(f"{name} Chemical Formula: {row['chemical_formula']}")
        
        # Benefits if available
        if row.get("benefits"):
            parts.append(f"{name} Benefits: {row['benefits']}")
        
        # Join all non-empty parts
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
                payload = {
                    "name": row.get("name", ""),
                    "slug": row.get("slug", ""),
                    "sequence": row.get("sequence", ""),
                    "synonyms": row.get("synonyms", ""),
                    "overview": row.get("overview", ""),
                    "mechanism_of_action": row.get("mechanism_of_action", ""),
                    "iupac_name": row.get("iupac_name", ""),
                    "molecular_mass": row.get("molecular_mass", ""),
                    "potential_research_fields": row.get("potential_research_fields", ""),
                    "chemical_formula": row.get("chemical_formula", ""),
                    "benefits": row.get("benefits", ""),
                    "embedding_text": embed_text,
                }
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
    
    def sync_peptides(self):
        """Main sync function: fetch, compare, and upload new peptides"""
        try:
            logger.info("🔄 Starting peptide sync from Supabase...")
            
            # Step 1: Load current CSV data for comparison (before fetching new data)
            df_old = self.get_current_csv_data()
            
            # Step 2: Fetch new data from Supabase
            df_new = self.fetch_from_supabase()
            
            if df_new.empty:
                logger.warning("⚠️ No peptides found in Supabase")
                return
            
            # Step 3: Find new peptides by comparing old and new data
            df_new_peptides = self.find_new_peptides(df_old, df_new)
            
            # Step 4: Save new CSV (overwrites old one)
            self.save_csv(df_new)
            
            # Step 5: Delete previous CSV if it exists (cleanup)
            if self.previous_csv.exists():
                self.previous_csv.unlink()
                logger.info("✅ Deleted previous CSV backup")
            
            # Step 6: Upload new peptides to Qdrant (if any)
            if df_new_peptides.empty:
                logger.info("✅ No new peptides to sync")
                return
            
            # Log if this is initial sync (no CSV existed)
            if df_old.empty:
                logger.info(f"🚀 Initial sync: Uploading all {len(df_new_peptides)} peptides to Qdrant")
            else:
                logger.info(f"🔄 Incremental sync: Uploading {len(df_new_peptides)} new peptides to Qdrant")
            
            self.upload_to_qdrant(df_new_peptides)
            
            logger.info("✅ Peptide sync completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Peptide sync failed: {e}")
            raise

