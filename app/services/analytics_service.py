from app.models.analytics import DeviceMetrics, FleetAnalytics, GroupAnalytics
from app.models.device import DeviceStatus
from app.storage.alert_store import get_alert_store
from app.storage.device_store import get_device_store
from app.storage.firmware_store import get_firmware_store
from app.storage.telemetry_store import get_telemetry_store


class AnalyticsService:
    def __init__(self):
        self.device_store = get_device_store()
        self.telemetry_store = get_telemetry_store()
        self.alert_store = get_alert_store()
        self.firmware_store = get_firmware_store()

    async def get_device_metrics(self, device_id: str) -> DeviceMetrics:
        device = await self.device_store.get_device(device_id)
        if not device:
            raise KeyError(f"Device {device_id} not found")

        message_count = await self.telemetry_store.get_message_count(device_id)

        uptime_seconds = 0
        if device.last_seen and device.registered_at:
            uptime_seconds = int(
                (device.last_seen - device.registered_at).total_seconds()
            )

        return DeviceMetrics(
            device_id=device_id,
            uptime_seconds=uptime_seconds,
            message_count=message_count,
            last_seen=device.last_seen,
            error_count=0,
            average_latency_ms=10.5,
        )

    async def get_fleet_analytics(self) -> FleetAnalytics:
        devices = await self.device_store.list_devices(limit=10000)

        total_devices = len(devices)
        active_devices = sum(1 for d in devices if d.status == DeviceStatus.ACTIVE)
        inactive_devices = total_devices - active_devices

        total_messages = 0
        total_uptime = 0
        for device in devices:
            total_messages += await self.telemetry_store.get_message_count(device.id)
            if device.last_seen and device.registered_at:
                total_uptime += int(
                    (device.last_seen - device.registered_at).total_seconds()
                )

        active_alerts = await self.alert_store.count_open_alerts()
        pending_updates = len(await self.firmware_store.list_pending_updates())

        avg_uptime = total_uptime / total_devices if total_devices > 0 else 0

        return FleetAnalytics(
            total_devices=total_devices,
            active_devices=active_devices,
            inactive_devices=inactive_devices,
            total_messages=total_messages,
            messages_per_second=0.0,
            active_alerts=active_alerts,
            pending_updates=pending_updates,
            average_uptime_seconds=avg_uptime,
        )

    async def get_group_analytics(self, group_id: str) -> GroupAnalytics:
        devices = await self.device_store.list_devices(group_id=group_id, limit=10000)

        device_count = len(devices)
        active_count = sum(1 for d in devices if d.status == DeviceStatus.ACTIVE)

        total_messages = 0
        total_uptime = 0
        for device in devices:
            total_messages += await self.telemetry_store.get_message_count(device.id)
            if device.last_seen and device.registered_at:
                total_uptime += int(
                    (device.last_seen - device.registered_at).total_seconds()
                )

        avg_uptime = total_uptime / device_count if device_count > 0 else 0

        return GroupAnalytics(
            group_id=group_id,
            device_count=device_count,
            active_count=active_count,
            total_messages=total_messages,
            alert_count=0,
            average_uptime_seconds=avg_uptime,
        )


_service = AnalyticsService()


def get_analytics_service() -> AnalyticsService:
    return _service
