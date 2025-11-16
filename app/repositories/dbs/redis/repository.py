"""Main Redis repository that composes all operation modules."""

from typing import Dict, Any, List, Optional
from app.repositories.base.base_repository import BaseRepository
from .client import RedisClientManager
from .utils_operations import RedisUtilsOperations
from .create_operations import RedisCreateOperations
from .read_operations import RedisReadOperations
from .update_operations import RedisUpdateOperations
from .delete_operations import RedisDeleteOperations
from .cache_operations import RedisCacheOperations

class CacheRepository(BaseRepository[Dict[str, Any]]):
    """Repository for cache operations using Redis."""
    
    def __init__(self):
        """Initialize Redis repository with all operation modules."""
        # Initialize client manager
        self.client_manager = RedisClientManager()
        self.redis_client = self.client_manager.redis_client
        
        # Initialize utility operations (needed by other operations)
        self.utils = RedisUtilsOperations()
        
        # Initialize operation modules
        self.create_ops = RedisCreateOperations(self.redis_client)
        self.read_ops = RedisReadOperations(self.redis_client)
        self.update_ops = RedisUpdateOperations(self.redis_client)
        self.delete_ops = RedisDeleteOperations(self.redis_client)
        self.cache_ops = RedisCacheOperations(self.redis_client, self.utils, self.create_ops, self.read_ops)
    
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
    
    # Additional Redis-specific methods
    def get_cached_response(self, query: str, peptide_name: Optional[str] = None, endpoint_type: str = "general") -> Optional[Dict[str, Any]]:
        """Get cached response for a query."""
        return self.cache_ops.get_cached_response(query, peptide_name, endpoint_type)
    
    def set_cached_response(self, query: str, response: Dict[str, Any], peptide_name: Optional[str] = None, endpoint_type: str = "general", ttl: Optional[int] = None) -> bool:
        """Set cached response for a query."""
        return self.cache_ops.set_cached_response(query, response, peptide_name, endpoint_type, ttl)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        return self.cache_ops.get_cache_stats()
    
    def clear_all_cache(self) -> bool:
        """Clear all cache entries."""
        return self.cache_ops.clear_all_cache()
    
    def get_ttl(self, key: str) -> int:
        """Get TTL for a cache key."""
        return self.cache_ops.get_ttl(key)
    
    def exists(self, key: str) -> bool:
        """Check if a cache key exists."""
        return self.cache_ops.exists(key)
    
    def ping(self) -> bool:
        """Ping Redis to check connection health."""
        return self.cache_ops.ping()

