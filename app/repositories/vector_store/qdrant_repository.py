"""Vector store repository for Qdrant operations."""

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from app.repositories.base_repository import BaseRepository
from app.core.config import settings
from app.utils.helpers import logger, ExternalApiTimer
import uuid
import time

class VectorStoreRepository(BaseRepository[Dict[str, Any]]):
    """Repository for vector store operations using Qdrant."""
    
    def __init__(self):
        """Initialize Qdrant client."""
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(settings.QDRANT_URL)
            
            if settings.QDRANT_API_KEY:
                self.client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY
                )
            else:
                self.client = QdrantClient(url=settings.QDRANT_URL)
            
            self.collection_name = settings.PEPTIDE_COLLECTION
            self.vector_size = 3072  # OpenAI text-embedding-3-large dimension
            
            # Ensure collection exists
            self._ensure_collection_exists()
            logger.info("Vector store repository initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store repository: {str(e)}")
            raise
    
    def _ensure_collection_exists(self):
        """Ensure the peptides collection exists, create if it doesn't."""
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
                logger.info(f"Collection '{self.collection_name}' created successfully")
            else:
                logger.info(f"Collection '{self.collection_name}' already exists")
                
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {str(e)}")
            raise
    
    def ensure_name_index(self):
        """Ensure name index exists for efficient name-based queries."""
        try:
            # Check if name index exists
            collection_info = self.client.get_collection(self.collection_name)
            existing_indexes = collection_info.payload_schema or {}
            
            if "name" not in existing_indexes:
                logger.info("Creating name index for efficient peptide lookups")
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="name",
                    field_schema="keyword"
                )
                logger.info("Name index created successfully")
            else:
                logger.debug("Name index already exists")
                
        except Exception as e:
            logger.error(f"Error creating name index: {str(e)}")
            raise
    
    def create(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Store a peptide in Qdrant with its embedding."""
        try:
            # Generate UUID for Qdrant point ID
            point_id = str(uuid.uuid4())
            
            # Create the point structure
            point = PointStruct(
                id=point_id,
                vector=entity["vector"],
                payload={
                    "name": entity["name"],
                    "overview": entity["overview"],
                    "mechanism_of_actions": entity["mechanism_of_actions"],
                    "potential_research_fields": entity["potential_research_fields"],
                    "created_at": entity["created_at"],
                    "text_content": entity["text_content"]
                }
            )
            
            # Insert with retry for transient errors
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    with ExternalApiTimer("qdrant", operation="upsert") as t:
                        self.client.upsert(
                            collection_name=self.collection_name,
                            points=[point]
                        )
                        t.set_status(status_code=200, success=True)
                    
                    logger.info(f"Peptide '{entity['name']}' stored successfully with ID: {point_id}")
                    return {"id": point_id, **entity}
                    
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    logger.warning(f"Attempt {attempt} failed, retrying: {str(e)}")
                    time.sleep(1)
                    
        except Exception as e:
            logger.error(f"Error storing peptide: {str(e)}")
            raise
    
    def get_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get peptide by point ID."""
        try:
            with ExternalApiTimer("qdrant", operation="retrieve") as t:
                points = self.client.retrieve(
                    collection_name=self.collection_name,
                    ids=[entity_id]
                )
                t.set_status(status_code=200, success=(len(points) > 0))
            
            if points:
                point = points[0]
                return {
                    "id": point.id,
                    "vector": point.vector,
                    **point.payload
                }
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving peptide by ID: {str(e)}")
            return None
    
    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get peptide by name using payload filter."""
        try:
            self.ensure_name_index()
            
            with ExternalApiTimer("qdrant", operation="scroll") as t:
                points, _ = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="name",
                                match=MatchValue(value=name)
                            )
                        ]
                    ),
                    limit=1
                )
                t.set_status(status_code=200, success=(len(points) > 0))
            
            if points:
                point = points[0]
                return {
                    "id": point.id,
                    "vector": point.vector,
                    **point.payload
                }
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving peptide by name: {str(e)}")
            return None
    
    def search_similar(self, vector: List[float], limit: int = 10, score_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """Search for similar peptides using vector similarity."""
        try:
            search_params = {
                "collection_name": self.collection_name,
                "query_vector": vector,
                "limit": limit,
                "with_payload": True,
                "with_vectors": True
            }
            
            if score_threshold:
                search_params["score_threshold"] = score_threshold
            
            with ExternalApiTimer("qdrant", operation="search") as t:
                results = self.client.search(**search_params)
                t.set_status(status_code=200, success=True)
            
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "vector": result.vector,
                    **result.payload
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching similar peptides: {str(e)}")
            return []
    
    def update(self, entity_id: str, entity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a peptide in Qdrant."""
        try:
            # Check if entity exists
            existing = self.get_by_id(entity_id)
            if not existing:
                return None
            
            # Update payload
            point = PointStruct(
                id=entity_id,
                vector=entity["vector"],
                payload={
                    "name": entity["name"],
                    "overview": entity["overview"],
                    "mechanism_of_actions": entity["mechanism_of_actions"],
                    "potential_research_fields": entity["potential_research_fields"],
                    "created_at": entity["created_at"],
                    "text_content": entity["text_content"]
                }
            )
            
            with ExternalApiTimer("qdrant", operation="upsert") as t:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=[point]
                )
                t.set_status(status_code=200, success=True)
            
            logger.info(f"Peptide '{entity['name']}' updated successfully")
            return {"id": entity_id, **entity}
            
        except Exception as e:
            logger.error(f"Error updating peptide: {str(e)}")
            return None
    
    def delete(self, entity_id: str) -> bool:
        """Delete a peptide by point ID."""
        try:
            with ExternalApiTimer("qdrant", operation="delete") as t:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=[entity_id]
                )
                t.set_status(status_code=200, success=True)
            
            logger.info(f"Peptide with ID '{entity_id}' deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting peptide: {str(e)}")
            return False
    
    def delete_by_name(self, name: str) -> bool:
        """Delete a peptide by name."""
        try:
            # First find the peptide by name
            peptide = self.get_by_name(name)
            if not peptide:
                logger.warning(f"Peptide '{name}' not found for deletion")
                return False
            
            # Delete by ID
            return self.delete(peptide["id"])
            
        except Exception as e:
            logger.error(f"Error deleting peptide by name: {str(e)}")
            return False
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List all peptides with pagination."""
        try:
            with ExternalApiTimer("qdrant", operation="scroll") as t:
                points, _ = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=limit,
                    offset=offset,
                    with_payload=True,
                    with_vectors=True
                )
                t.set_status(status_code=200, success=True)
            
            formatted_results = []
            for point in points:
                formatted_results.append({
                    "id": point.id,
                    "vector": point.vector,
                    **point.payload
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error listing peptides: {str(e)}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "status": collection_info.status,
                "optimizer_status": collection_info.optimizer_status
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {}
