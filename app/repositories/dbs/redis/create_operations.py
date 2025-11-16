"""Create operations for Redis repository."""

from typing import Dict, Any
from app.core.config import settings
from app.utils.helpers import logger, ExternalApiTimer
import json

class RedisCreateOperations:
    """Handles create operations for Redis."""
    
    def __init__(self, redis_client):
        """Initialize with Redis client."""
        self.redis_client = redis_client
    
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

