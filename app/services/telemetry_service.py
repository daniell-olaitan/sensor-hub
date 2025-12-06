from typing import Optional

from app.core.event_bus import get_event_bus
from app.core.rate_limiter import get_rate_limiter
from app.models.telemetry import TelemetryBatch, TelemetryPoint, TelemetryQuery
from app.services.alert_service import get_alert_service
from app.services.device_service import get_device_service
from app.storage.telemetry_store import get_telemetry_store


class TelemetryService:
    def __init__(self):
        self.store = get_telemetry_store()
        self.device_service = get_device_service()
        self.alert_service = get_alert_service()
        self.event_bus = get_event_bus()
        self.rate_limiter = get_rate_limiter()

    async def ingest_point(self, point: TelemetryPoint) -> None:
        allowed, remaining = await self.rate_limiter.check_device_rate_limit(
            point.device_id
        )

        if not allowed:
            raise ValueError(f"Rate limit exceeded for device {point.device_id}")

        await self.store.save_point(point)
        await self.device_service.mark_active(point.device_id)

        await self.alert_service.check_alerts(point)

        await self.event_bus.publish(
            "telemetry.ingested",
            "telemetry.point",
            {
                "device_id": point.device_id,
                "metric": point.metric,
                "value": point.value,
            },
        )

    async def ingest_batch(self, batch: TelemetryBatch) -> None:
        allowed, remaining = await self.rate_limiter.check_device_rate_limit(
            batch.device_id
        )

        if not allowed:
            raise ValueError(f"Rate limit exceeded for device {batch.device_id}")

        await self.store.save_batch(batch.points)
        await self.device_service.mark_active(batch.device_id)

        for point in batch.points:
            await self.alert_service.check_alerts(point)

        await self.event_bus.publish(
            "telemetry.ingested",
            "telemetry.batch",
            {
                "device_id": batch.device_id,
                "point_count": len(batch.points),
            },
        )

    async def query_telemetry(self, query: TelemetryQuery) -> list[TelemetryPoint]:
        return await self.store.query_points(
            query.device_id,
            query.metric,
            query.start_time,
            query.end_time,
            query.limit,
        )

    async def get_latest(self, device_id: str, metric: str) -> Optional[TelemetryPoint]:
        return await self.store.get_latest(device_id, metric)


_service = TelemetryService()


def get_telemetry_service() -> TelemetryService:
    return _service
