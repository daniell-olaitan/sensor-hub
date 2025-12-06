from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TelemetryPoint(BaseModel):
    device_id: str
    timestamp: datetime
    metric: str
    value: Any
    unit: str = ""
    metadata: dict = Field(default_factory=dict)


class TelemetryBatch(BaseModel):
    device_id: str
    points: list[TelemetryPoint]


class TelemetryQuery(BaseModel):
    device_id: str
    metric: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100
