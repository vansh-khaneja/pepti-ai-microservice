"""Repository manager for managing core data repositories globally."""

from typing import Optional
from app.repositories.vector_store.qdrant_repository import VectorStoreRepository
from app.repositories.relational.postgresql_repository import RelationalRepository
from app.repositories.cache.redis_repository import CacheRepository
from app.utils.helpers import logger


class RepositoryManager:
    """Singleton manager for core data repositories."""
    
    _instance: Optional['RepositoryManager'] = None
    
    # Repository instances
    _vector_store_repo: Optional[VectorStoreRepository] = None
    _relational_repo: Optional[RelationalRepository] = None
    _cache_repo: Optional[CacheRepository] = None
    
    def __new__(cls) -> 'RepositoryManager':
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the repository manager."""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._initialize_repositories()
    
    def _initialize_repositories(self):
        """Initialize all repositories."""
        try:
            # Initialize vector store repository
            self._vector_store_repo = VectorStoreRepository()
            logger.info("Vector store repository initialized successfully")
            
            # Initialize relational repository
            self._relational_repo = RelationalRepository()
            logger.info("Relational repository initialized successfully")
            
            # Initialize cache repository
            self._cache_repo = CacheRepository()
            logger.info("Cache repository initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize repositories: {str(e)}")
    
    # Core Repositories
    @property
    def vector_store(self) -> VectorStoreRepository:
        """Get vector store repository instance."""
        if self._vector_store_repo is None:
            raise ValueError("Vector store repository not initialized")
        return self._vector_store_repo
    
    @property
    def relational(self) -> RelationalRepository:
        """Get relational repository instance."""
        if self._relational_repo is None:
            raise ValueError("Relational repository not initialized")
        return self._relational_repo
    
    @property
    def cache(self) -> CacheRepository:
        """Get cache repository instance."""
        if self._cache_repo is None:
            raise ValueError("Cache repository not initialized")
        return self._cache_repo
    
    # Health checks
    def is_vector_store_available(self) -> bool:
        """Check if vector store is available."""
        return self._vector_store_repo is not None
    
    def is_relational_db_available(self) -> bool:
        """Check if relational database is available."""
        return self._relational_repo is not None
    
    def is_cache_available(self) -> bool:
        """Check if cache is available."""
        return self._cache_repo is not None
    
    def get_health_status(self) -> dict:
        """Get health status of all repositories."""
        return {
            "vector_store": {
                "available": self.is_vector_store_available(),
                "qdrant": self._vector_store_repo is not None
            },
            "relational_db": {
                "available": self.is_relational_db_available(),
                "postgresql": self._relational_repo is not None
            },
            "cache": {
                "available": self.is_cache_available(),
                "redis": self._cache_repo is not None
            }
        }


# Global instance
repository_manager = RepositoryManager()
