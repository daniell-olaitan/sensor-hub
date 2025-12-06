from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class RuleOperator(str, Enum):
    GT = "gt"
    LT = "lt"
    EQ = "eq"
    NE = "ne"


class AlertRule(BaseModel):
    id: str
    device_id: Optional[str] = None
    group_id: Optional[str] = None
    metric: str
    operator: RuleOperator
    threshold: float
    severity: AlertSeverity
    enabled: bool = True
    created_at: datetime


class Alert(BaseModel):
    id: str
    rule_id: str
    device_id: str
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.OPEN
    message: str
    value: float
    threshold: float
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class AlertRuleCreate(BaseModel):
    device_id: Optional[str] = None
    group_id: Optional[str] = None
    metric: str
    operator: RuleOperator
    threshold: float
    severity: AlertSeverity
