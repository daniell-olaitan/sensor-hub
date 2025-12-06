from datetime import datetime
from typing import Optional

from app.config.settings import get_settings
from app.core.redis_client import get_redis_client
from app.models.telemetry import TelemetryPoint


class TelemetryStore:
    def __init__(self):
        self.redis = None
        self.settings = get_settings()

    async def initialize(self):
        if not self.redis:
            self.redis = await get_redis_client()

    async def save_point(self, point: TelemetryPoint) -> None:
        await self.initialize()

        ts = int(point.timestamp.timestamp())
        key = f"telemetry:{point.device_id}:{point.metric}"

        await self.redis.zadd(
            key,
            {point.model_dump_json(): ts},
        )
        await self.redis.expire(key, self.settings.telemetry_retention_seconds)

        await self.redis.incr(f"telemetry:count:{point.device_id}")

    async def save_batch(self, points: list[TelemetryPoint]) -> None:
        await self.initialize()

        async with self.redis.pipeline() as pipe:
            for point in points:
                ts = int(point.timestamp.timestamp())
                key = f"telemetry:{point.device_id}:{point.metric}"
                pipe.zadd(key, {point.model_dump_json(): ts})
                pipe.expire(key, self.settings.telemetry_retention_seconds)

            if points:
                pipe.incrby(f"telemetry:count:{points[0].device_id}", len(points))

            await pipe.execute()

    async def query_points(
        self,
        device_id: str,
        metric: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[TelemetryPoint]:
        await self.initialize()

        if metric:
            keys = [f"telemetry:{device_id}:{metric}"]
        else:
            pattern = f"telemetry:{device_id}:*"
            keys = [k.decode() for k in await self.redis.keys(pattern)]

        min_score = int(start_time.timestamp()) if start_time else "-inf"
        max_score = int(end_time.timestamp()) if end_time else "+inf"

        points = []
        for key in keys:
            results = await self.redis.zrangebyscore(
                key, min_score, max_score, start=0, num=limit
            )
            for result in results:
                points.append(TelemetryPoint.model_validate_json(result))

        return sorted(points, key=lambda p: p.timestamp, reverse=True)[:limit]

    async def get_latest(self, device_id: str, metric: str) -> Optional[TelemetryPoint]:
        await self.initialize()
        key = f"telemetry:{device_id}:{metric}"
        results = await self.redis.zrange(key, -1, -1)
        if not results:
            return None
        return TelemetryPoint.model_validate_json(results[0])

    async def get_message_count(self, device_id: str) -> int:
        await self.initialize()
        count = await self.redis.get(f"telemetry:count:{device_id}")
        return int(count) if count else 0


_store = TelemetryStore()


def get_telemetry_store() -> TelemetryStore:
    return _store
