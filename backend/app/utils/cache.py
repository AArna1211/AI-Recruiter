"""
Caching Utilities
"""
import hashlib
import json
import redis
from functools import wraps
from typing import Any, Callable
import logging

logger = logging.getLogger(__name__)

# Initialize Redis client
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def cache_result(ttl: int = 3600):
    """Decorator to cache function results in Redis"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key_parts = [func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}:{v}" for k, v in kwargs.items()])
            key = hashlib.md5("_".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            try:
                cached = redis_client.get(f"cache:{key}")
                if cached:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
            
            # Compute result
            result = func(*args, **kwargs)
            
            # Store in cache
            try:
                # Convert numpy arrays to lists for JSON serialization
                if hasattr(result, 'tolist'):
                    result = result.tolist()
                redis_client.setex(
                    f"cache:{key}",
                    ttl,
                    json.dumps(result)
                )
            except Exception as e:
                logger.warning(f"Cache write error: {e}")
            
            return result
        return wrapper
    return decorator
