"""Read operations for Redis repository."""

from typing import Dict, Any, Optional, List
from app.utils.helpers import logger, ExternalApiTimer
import json

class RedisReadOperations:
    """Handles read operations for Redis."""
    
    def __init__(self, redis_client):
        """Initialize with Redis client."""
        self.redis_client = redis_client
    
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

