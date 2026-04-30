import hashlib
import json
from typing import Optional, Dict, Any
from functools import lru_cache

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

in_memory_cache: Dict[str, Any] = {}


def _generate_cache_key(user_id: int, question: str) -> str:
    key_str = f"{user_id}:{question}".encode()
    return hashlib.md5(key_str).hexdigest()


def get_cached_result(user_id: int, question: str) -> Optional[Dict[str, Any]]:
    if not settings.cache_enabled:
        return None
    
    cache_key = _generate_cache_key(user_id, question)
    
    try:
        import redis
        r = redis.from_url(settings.redis_url)
        cached = r.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for key {cache_key}")
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis cache lookup failed: {str(e)}, falling back to in-memory")
    
    if cache_key in in_memory_cache:
        logger.debug(f"In-memory cache hit for key {cache_key}")
        return in_memory_cache[cache_key]
    
    return None


def set_cached_result(user_id: int, question: str, result: Dict[str, Any]) -> None:
    if not settings.cache_enabled:
        return
    
    cache_key = _generate_cache_key(user_id, question)
    
    try:
        import redis
        r = redis.from_url(settings.redis_url)
        r.setex(
            cache_key,
            settings.cache_ttl,
            json.dumps(result)
        )
        logger.debug(f"Cached result in Redis for key {cache_key}")
    except Exception as e:
        logger.warning(f"Redis cache write failed: {str(e)}, using in-memory cache")
        in_memory_cache[cache_key] = result
        logger.debug(f"Cached result in memory for key {cache_key}")


def clear_cache(user_id: int) -> None:
    logger.info(f"Clearing cache for user {user_id}")
    
    try:
        import redis
        r = redis.from_url(settings.redis_url)
        keys = r.keys(f"*{user_id}*")
        if keys:
            r.delete(*keys)
    except Exception as e:
        logger.warning(f"Redis cache clear failed: {str(e)}")
    
    to_delete = [k for k in in_memory_cache.keys() if str(user_id) in k]
    for k in to_delete:
        del in_memory_cache[k]