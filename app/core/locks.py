import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from app.core.redis_client import get_redis_client
from app.config.settings import get_settings


class DistributedLock:
    def __init__(self, resource: str, timeout: Optional[int] = None):
        self.resource = resource
        self.settings = get_settings()
        self.timeout = timeout or self.settings.lock_timeout_seconds
        self.redis = None
        self.lock_key = f"lock:{resource}"
        self.lock_value = None

    async def initialize(self):
        if not self.redis:
            self.redis = await get_redis_client()

    async def acquire(self) -> bool:
        await self.initialize()

        import uuid
        self.lock_value = str(uuid.uuid4())

        await asyncio.sleep(0.01)

        acquired = await self.redis.set(
            self.lock_key, self.lock_value, nx=True, ex=self.timeout
        )

        return bool(acquired)

    async def release(self) -> bool:
        await self.initialize()

        if not self.lock_value:
            return False

        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        result = await self.redis.eval(
            lua_script, 1, self.lock_key, self.lock_value
        )

        return bool(result)

    async def extend(self, additional_time: int) -> bool:
        await self.initialize()

        if not self.lock_value:
            return False

        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """

        result = await self.redis.eval(
            lua_script, 1, self.lock_key, self.lock_value, additional_time
        )

        return bool(result)


@asynccontextmanager
async def distributed_lock(
    resource: str, timeout: Optional[int] = None, retry_count: int = 3
):
    lock = DistributedLock(resource, timeout)
    settings = get_settings()

    acquired = False
    for attempt in range(retry_count):
        if await lock.acquire():
            acquired = True
            break
        await asyncio.sleep(settings.lock_retry_delay_ms / 1000)

    if not acquired:
        raise TimeoutError(f"Failed to acquire lock for {resource}")

    try:
        yield lock
    finally:
        await lock.release()
