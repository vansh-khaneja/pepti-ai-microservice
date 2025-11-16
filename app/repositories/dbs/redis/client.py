"""Redis client initialization and configuration."""

import redis
from app.core.config import settings
from app.utils.helpers import logger

class RedisClientManager:
    """Manages Redis client initialization."""
    
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
            logger.info("Redis client initialized successfully with connection pooling")
        except Exception as e:
            logger.error(f"Failed to connect to Redis at {settings.REDIS_URL}: {str(e)}")
            self.redis_client = None

