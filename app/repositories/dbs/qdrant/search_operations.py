"""Search operations for Qdrant repository."""

from typing import List, Dict, Any, Optional
from app.utils.helpers import logger, ExternalApiTimer

class QdrantSearchOperations:
    """Handles search operations for Qdrant."""
    
    def __init__(self, client, collection_name: str):
        """Initialize with Qdrant client and collection name."""
        self.client = client
        self.collection_name = collection_name
    
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

