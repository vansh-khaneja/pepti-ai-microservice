"""Delete operations for Redis repository."""

from app.utils.helpers import logger, ExternalApiTimer

class RedisDeleteOperations:
    """Handles delete operations for Redis."""
    
    def __init__(self, redis_client):
        """Initialize with Redis client."""
        self.redis_client = redis_client
    
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

