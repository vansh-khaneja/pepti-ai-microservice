"""Cache-specific operations for Redis repository."""

from typing import Dict, Any, Optional
from app.core.config import settings
from app.utils.helpers import logger, ExternalApiTimer
import json

class RedisCacheOperations:
    """Handles cache-specific operations for Redis."""
    
    def __init__(self, redis_client, utils_ops, create_ops, read_ops):
        """Initialize with Redis client, utils operations, create operations, and read operations."""
        self.redis_client = redis_client
        self.utils_ops = utils_ops
        self.create_ops = create_ops
        self.read_ops = read_ops
    
    def get_cached_response(self, query: str, peptide_name: Optional[str] = None, endpoint_type: str = "general") -> Optional[Dict[str, Any]]:
        """Get cached response for a query."""
        cache_key = self.utils_ops._generate_cache_key("chat_cache", endpoint_type, query, peptide_name or "")
        return self.read_ops.get_by_id(cache_key)
    
    def set_cached_response(self, query: str, response: Dict[str, Any], peptide_name: Optional[str] = None, endpoint_type: str = "general", ttl: Optional[int] = None) -> bool:
        """Set cached response for a query."""
        cache_key = self.utils_ops._generate_cache_key("chat_cache", endpoint_type, query, peptide_name or "")
        
        # Create entity in the expected format
        entity = {
            "key": cache_key,
            "data": response,
            "ttl": ttl or settings.CACHE_TTL
        }
        
        try:
            result = self.create_ops.create(entity)
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

