from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DeviceStatus(str, Enum):
    REGISTERED = "registered"
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class DeviceType(str, Enum):
    SENSOR = "sensor"
    GATEWAY = "gateway"
    ACTUATOR = "actuator"
    HYBRID = "hybrid"


class Device(BaseModel):
    id: str
    serial_number: str
    device_type: DeviceType
    status: DeviceStatus = DeviceStatus.REGISTERED
    firmware_version: str
    metadata: dict = Field(default_factory=dict)
    registered_at: datetime
    last_seen: Optional[datetime] = None
    location: Optional[str] = None
    group_id: Optional[str] = None


class DeviceRegistration(BaseModel):
    serial_number: str
    device_type: DeviceType
    firmware_version: str
    metadata: dict = Field(default_factory=dict)
    location: Optional[str] = None
    group_id: Optional[str] = None


class DeviceUpdate(BaseModel):
    status: Optional[DeviceStatus] = None
    location: Optional[str] = None
    metadata: Optional[dict] = None
    group_id: Optional[str] = None
