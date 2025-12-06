from fastapi import APIRouter

from app.models.analytics import DeviceMetrics, FleetAnalytics, GroupAnalytics
from app.services.analytics_service import get_analytics_service

router = APIRouter()


@router.get("/devices/{device_id}", response_model=DeviceMetrics)
async def get_device_metrics(device_id: str):
    service = get_analytics_service()
    return await service.get_device_metrics(device_id)


@router.get("/fleet", response_model=FleetAnalytics)
async def get_fleet_analytics():
    service = get_analytics_service()
    return await service.get_fleet_analytics()


@router.get("/groups/{group_id}", response_model=GroupAnalytics)
async def get_group_analytics(group_id: str):
    service = get_analytics_service()
    return await service.get_group_analytics(group_id)
