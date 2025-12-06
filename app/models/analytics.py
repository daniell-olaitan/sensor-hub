from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DeviceMetrics(BaseModel):
    device_id: str
    uptime_seconds: int
    message_count: int
    last_seen: Optional[datetime]
    error_count: int
    average_latency_ms: float


class FleetAnalytics(BaseModel):
    total_devices: int
    active_devices: int
    inactive_devices: int
    total_messages: int
    messages_per_second: float
    active_alerts: int
    pending_updates: int
    average_uptime_seconds: float


class GroupAnalytics(BaseModel):
    group_id: str
    device_count: int
    active_count: int
    total_messages: int
    alert_count: int
    average_uptime_seconds: float
