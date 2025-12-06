from fastapi import APIRouter

from app.models.firmware import FirmwareMetadata, FirmwareUpdate, FirmwareUpdateRequest
from app.services.firmware_service import get_firmware_service

router = APIRouter()


@router.post("/updates", response_model=FirmwareUpdate, status_code=201)
async def initiate_update(request: FirmwareUpdateRequest):
    service = get_firmware_service()
    return await service.initiate_update(request)


@router.get("/updates/{update_id}", response_model=FirmwareUpdate)
async def get_update(update_id: str):
    service = get_firmware_service()
    return await service.get_update(update_id)


@router.post("/register", status_code=201)
async def register_firmware(metadata: FirmwareMetadata):
    service = get_firmware_service()
    await service.register_firmware(metadata)
    return {"status": "registered", "version": metadata.version}


@router.get("/versions", response_model=list[str])
async def list_versions():
    service = get_firmware_service()
    return await service.list_versions()
