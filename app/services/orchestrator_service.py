import asyncio
from datetime import datetime

from app.core.event_bus import get_event_bus
from app.core.saga import Saga
from app.models.device import DeviceStatus
from app.models.firmware import UpdateStatus
from app.storage.device_store import get_device_store
from app.storage.firmware_store import get_firmware_store


class OrchestratorService:
    def __init__(self):
        self.firmware_store = get_firmware_store()
        self.device_store = get_device_store()
        self.event_bus = get_event_bus()

    async def orchestrate_firmware_update(self, update_id: str):
        update = await self.firmware_store.get_update(update_id)
        if not update:
            raise KeyError(f"Update {update_id} not found")

        saga = Saga(f"firmware_update_{update_id}")

        saga.add_step(
            "download",
            self._download_firmware,
            self._rollback_download,
            update_id,
        )

        saga.add_step(
            "set_maintenance",
            self._set_device_maintenance,
            self._restore_device_status,
            update.device_id,
        )

        saga.add_step(
            "install",
            self._install_firmware,
            self._rollback_install,
            update_id,
        )

        saga.add_step(
            "verify",
            self._verify_installation,
            self._rollback_verify,
            update_id,
        )

        try:
            await saga.execute()

            update.status = UpdateStatus.INSTALLED
            update.progress = 100
            update.completed_at = datetime.utcnow()
            await self.firmware_store.save_update(update)

            device = await self.device_store.get_device(update.device_id)
            device.firmware_version = update.to_version
            device.status = DeviceStatus.ACTIVE
            await self.device_store.save_device(device)

            await self.event_bus.publish(
                "firmware.updates",
                "update.completed",
                {"update_id": update_id, "device_id": update.device_id},
            )

        except Exception as e:
            update = await self.firmware_store.get_update(update_id)
            update.status = UpdateStatus.ROLLED_BACK
            update.error = str(e)
            update.completed_at = datetime.utcnow()
            await self.firmware_store.save_update(update)

            await self.event_bus.publish(
                "firmware.updates",
                "update.failed",
                {"update_id": update_id, "error": str(e)},
            )

    async def _download_firmware(self, update_id: str):
        update = await self.firmware_store.get_update(update_id)
        update.status = UpdateStatus.DOWNLOADING
        update.progress = 0
        await self.firmware_store.save_update(update)

        await asyncio.sleep(0.1)

        update.status = UpdateStatus.DOWNLOADED
        update.progress = 30
        await self.firmware_store.save_update(update)

        return {"update_id": update_id}

    async def _rollback_download(self, update_id: str):
        pass

    async def _set_device_maintenance(self, device_id: str):
        device = await self.device_store.get_device(device_id)

        original_context = {
            "device_id": device_id,
            "original_status": device.status,
            "original_metadata": device.metadata,
        }

        await asyncio.sleep(0.05)

        device.metadata["update_attempt_count"] = device.metadata.get(
            "update_attempt_count", 0
        ) + 1
        device.metadata["last_update_attempt"] = datetime.utcnow().isoformat()
        device.metadata["maintenance_reason"] = "firmware_update"
        device.status = DeviceStatus.MAINTENANCE
        await self.device_store.save_device(device)

        return original_context

    async def _restore_device_status(self, device_id: str):
        device = await self.device_store.get_device(device_id)
        device.status = DeviceStatus.ACTIVE
        device.metadata.pop("maintenance_reason", None)
        await self.device_store.save_device(device)

    async def _install_firmware(self, update_id: str):
        update = await self.firmware_store.get_update(update_id)
        device = await self.device_store.get_device(update.device_id)

        original_context = {
            "update_id": update_id,
            "device_id": update.device_id,
            "original_version": update.from_version,
        }

        update.status = UpdateStatus.INSTALLING
        update.progress = 50
        await self.firmware_store.save_update(update)

        await asyncio.sleep(0.1)

        device.firmware_version = update.to_version
        device.metadata["last_firmware_update"] = datetime.utcnow().isoformat()
        await self.device_store.save_device(device)

        update.progress = 80
        await self.firmware_store.save_update(update)

        return original_context

    async def _rollback_install(self, update_id: str):
        update = await self.firmware_store.get_update(update_id)
        device = await self.device_store.get_device(update.device_id)

        device.firmware_version = update.from_version
        device.metadata.pop("last_firmware_update", None)
        await self.device_store.save_device(device)

    async def _verify_installation(self, update_id: str):
        await asyncio.sleep(0.05)
        raise Exception("Installation verification failed: checksum mismatch")

    async def _rollback_verify(self, update_id: str):
        pass


_service = OrchestratorService()


def get_orchestrator_service() -> OrchestratorService:
    return _service