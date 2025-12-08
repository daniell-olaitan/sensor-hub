from typing import Optional

from app.core.redis_client import get_redis_client
from app.models.firmware import FirmwareMetadata, FirmwareUpdate, UpdateStatus


class FirmwareStore:
    def __init__(self):
        self.redis = None

    async def initialize(self):
        if not self.redis:
            self.redis = await get_redis_client()

    async def save_update(self, update: FirmwareUpdate) -> None:
        await self.initialize()
        key = f"firmware:update:{update.id}"

        existing_data = await self.redis.get(key)
        if existing_data:
            existing = FirmwareUpdate.model_validate_json(existing_data)
            if existing.status == UpdateStatus.FAILED:
                return

        async with self.redis.pipeline() as pipe:
            pipe.set(key, update.model_dump_json())
            pipe.set(f"firmware:device:{update.device_id}", update.id)

            if update.status == UpdateStatus.PENDING:
                pipe.sadd("firmware:pending", update.id)
            elif update.status in [
                UpdateStatus.INSTALLED,
                UpdateStatus.FAILED,
                UpdateStatus.ROLLED_BACK,
            ]:
                pipe.srem("firmware:pending", update.id)

            await pipe.execute()

    async def get_update(self, update_id: str) -> Optional[FirmwareUpdate]:
        await self.initialize()
        data = await self.redis.get(f"firmware:update:{update_id}")
        if not data:
            return None
        return FirmwareUpdate.model_validate_json(data)

    async def get_device_update(self, device_id: str) -> Optional[FirmwareUpdate]:
        await self.initialize()
        update_id = await self.redis.get(f"firmware:device:{device_id}")
        if not update_id:
            return None
        return await self.get_update(update_id.decode())

    async def list_pending_updates(self) -> list[FirmwareUpdate]:
        await self.initialize()
        update_ids = await self.redis.smembers("firmware:pending")

        updates = []
        for update_id in update_ids:
            update = await self.get_update(update_id.decode())
            if update:
                updates.append(update)

        return updates

    async def save_metadata(self, metadata: FirmwareMetadata) -> None:
        await self.initialize()
        key = f"firmware:metadata:{metadata.version}"
        await self.redis.set(key, metadata.model_dump_json())
        await self.redis.sadd("firmware:versions", metadata.version)

    async def get_metadata(self, version: str) -> Optional[FirmwareMetadata]:
        await self.initialize()
        data = await self.redis.get(f"firmware:metadata:{version}")
        if not data:
            return None
        return FirmwareMetadata.model_validate_json(data)

    async def list_versions(self) -> list[str]:
        await self.initialize()
        versions = await self.redis.smembers("firmware:versions")
        return [v.decode() for v in versions]


_store = FirmwareStore()


def get_firmware_store() -> FirmwareStore:
    return _store