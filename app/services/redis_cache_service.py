import redis
import json
import hashlib
from typing import Dict, Any, Optional
from app.core.config import settings
from app.utils.helpers import logger, ExternalApiTimer

class RedisCacheService:
    def __init__(self):
        """Initialize Redis connection"""
        try:
            logger.info(f"Connecting to Redis at: {settings.REDIS_URL} (DB: {settings.REDIS_DB})")
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis at {settings.REDIS_URL}: {str(e)}")
            self.redis_client = None

    def _generate_cache_key(self, query: str, peptide_name: Optional[str] = None, endpoint_type: str = "general") -> str:
        """
        Generate a consistent cache key for queries
        
        Args:
            query: The user query
            peptide_name: Optional peptide name for specific queries
            endpoint_type: Type of endpoint ("general" or "specific")
        """
        # Normalize query (lowercase, strip whitespace)
        normalized_query = query.lower().strip()
        
        # Create key components
        key_parts = [endpoint_type, normalized_query]
        if peptide_name:
            key_parts.append(peptide_name.lower().strip())
        
        # Join and hash for consistent key length
        key_string = "|".join(key_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"chat_cache:{key_hash}"

    def get_cached_response(self, query: str, peptide_name: Optional[str] = None, endpoint_type: str = "general") -> Optional[Dict[str, Any]]:
        """
        Retrieve cached response for a query
        
        Args:
            query: The user query
            peptide_name: Optional peptide name for specific queries
            endpoint_type: Type of endpoint ("general" or "specific")
            
        Returns:
            Cached response dict or None if not found
        """
        if not self.redis_client:
            return None
            
        try:
            cache_key = self._generate_cache_key(query, peptide_name, endpoint_type)
            
            with ExternalApiTimer("redis", operation="get", metadata={"key": cache_key}) as t:
                cached_data = self.redis_client.get(cache_key)
                t.set_status(status_code=200, success=(cached_data is not None))
            
            if cached_data:
                logger.info(f"Cache HIT for query: {query[:50]}...")
                return json.loads(cached_data)
            else:
                logger.info(f"Cache MISS for query: {query[:50]}...")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
            return None

    def set_cached_response(self, query: str, response: Dict[str, Any], peptide_name: Optional[str] = None, endpoint_type: str = "general", ttl: Optional[int] = None) -> bool:
        """
        Cache a response for a query
        
        Args:
            query: The user query
            response: The response to cache
            peptide_name: Optional peptide name for specific queries
            endpoint_type: Type of endpoint ("general" or "specific")
            ttl: Time to live in seconds (defaults to settings.CACHE_TTL)
            
        Returns:
            True if cached successfully, False otherwise
        """
        if not self.redis_client:
            return False
            
        try:
            cache_key = self._generate_cache_key(query, peptide_name, endpoint_type)
            ttl = ttl or settings.CACHE_TTL
            
            # Add metadata to cached response
            cached_response = {
                "query": query,
                "peptide_name": peptide_name,
                "endpoint_type": endpoint_type,
                "cached_at": response.get("timestamp", ""),
                "response": response
            }
            
            with ExternalApiTimer("redis", operation="set", metadata={"key": cache_key, "ttl": ttl}) as t:
                result = self.redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(cached_response, default=str)
                )
                t.set_status(status_code=200, success=result)
            
            if result:
                logger.info(f"Cached response for query: {query[:50]}... (TTL: {ttl}s)")
                return True
            else:
                logger.warning(f"Failed to cache response for query: {query[:50]}...")
                return False
                
        except Exception as e:
            logger.error(f"Error caching response: {str(e)}")
            return False

    def invalidate_cache(self, pattern: str = "chat_cache:*") -> int:
        """
        Invalidate cache entries matching a pattern
        
        Args:
            pattern: Redis key pattern to match
            
        Returns:
            Number of keys deleted
        """
        if not self.redis_client:
            return 0
            
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted_count = self.redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted_count} cache entries matching pattern: {pattern}")
                return deleted_count
            return 0
            
        except Exception as e:
            logger.error(f"Error invalidating cache: {str(e)}")
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get Redis cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.redis_client:
            return {"error": "Redis not connected"}
            
        try:
            info = self.redis_client.info()
            cache_keys = self.redis_client.keys("chat_cache:*")
            
            return {
                "redis_url": settings.REDIS_URL,
                "redis_db": settings.REDIS_DB,
                "cache_ttl": settings.CACHE_TTL,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "cache_keys_count": len(cache_keys),
                "cache_keys_sample": cache_keys[:5] if cache_keys else []
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {"error": str(e)}

    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
