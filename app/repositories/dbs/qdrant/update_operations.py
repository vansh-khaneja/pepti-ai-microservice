"""Update operations for Qdrant repository."""

from typing import Dict, Any, Optional
from qdrant_client.models import PointStruct
from app.utils.helpers import logger, ExternalApiTimer

class QdrantUpdateOperations:
    """Handles update operations for Qdrant."""
    
    def __init__(self, client, collection_name: str, read_ops):
        """Initialize with Qdrant client, collection name, and read operations."""
        self.client = client
        self.collection_name = collection_name
        self.read_ops = read_ops
    
    def update(self, entity_id: str, entity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a peptide in Qdrant."""
        try:
            # Check if entity exists
            existing = self.read_ops.get_by_id(entity_id)
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

