"""Utility operations for Redis repository."""

import hashlib

class RedisUtilsOperations:
    """Handles utility operations for Redis."""
    
    def _generate_cache_key(self, key_prefix: str, *key_parts: str) -> str:
        """Generate a consistent cache key."""
        # Normalize key parts (lowercase, strip whitespace)
        normalized_parts = [part.lower().strip() for part in key_parts if part]
        
        # Join and hash for consistent key length
        key_string = "|".join([key_prefix] + normalized_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"{key_prefix}:{key_hash}"

