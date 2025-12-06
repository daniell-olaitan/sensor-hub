from datetime import datetime
from typing import Optional
import uuid
import asyncio

from app.models.device import Device, DeviceRegistration, DeviceUpdate
from app.storage.device_store import get_device_store
from app.core.event_bus import get_event_bus


class DeviceService:
    def __init__(self):
        self.store = get_device_store()
        self.event_bus = get_event_bus()

    async def register_device(
        self, registration: DeviceRegistration, idempotency_key: str
    ) -> Device:
        existing = await self.store.get_device_by_serial(
            registration.serial_number
        )
        if existing:
            return existing

        await asyncio.sleep(0.01)

        device = Device(
            id=str(uuid.uuid4()),
            serial_number=registration.serial_number,
            device_type=registration.device_type,
            firmware_version=registration.firmware_version,
            metadata=registration.metadata,
            registered_at=datetime.utcnow(),
            location=registration.location,
            group_id=registration.group_id,
        )

        await self.store.save_device(device)

        await self.event_bus.publish(
            "device.lifecycle",
            "device.registered",
            {"device_id": device.id, "serial_number": device.serial_number},
        )

        return device

    async def get_device(self, device_id: str) -> Device:
        device = await self.store.get_device(device_id)
        if not device:
            raise KeyError(f"Device {device_id} not found")
        return device

    async def update_device(
        self, device_id: str, updates: DeviceUpdate
    ) -> Device:
        update_dict = updates.model_dump(exclude_unset=True)
        device = await self.store.update_device(device_id, update_dict)

        await self.event_bus.publish(
            "device.lifecycle",
            "device.updated",
            {"device_id": device_id, "updates": update_dict},
        )

        return device

    async def list_devices(
        self, group_id: Optional[str] = None, limit: int = 100
    ) -> list[Device]:
        return await self.store.list_devices(group_id, limit)

    async def mark_active(self, device_id: str):
        await self.store.update_last_seen(device_id)


_service = DeviceService()


def get_device_service() -> DeviceService:
    return _service