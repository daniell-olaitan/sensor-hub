import uuid
from datetime import datetime
from typing import Optional

from app.core.circuit_breaker import get_circuit_breaker
from app.core.event_bus import get_event_bus
from app.models.alert import (
    Alert,
    AlertRule,
    AlertRuleCreate,
    AlertStatus,
    RuleOperator,
)
from app.models.telemetry import TelemetryPoint
from app.storage.alert_store import get_alert_store


class AlertService:
    def __init__(self):
        self.store = get_alert_store()
        self.event_bus = get_event_bus()
        self.notification_cb = get_circuit_breaker("notification_service")
        self.notification_call_count = 0

    async def create_rule(self, rule_create: AlertRuleCreate) -> AlertRule:
        rule = AlertRule(
            id=str(uuid.uuid4()),
            device_id=rule_create.device_id,
            group_id=rule_create.group_id,
            metric=rule_create.metric,
            operator=rule_create.operator,
            threshold=rule_create.threshold,
            severity=rule_create.severity,
            created_at=datetime.utcnow(),
        )

        await self.store.save_rule(rule)

        await self.event_bus.publish(
            "alert.rules",
            "rule.created",
            {"rule_id": rule.id},
        )

        return rule

    async def get_rule(self, rule_id: str) -> AlertRule:
        rule = await self.store.get_rule(rule_id)
        if not rule:
            raise KeyError(f"Rule {rule_id} not found")
        return rule

    async def list_rules(self, device_id: Optional[str] = None) -> list[AlertRule]:
        return await self.store.list_rules(device_id)

    async def check_alerts(self, point: TelemetryPoint) -> None:
        rules = await self.store.list_rules(point.device_id, enabled_only=True)

        for rule in rules:
            if rule.metric != point.metric:
                continue

            if self._evaluate_rule(rule, point.value):
                await self._trigger_alert(rule, point)

    def _evaluate_rule(self, rule: AlertRule, value: float) -> bool:
        threshold = rule.threshold

        if rule.operator == RuleOperator.GT:
            return value > threshold
        elif rule.operator == RuleOperator.LT:
            return value < threshold
        elif rule.operator == RuleOperator.EQ:
            return value == threshold
        elif rule.operator == RuleOperator.NE:
            return value != threshold

        return False

    async def _trigger_alert(self, rule: AlertRule, point: TelemetryPoint) -> None:
        alert = Alert(
            id=str(uuid.uuid4()),
            rule_id=rule.id,
            device_id=point.device_id,
            severity=rule.severity,
            message=f"{point.metric} {rule.operator.value} {rule.threshold}",
            value=point.value,
            threshold=rule.threshold,
            triggered_at=datetime.utcnow(),
        )

        await self.store.save_alert(alert)

        await self.event_bus.publish(
            "alert.triggered",
            "alert.new",
            {
                "alert_id": alert.id,
                "device_id": alert.device_id,
                "severity": alert.severity.value,
            },
        )

        try:
            await self.notification_cb.call(self._send_notification, alert)
        except Exception:
            pass

    async def _send_notification(self, alert: Alert):
        import asyncio

        await asyncio.sleep(0.01)

        self.notification_call_count += 1
        raise Exception("Notification service unavailable")

    async def list_alerts(
        self,
        device_id: Optional[str] = None,
        status: Optional[AlertStatus] = None,
        limit: int = 100,
    ) -> list[Alert]:
        return await self.store.list_alerts(device_id, status, limit)

    async def acknowledge_alert(self, alert_id: str) -> Alert:
        return await self.store.update_alert_status(alert_id, AlertStatus.ACKNOWLEDGED)

    async def resolve_alert(self, alert_id: str) -> Alert:
        return await self.store.update_alert_status(alert_id, AlertStatus.RESOLVED)


_service = AlertService()


def get_alert_service() -> AlertService:
    return _service
