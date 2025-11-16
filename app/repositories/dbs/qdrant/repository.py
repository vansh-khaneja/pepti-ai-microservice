"""Main Qdrant repository that composes all operation modules."""

from typing import Dict, Any, List, Optional
from app.repositories.base.base_repository import BaseRepository
from .client import QdrantClientManager
from .create_operations import QdrantCreateOperations
from .read_operations import QdrantReadOperations
from .update_operations import QdrantUpdateOperations
from .delete_operations import QdrantDeleteOperations
from .search_operations import QdrantSearchOperations
from .utils_operations import QdrantUtilsOperations

class VectorStoreRepository(BaseRepository[Dict[str, Any]]):
    """Repository for vector store operations using Qdrant."""
    
    def __init__(self):
        """Initialize Qdrant repository with all operation modules."""
        # Initialize client manager
        self.client_manager = QdrantClientManager()
        self.client = self.client_manager.client
        self.collection_name = self.client_manager.collection_name
        
        # Initialize utility operations (needed by other operations)
        self.utils = QdrantUtilsOperations(self.client, self.collection_name)
        
        # Initialize operation modules
        self.create_ops = QdrantCreateOperations(self.client, self.collection_name)
        self.read_ops = QdrantReadOperations(self.client, self.collection_name, self.utils)
        self.update_ops = QdrantUpdateOperations(self.client, self.collection_name, self.read_ops)
        self.delete_ops = QdrantDeleteOperations(self.client, self.collection_name, self.utils)
        self.search_ops = QdrantSearchOperations(self.client, self.collection_name)
    
    # BaseRepository interface methods
    def create(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new entity."""
        return self.create_ops.create(entity)
    
    def get_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID."""
        return self.read_ops.get_by_id(entity_id)
    
    def update(self, entity_id: str, entity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an entity."""
        return self.update_ops.update(entity_id, entity)
    
    def delete(self, entity_id: str) -> bool:
        """Delete an entity."""
        return self.delete_ops.delete(entity_id)
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List all entities with pagination."""
        return self.read_ops.list_all(limit, offset)
    
    # Additional Qdrant-specific methods
    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get peptide by name."""
        return self.read_ops.get_by_name(name)
    
    def search_similar(self, vector: List[float], limit: int = 10, score_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """Search for similar peptides."""
        return self.search_ops.search_similar(vector, limit, score_threshold)
    
    def delete_by_names(self, names: set) -> int:
        """Delete multiple peptides by names."""
        return self.delete_ops.delete_by_names(names)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        return self.utils.get_collection_stats()
    
    def get_all_peptide_names(self) -> set:
        """Get all peptide names."""
        return self.utils.get_all_peptide_names()
    
    def get_peptide_name_to_ids(self) -> Dict[str, List]:
        """Get mapping of peptide names to their point IDs."""
        return self.utils.get_peptide_name_to_ids()
    
    def ensure_name_index(self):
        """Ensure name index exists."""
        return self.utils.ensure_name_index()
    
    def health_check(self) -> bool:
        """Check Qdrant connection health."""
        return self.utils.health_check()

