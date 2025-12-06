from typing import Optional

import redis.asyncio as redis

from app.config.settings import get_settings

_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    global _redis_client

    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.Redis.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            socket_timeout=settings.redis_socket_timeout,
            decode_responses=False,
        )

    return _redis_client


async def close_redis_client():
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
