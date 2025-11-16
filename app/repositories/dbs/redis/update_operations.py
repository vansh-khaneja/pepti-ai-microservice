"""Update operations for Redis repository."""

from typing import Dict, Any, Optional
from app.core.config import settings
from app.utils.helpers import logger, ExternalApiTimer
import json

class RedisUpdateOperations:
    """Handles update operations for Redis."""
    
    def __init__(self, redis_client):
        """Initialize with Redis client."""
        self.redis_client = redis_client
    
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

