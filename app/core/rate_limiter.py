import time

from app.config.settings import get_settings
from app.core.redis_client import get_redis_client


class RateLimiter:
    def __init__(self):
        self.redis = None
        self.settings = get_settings()

    async def initialize(self):
        if not self.redis:
            self.redis = await get_redis_client()

    async def check_rate_limit(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        await self.initialize()

        now = int(time.time() * 1000)
        window_start = now - (window_seconds * 1000)
        key = f"ratelimit:{identifier}"

        lua_script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local window_start = tonumber(ARGV[2])
        local max_requests = tonumber(ARGV[3])
        local window_seconds = tonumber(ARGV[4])

        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

        local current_count = redis.call('ZCARD', key)

        if current_count < max_requests then
            redis.call('ZADD', key, now, now)
            redis.call('EXPIRE', key, window_seconds * 2)
            return {1, max_requests - current_count - 1}
        else
            return {0, 0}
        end
        """

        result = await self.redis.eval(
            lua_script,
            1,
            key,
            now,
            window_start,
            max_requests,
            window_seconds,
        )

        allowed = bool(result[0])
        remaining = int(result[1])

        return allowed, remaining

    async def check_device_rate_limit(self, device_id: str) -> tuple[bool, int]:
        return await self.check_rate_limit(
            f"device:{device_id}",
            self.settings.rate_limit_telemetry_per_device,
            self.settings.rate_limit_window_seconds,
        )

    async def check_global_rate_limit(self) -> tuple[bool, int]:
        return await self.check_rate_limit(
            "global",
            self.settings.rate_limit_global_per_second,
            1,
        )


_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    return _rate_limiter
