"""Create operations for Qdrant repository."""

from typing import Dict, Any
from qdrant_client.models import PointStruct
from app.utils.helpers import logger
import uuid
import time

class QdrantCreateOperations:
    """Handles create operations for Qdrant."""
    
    def __init__(self, client, collection_name: str):
        """Initialize with Qdrant client and collection name."""
        self.client = client
        self.collection_name = collection_name
    
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
                    self.client.upsert(
                        collection_name=self.collection_name,
                        points=[point]
                    )
                    
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

