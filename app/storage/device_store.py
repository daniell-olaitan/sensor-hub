from datetime import datetime
from typing import Optional

from app.core.redis_client import get_redis_client
from app.models.device import Device, DeviceStatus


class DeviceStore:
    def __init__(self):
        self.redis = None
        self._device_cache = {}

    async def initialize(self):
        if not self.redis:
            self.redis = await get_redis_client()

    async def save_device(self, device: Device) -> None:
        await self.initialize()
        key = f"device:{device.id}"

        async with self.redis.pipeline() as pipe:
            pipe.set(key, device.model_dump_json())
            pipe.sadd("device:all", device.id)
            if device.group_id:
                pipe.sadd(f"device:group:{device.group_id}", device.id)
            await pipe.execute()

        self._device_cache[device.id] = device

    async def get_device(self, device_id: str) -> Optional[Device]:
        if device_id in self._device_cache:
            return self._device_cache[device_id]

        await self.initialize()
        key = f"device:{device_id}"
        data = await self.redis.get(key)
        if not data:
            return None
        device = Device.model_validate_json(data)
        self._device_cache[device_id] = device
        return device

    async def get_device_by_serial(self, serial: str) -> Optional[Device]:
        await self.initialize()
        device_id = await self.redis.get(f"device:serial:{serial}")
        if not device_id:
            return None
        return await self.get_device(device_id.decode())

    async def update_device(self, device_id: str, updates: dict) -> Device:
        await self.initialize()
        device = await self.get_device(device_id)
        if not device:
            raise KeyError(f"Device {device_id} not found")

        for key, value in updates.items():
            if hasattr(device, key) and value is not None:
                setattr(device, key, value)

        await self.save_device(device)
        return device

    async def list_devices(
        self, group_id: Optional[str] = None, limit: int = 100
    ) -> list[Device]:
        await self.initialize()

        if group_id:
            device_ids = await self.redis.smembers(f"device:group:{group_id}")
        else:
            device_ids = await self.redis.smembers("device:all")

        devices = []
        for device_id in list(device_ids)[:limit]:
            device = await self.get_device(device_id.decode())
            if device:
                devices.append(device)

        return devices

    async def update_last_seen(self, device_id: str) -> None:
        await self.initialize()
        device = await self.get_device(device_id)
        if device:
            device.last_seen = datetime.utcnow()
            device.status = DeviceStatus.ACTIVE
            await self.save_device(device)

    async def exists_by_serial(self, serial_number: str) -> bool:
        await self.initialize()
        return await self.redis.exists(f"device:serial:{serial_number}") > 0


_store = DeviceStore()


def get_device_store() -> DeviceStore:
    return _store