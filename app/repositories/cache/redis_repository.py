"""Cache repository for Redis operations."""

import redis
import json
import hashlib
from typing import Dict, Any, Optional, List
from app.repositories.base_repository import BaseRepository
from app.core.config import settings
from app.utils.helpers import logger, ExternalApiTimer

class CacheRepository(BaseRepository[Dict[str, Any]]):
    """Repository for cache operations using Redis."""
    
    def __init__(self):
        """Initialize Redis connection with connection pooling."""
        try:
            logger.info(f"Connecting to Redis at: {settings.REDIS_URL} (DB: {settings.REDIS_DB})")
            # Use connection pool for better performance
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                max_connections=50,  # Connection pool size
                health_check_interval=30  # Health check every 30 seconds
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Cache repository initialized successfully with connection pooling")
        except Exception as e:
            logger.error(f"Failed to connect to Redis at {settings.REDIS_URL}: {str(e)}")
            self.redis_client = None
    
    def _generate_cache_key(self, key_prefix: str, *key_parts: str) -> str:
        """Generate a consistent cache key."""
        # Normalize key parts (lowercase, strip whitespace)
        normalized_parts = [part.lower().strip() for part in key_parts if part]
        
        # Join and hash for consistent key length
        key_string = "|".join([key_prefix] + normalized_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"{key_prefix}:{key_hash}"
    
    def create(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Store data in cache."""
        try:
            if not self.redis_client:
                return entity
            
            key = entity.get("key")
            data = entity.get("data", entity)
            ttl = entity.get("ttl", settings.CACHE_TTL)
            
            if not key:
                raise ValueError("Cache key is required")
            
            with ExternalApiTimer("redis", operation="set") as t:
                self.redis_client.setex(key, ttl, json.dumps(data))
                t.set_status(status_code=200, success=True)
            
            logger.info(f"Data cached successfully with key: {key}")
            return entity
            
        except Exception as e:
            logger.error(f"Error caching data: {str(e)}")
            return entity
    
    def get_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get data from cache by key."""
        try:
            if not self.redis_client:
                return None
            
            with ExternalApiTimer("redis", operation="get") as t:
                cached_data = self.redis_client.get(entity_id)
                t.set_status(status_code=200, success=(cached_data is not None))
            
            if cached_data:
                logger.info(f"Cache HIT for key: {entity_id}")
                return json.loads(cached_data)
            else:
                logger.info(f"Cache MISS for key: {entity_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
            return None
    
    def update(self, entity_id: str, entity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update cached data."""
        try:
            if not self.redis_client:
                return None
            
            data = entity.get("data", entity)
            ttl = entity.get("ttl", settings.CACHE_TTL)
            
            with ExternalApiTimer("redis", operation="setex") as t:
                self.redis_client.setex(entity_id, ttl, json.dumps(data))
                t.set_status(status_code=200, success=True)
            
            logger.info(f"Cache updated successfully for key: {entity_id}")
            return {"key": entity_id, "data": data}
            
        except Exception as e:
            logger.error(f"Error updating cache: {str(e)}")
            return None
    
    def delete(self, entity_id: str) -> bool:
        """Delete data from cache."""
        try:
            if not self.redis_client:
                return False
            
            with ExternalApiTimer("redis", operation="delete") as t:
                result = self.redis_client.delete(entity_id)
                t.set_status(status_code=200, success=(result > 0))
            
            if result > 0:
                logger.info(f"Cache deleted successfully for key: {entity_id}")
                return True
            else:
                logger.info(f"Cache key not found: {entity_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting from cache: {str(e)}")
            return False
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List all cache keys (not recommended for production)."""
        try:
            if not self.redis_client:
                return []
            
            with ExternalApiTimer("redis", operation="keys") as t:
                keys = self.redis_client.keys("*")
                t.set_status(status_code=200, success=True)
            
            # Apply pagination
            paginated_keys = keys[offset:offset + limit]
            
            results = []
            for key in paginated_keys:
                try:
                    data = self.redis_client.get(key)
                    if data:
                        results.append({
                            "key": key,
                            "data": json.loads(data)
                        })
                except Exception:
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Error listing cache keys: {str(e)}")
            return []
    
    def get_cached_response(self, query: str, peptide_name: Optional[str] = None, endpoint_type: str = "general") -> Optional[Dict[str, Any]]:
        """Get cached response for a query."""
        cache_key = self._generate_cache_key("chat_cache", endpoint_type, query, peptide_name or "")
        cached_data = self.get_by_id(cache_key)
        
        if cached_data:
            # Return the cached response data directly
            return cached_data
        return None
    
    def set_cached_response(self, query: str, response: Dict[str, Any], peptide_name: Optional[str] = None, endpoint_type: str = "general", ttl: Optional[int] = None) -> bool:
        """Set cached response for a query."""
        cache_key = self._generate_cache_key("chat_cache", endpoint_type, query, peptide_name or "")
        
        # Create entity in the expected format
        entity = {
            "key": cache_key,
            "data": response,
            "ttl": ttl or settings.CACHE_TTL
        }
        
        try:
            result = self.create(entity)
            return result is not None
        except Exception as e:
            logger.error(f"Error setting cached response: {str(e)}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        try:
            if not self.redis_client:
                return {"status": "disconnected"}
            
            info = self.redis_client.info()
            return {
                "status": "connected",
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "db_size": self.redis_client.dbsize()
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def clear_all_cache(self) -> bool:
        """Clear all cache entries."""
        try:
            if not self.redis_client:
                return False
            
            with ExternalApiTimer("redis", operation="flushdb") as t:
                self.redis_client.flushdb()
                t.set_status(status_code=200, success=True)
            
            logger.info("All cache entries cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return False
    
    def get_ttl(self, key: str) -> int:
        """Get TTL for a cache key."""
        try:
            if not self.redis_client:
                return -1
            
            return self.redis_client.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL: {str(e)}")
            return -1
    
    def exists(self, key: str) -> bool:
        """Check if a cache key exists."""
        try:
            if not self.redis_client:
                return False
            
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Error checking key existence: {str(e)}")
            return False
    
    def ping(self) -> bool:
        """Ping Redis to check connection health."""
        try:
            if not self.redis_client:
                return False
            
            return self.redis_client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {str(e)}")
            raise