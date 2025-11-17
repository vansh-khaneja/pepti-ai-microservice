"""Utility operations for Qdrant repository."""

from typing import Dict, Any, List
from app.utils.helpers import logger

class QdrantUtilsOperations:
    """Handles utility operations for Qdrant."""
    
    def __init__(self, client, collection_name: str):
        """Initialize with Qdrant client and collection name."""
        self.client = client
        self.collection_name = collection_name
    
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
    
    def get_all_peptide_names(self) -> set:
        """Get all peptide names from Qdrant by scrolling through all points"""
        try:
            peptide_names = set()
            offset = None
            batch_size = 100  # Scroll in batches
            
            logger.info(f"📥 Fetching all peptide names from Qdrant collection '{self.collection_name}'...")
            
            while True:
                points, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=batch_size,
                    offset=offset,
                    with_payload=["name"],  # Only fetch name field to save bandwidth
                    with_vectors=False  # Don't need vectors
                )
                
                # Extract names from points
                for point in points:
                    name = point.payload.get("name")
                    if name:
                        peptide_names.add(str(name).strip())
                
                logger.debug(f"📊 Scrolled batch: found {len(points)} points, total unique names: {len(peptide_names)}")
                
                # Check if there are more points
                if next_offset is None:
                    break
                offset = next_offset
            
            logger.info(f"✅ Retrieved {len(peptide_names)} unique peptide names from Qdrant")
            return peptide_names
            
        except Exception as e:
            logger.error(f"Error getting all peptide names from Qdrant: {str(e)}")
            return set()
    
    def get_peptide_name_to_ids(self) -> Dict[str, List]:
        """Get mapping of peptide names to their point IDs (handles duplicates)"""
        try:
            name_to_ids = {}
            offset = None
            batch_size = 100  # Scroll in batches
            
            logger.info(f"📥 Fetching peptide name-to-ID mapping from Qdrant collection '{self.collection_name}'...")
            
            while True:
                points, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=batch_size,
                    offset=offset,
                    with_payload=["name"],  # Only fetch name field
                    with_vectors=False  # Don't need vectors
                )
                
                # Map names to IDs
                for point in points:
                    name = point.payload.get("name")
                    if name:
                        name_str = str(name).strip()
                        if name_str not in name_to_ids:
                            name_to_ids[name_str] = []
                        name_to_ids[name_str].append(point.id)
                
                logger.debug(f"📊 Scrolled batch: found {len(points)} points, total unique names: {len(name_to_ids)}")
                
                # Check if there are more points
                if next_offset is None:
                    break
                offset = next_offset
            
            logger.info(f"✅ Retrieved name-to-ID mapping for {len(name_to_ids)} unique peptide names from Qdrant")
            return name_to_ids
            
        except Exception as e:
            logger.error(f"Error getting peptide name-to-ID mapping from Qdrant: {str(e)}")
            return {}
    
    def health_check(self) -> bool:
        """Check Qdrant connection health by attempting to get collections."""
        try:
            # Try to get collections - this will fail if Qdrant is not accessible
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {str(e)}")
            raise

