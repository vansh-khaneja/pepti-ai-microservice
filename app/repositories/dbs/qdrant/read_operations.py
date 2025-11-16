"""Read operations for Qdrant repository."""

from typing import Dict, Any, Optional, List
from qdrant_client.models import Filter, FieldCondition, MatchValue
from app.utils.helpers import logger, ExternalApiTimer

class QdrantReadOperations:
    """Handles read operations for Qdrant."""
    
    def __init__(self, client, collection_name: str, index_manager):
        """Initialize with Qdrant client, collection name, and index manager."""
        self.client = client
        self.collection_name = collection_name
        self.index_manager = index_manager
    
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
            self.index_manager.ensure_name_index()
            
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

