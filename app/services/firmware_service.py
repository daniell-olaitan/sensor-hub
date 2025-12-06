import uuid
from datetime import datetime

from app.core.event_bus import get_event_bus
from app.models.firmware import (
    FirmwareMetadata,
    FirmwareUpdate,
    FirmwareUpdateRequest,
    UpdateStatus,
)
from app.services.device_service import get_device_service
from app.services.orchestrator_service import get_orchestrator_service
from app.storage.firmware_store import get_firmware_store


class FirmwareService:
    def __init__(self):
        self.store = get_firmware_store()
        self.device_service = get_device_service()
        self.orchestrator = get_orchestrator_service()
        self.event_bus = get_event_bus()

    async def initiate_update(self, request: FirmwareUpdateRequest) -> FirmwareUpdate:
        device = await self.device_service.get_device(request.device_id)

        existing = await self.store.get_device_update(request.device_id)
        if existing and existing.status in [
            UpdateStatus.PENDING,
            UpdateStatus.DOWNLOADING,
            UpdateStatus.INSTALLING,
        ]:
            if not request.force:
                return existing

        metadata = await self.store.get_metadata(request.to_version)
        if not metadata:
            raise ValueError(f"Version {request.to_version} not found")

        update = FirmwareUpdate(
            id=str(uuid.uuid4()),
            device_id=request.device_id,
            from_version=device.firmware_version,
            to_version=request.to_version,
            status=UpdateStatus.PENDING,
            started_at=datetime.utcnow(),
        )

        await self.store.save_update(update)

        await self.orchestrator.orchestrate_firmware_update(update.id)

        return update

    async def get_update(self, update_id: str) -> FirmwareUpdate:
        update = await self.store.get_update(update_id)
        if not update:
            raise KeyError(f"Update {update_id} not found")
        return update

    async def register_firmware(self, metadata: FirmwareMetadata) -> None:
        await self.store.save_metadata(metadata)

        await self.event_bus.publish(
            "firmware.catalog",
            "firmware.registered",
            {"version": metadata.version},
        )

    async def list_versions(self) -> list[str]:
        return await self.store.list_versions()


_service = FirmwareService()


def get_firmware_service() -> FirmwareService:
    return _service
