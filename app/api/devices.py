from typing import Optional

from fastapi import APIRouter, Header

from app.models.device import Device, DeviceRegistration, DeviceUpdate
from app.services.device_service import get_device_service

router = APIRouter()


@router.post("", response_model=Device, status_code=201)
async def register_device(
    registration: DeviceRegistration,
    idempotency_key: str = Header(..., alias="idempotency-key"),
):
    service = get_device_service()
    return await service.register_device(registration, idempotency_key)


@router.get("/{device_id}", response_model=Device)
async def get_device(device_id: str):
    service = get_device_service()
    return await service.get_device(device_id)


@router.patch("/{device_id}", response_model=Device)
async def update_device(device_id: str, updates: DeviceUpdate):
    service = get_device_service()
    return await service.update_device(device_id, updates)


@router.get("", response_model=list[Device])
async def list_devices(group_id: Optional[str] = None, limit: int = 100):
    service = get_device_service()
    return await service.list_devices(group_id, limit)
