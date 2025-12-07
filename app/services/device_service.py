import asyncio
import uuid
from datetime import datetime
from typing import Optional

from app.core.event_bus import get_event_bus
from app.core.redis_client import get_redis_client
from app.models.device import Device, DeviceRegistration, DeviceUpdate
from app.storage.device_store import get_device_store


class DeviceService:
    def __init__(self):
        self.store = get_device_store()
        self.event_bus = get_event_bus()

    async def register_device(
        self, registration: DeviceRegistration, idempotency_key: str
    ) -> Device:
        redis = await get_redis_client()
        serial_key = f"device:serial:{registration.serial_number}"

        for attempt in range(10):
            existing_id = await redis.get(serial_key)
            if existing_id:
                device = await self.store.get_device(existing_id.decode())
                if device:
                    return device

            device_id = str(uuid.uuid4())
            device = Device(
                id=device_id,
                serial_number=registration.serial_number,
                device_type=registration.device_type,
                firmware_version=registration.firmware_version,
                metadata=registration.metadata,
                registered_at=datetime.utcnow(),
                location=registration.location,
                group_id=registration.group_id,
            )

            success = await redis.set(serial_key, device_id, nx=True, ex=3600)

            if success:
                await self.store.save_device(device)

                await self.event_bus.publish(
                    "device.lifecycle",
                    "device.registered",
                    {"device_id": device.id, "serial_number": device.serial_number},
                )

                return device

            await asyncio.sleep(0.01 * (attempt + 1))

        existing_id = await redis.get(serial_key)
        if existing_id:
            device = await self.store.get_device(existing_id.decode())
            if device:
                return device

        raise Exception(f"Failed to register device {registration.serial_number}")

    async def get_device(self, device_id: str) -> Device:
        device = await self.store.get_device(device_id)
        if not device:
            raise KeyError(f"Device {device_id} not found")
        return device

    async def update_device(self, device_id: str, updates: DeviceUpdate) -> Device:
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
