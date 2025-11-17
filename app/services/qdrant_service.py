import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import settings
from app.models.peptide import PeptidePayload
from app.utils.helpers import logger

class QdrantService:
    # Class-level flag to ensure heavy collection/index checks happen only once per process
    _initialized: bool = False
    def __init__(self):
        """Initialize Qdrant client"""
        try:
            # Parse the Qdrant URL to extract host and port
            from urllib.parse import urlparse
            parsed_url = urlparse(settings.QDRANT_URL)
            
            # Initialize Qdrant client with URL
            if settings.QDRANT_API_KEY:
                self.client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY
                )
            else:
                self.client = QdrantClient(
                    url=settings.QDRANT_URL
                )
            
            self.collection_name = settings.PEPTIDE_COLLECTION
            # Match OpenAI text-embedding-3-large default dimension (3072)
            self.vector_size = 3072
            if not QdrantService._initialized:
                self._ensure_collection_exists()
                QdrantService._initialized = True
            logger.info("Qdrant service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant service: {str(e)}")
            raise

    def _ensure_collection_exists(self):
        """Ensure the peptides collection exists, create if it doesn't"""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                
                # Create index on the name field for efficient searching
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="name",
                    field_schema="keyword"
                )
                
                logger.info(f"Collection {self.collection_name} created successfully with name index")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
                # Validate collection vector size and warn if mismatch
                try:
                    info = self.client.get_collection(self.collection_name)
                    actual = getattr(getattr(info, "vectors_count", None), "value", None)
                    # get_collection schema differs by client versions; try to fetch vector params
                    params = getattr(info, "config", None) or getattr(info, "status", None)
                    # Fall back to making a lightweight assumption if structure isn't accessible
                except Exception:
                    params = None
                try:
                    # Newer clients: info.vectors contains parameter
                    vectors_param = getattr(info, "vectors", None)
                    actual_size = getattr(vectors_param, "size", None)
                except Exception:
                    actual_size = None
                if actual_size and actual_size != self.vector_size:
                    logger.warning(
                        f"Qdrant collection dimension mismatch: actual={actual_size}, expected={self.vector_size}. "
                        "Consider recreating the collection with the correct dimension or migrating vectors."
                    )
                
                # Always try to create the name index on existing collections
                # This handles cases where the collection exists but index is missing
                try:
                    logger.info("Ensuring name index exists on existing collection")
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name="name",
                        field_schema="keyword"
                    )
                    logger.info("Name index created/verified successfully")
                except Exception as index_error:
                    # If index already exists, this is fine
                    if "already exists" in str(index_error).lower():
                        logger.info("Name index already exists")
                    else:
                        logger.warning(f"Could not create name index: {str(index_error)}")
                
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {str(e)}")
            raise

    def ensure_name_index(self):
        """Ensure the name index exists, create if it doesn't"""
        try:
            logger.info("Ensuring name index exists")
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="name",
                field_schema="keyword"
            )
            logger.info("Name index created/verified successfully")
        except Exception as e:
            # If index already exists, this is fine
            if "already exists" in str(e).lower():
                logger.info("Name index already exists")
            else:
                logger.error(f"Error ensuring name index exists: {str(e)}")
                raise

    def store_peptide(self, peptide: PeptidePayload, embedding: List[float]) -> str:
        """Store a peptide in Qdrant with its embedding"""
        try:
            # Generate UUID for Qdrant point ID (required by Qdrant)
            import uuid
            point_id = str(uuid.uuid4())
            
            # Create the point structure
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "name": peptide.name,
                    "overview": peptide.overview,
                    "mechanism_of_actions": peptide.mechanism_of_actions,
                    "potential_research_fields": peptide.potential_research_fields,
                    "created_at": peptide.created_at.isoformat(),
                    "text_content": peptide.to_text()
                }
            )
            
            # Insert the point with simple retry for transient 5xx errors (e.g., 502 Bad Gateway)
            import time
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    self.client.upsert(
                        collection_name=self.collection_name,
                        points=[point]
                    )
                    break
                except Exception as upsert_error:
                    message = str(upsert_error)
                    is_transient = any(token in message for token in ["502", "503", "Bad Gateway", "Service Unavailable", "Gateway"])
                    if is_transient and attempt < max_attempts:
                        sleep_seconds = 1.5 * attempt
                        logger.warning(f"Qdrant upsert attempt {attempt} failed with transient error; retrying in {sleep_seconds:.1f}s: {message}")
                        time.sleep(sleep_seconds)
                        continue
                    raise
            
            logger.info(f"Peptide '{peptide.name}' stored successfully in Qdrant")
            return point_id
            
        except Exception as e:
            logger.error(f"Error storing peptide in Qdrant: {str(e)}")
            raise

    def delete_peptide(self, peptide_name: str) -> bool:
        """Delete a peptide by name"""
        try:
            # Search for the peptide by name in payload
            search_results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter={
                    "must": [
                        {
                            "key": "name",
                            "match": {"value": peptide_name}
                        }
                    ]
                },
                limit=1
            )
            
            if not search_results[0]:
                logger.warning(f"Peptide '{peptide_name}' not found")
                return False
            
            # Get the point ID from the search result
            point_id = search_results[0][0].id
            
            # Delete the point using its ID
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[point_id]
            )
            
            logger.info(f"Peptide '{peptide_name}' deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting peptide from Qdrant: {str(e)}")
            raise

    def get_peptide_by_name(self, peptide_name: str) -> Optional[Dict[str, Any]]:
        """Get peptide data by name from payload"""
        try:
            # Search for the peptide by name in payload
            search_results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter={
                    "must": [
                        {
                            "key": "name",
                            "match": {"value": peptide_name}
                        }
                    ]
                },
                limit=1,
                with_vectors=True  # Explicitly request vectors
            )
            
            if not search_results[0]:
                logger.warning(f"Peptide '{peptide_name}' not found")
                return None
            
            # Get the first result
            point = search_results[0][0]
            
            return {
                "id": point.id,
                "payload": point.payload,
                "vector": point.vector
            }
            
        except Exception as e:
            logger.error(f"Error retrieving peptide from Qdrant: {str(e)}")
            raise

    def search_peptides(self, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """Search for peptides using vector similarity"""
        try:
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit
            )
            
            peptides = []
            for result in search_results:
                peptides.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload
                })
            
            logger.info(f"Found {len(peptides)} peptides in similarity search")
            return peptides
            
        except Exception as e:
            logger.error(f"Error searching peptides in Qdrant: {str(e)}")
            raise
