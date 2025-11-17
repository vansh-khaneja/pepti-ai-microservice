"""Delete operations for Qdrant repository."""

from typing import Dict, List
from app.utils.helpers import logger

class QdrantDeleteOperations:
    """Handles delete operations for Qdrant."""
    
    def __init__(self, client, collection_name: str, utils_ops):
        """Initialize with Qdrant client, collection name, and utils operations."""
        self.client = client
        self.collection_name = collection_name
        self.utils_ops = utils_ops
    
    def delete(self, entity_id: str) -> bool:
        """Delete a peptide by point ID."""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[entity_id]
            )
            
            logger.info(f"Peptide with ID '{entity_id}' deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting peptide: {str(e)}")
            return False
    
    def delete_by_names(self, names: set) -> int:
        """
        Delete multiple peptides by names. 
        Uses name-to-ID mapping from scroll (no index required).
        Returns count of successfully deleted peptides.
        """
        if not names:
            return 0
        
        try:
            # Get name-to-ID mapping by scrolling through all points
            name_to_ids = self.utils_ops.get_peptide_name_to_ids()
            
            # Collect all point IDs to delete
            ids_to_delete = []
            names_found = set()
            
            for name in names:
                name_str = str(name).strip()
                if name_str in name_to_ids:
                    ids_to_delete.extend(name_to_ids[name_str])
                    names_found.add(name_str)
                else:
                    logger.debug(f"Peptide '{name_str}' not found in Qdrant for deletion")
            
            if not ids_to_delete:
                logger.warning(f"⚠️ No peptides found to delete from {len(names)} requested names")
                return 0
            
            # Delete all points by their IDs
            logger.info(f"🗑️ Deleting {len(ids_to_delete)} point(s) for {len(names_found)} peptide name(s)...")
            
            deleted_count = 0
            failed_count = 0
            
            # Delete in batches to avoid overwhelming Qdrant
            batch_size = 50
            for i in range(0, len(ids_to_delete), batch_size):
                batch_ids = ids_to_delete[i:i + batch_size]
                try:
                    self.client.delete(
                        collection_name=self.collection_name,
                        points_selector=batch_ids
                    )
                    deleted_count += len(batch_ids)
                    logger.debug(f"✅ Deleted batch of {len(batch_ids)} points")
                except Exception as e:
                    logger.error(f"Error deleting batch of points: {str(e)}")
                    failed_count += len(batch_ids)
            
            if deleted_count > 0:
                logger.info(f"✅ Deleted {deleted_count} point(s) for {len(names_found)} peptide name(s) from Qdrant")
            if failed_count > 0:
                logger.warning(f"⚠️ Failed to delete {failed_count} points")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting peptides by names: {str(e)}")
            return 0

