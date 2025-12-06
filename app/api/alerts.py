from typing import Optional

from fastapi import APIRouter

from app.models.alert import Alert, AlertRule, AlertRuleCreate, AlertStatus
from app.services.alert_service import get_alert_service

router = APIRouter()


@router.post("/rules", response_model=AlertRule, status_code=201)
async def create_rule(rule: AlertRuleCreate):
    service = get_alert_service()
    return await service.create_rule(rule)


@router.get("/rules/{rule_id}", response_model=AlertRule)
async def get_rule(rule_id: str):
    service = get_alert_service()
    return await service.get_rule(rule_id)


@router.get("/rules", response_model=list[AlertRule])
async def list_rules(device_id: Optional[str] = None):
    service = get_alert_service()
    return await service.list_rules(device_id)


@router.get("", response_model=list[Alert])
async def list_alerts(
    device_id: Optional[str] = None,
    status: Optional[AlertStatus] = None,
    limit: int = 100,
):
    service = get_alert_service()
    return await service.list_alerts(device_id, status, limit)


@router.post("/{alert_id}/acknowledge", response_model=Alert)
async def acknowledge_alert(alert_id: str):
    service = get_alert_service()
    return await service.acknowledge_alert(alert_id)


@router.post("/{alert_id}/resolve", response_model=Alert)
async def resolve_alert(alert_id: str):
    service = get_alert_service()
    return await service.resolve_alert(alert_id)
