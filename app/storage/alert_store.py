from datetime import datetime
from typing import Optional

from app.core.redis_client import get_redis_client
from app.models.alert import Alert, AlertRule, AlertStatus


class AlertStore:
    def __init__(self):
        self.redis = None

    async def initialize(self):
        if not self.redis:
            self.redis = await get_redis_client()

    async def save_rule(self, rule: AlertRule) -> None:
        await self.initialize()
        key = f"alert:rule:{rule.id}"
        await self.redis.set(key, rule.model_dump_json())
        await self.redis.sadd("alert:rules:all", rule.id)

        if rule.device_id:
            await self.redis.sadd(f"alert:rules:device:{rule.device_id}", rule.id)
        if rule.group_id:
            await self.redis.sadd(f"alert:rules:group:{rule.group_id}", rule.id)

    async def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        await self.initialize()
        data = await self.redis.get(f"alert:rule:{rule_id}")
        if not data:
            return None
        return AlertRule.model_validate_json(data)

    async def list_rules(
        self, device_id: Optional[str] = None, enabled_only: bool = True
    ) -> list[AlertRule]:
        await self.initialize()

        if device_id:
            rule_ids = await self.redis.smembers(f"alert:rules:device:{device_id}")
        else:
            rule_ids = await self.redis.smembers("alert:rules:all")

        rules = []
        for rule_id in rule_ids:
            rule = await self.get_rule(rule_id.decode())
            if rule and (not enabled_only or rule.enabled):
                rules.append(rule)

        return rules

    async def save_alert(self, alert: Alert) -> None:
        await self.initialize()
        key = f"alert:{alert.id}"

        async with self.redis.pipeline() as pipe:
            pipe.set(key, alert.model_dump_json())
            pipe.zadd(
                "alert:timeline",
                {alert.id: int(alert.triggered_at.timestamp())},
            )
            pipe.sadd(f"alert:device:{alert.device_id}", alert.id)

            if alert.status == AlertStatus.OPEN:
                pipe.sadd("alert:open", alert.id)

            await pipe.execute()

    async def get_alert(self, alert_id: str) -> Optional[Alert]:
        await self.initialize()
        data = await self.redis.get(f"alert:{alert_id}")
        if not data:
            return None
        return Alert.model_validate_json(data)

    async def list_alerts(
        self,
        device_id: Optional[str] = None,
        status: Optional[AlertStatus] = None,
        limit: int = 100,
    ) -> list[Alert]:
        await self.initialize()

        if status == AlertStatus.OPEN:
            alert_ids = await self.redis.smembers("alert:open")
        elif device_id:
            alert_ids = await self.redis.smembers(f"alert:device:{device_id}")
        else:
            alert_ids = await self.redis.zrange("alert:timeline", 0, limit - 1)

        alerts = []
        for alert_id in list(alert_ids)[:limit]:
            alert = await self.get_alert(alert_id.decode())
            if alert:
                if status and alert.status != status:
                    continue
                alerts.append(alert)

        return sorted(alerts, key=lambda a: a.triggered_at, reverse=True)

    async def update_alert_status(self, alert_id: str, status: AlertStatus) -> Alert:
        await self.initialize()
        alert = await self.get_alert(alert_id)
        if not alert:
            raise KeyError(f"Alert {alert_id} not found")

        alert.status = status
        if status == AlertStatus.ACKNOWLEDGED:
            alert.acknowledged_at = datetime.utcnow()
        elif status == AlertStatus.RESOLVED:
            alert.resolved_at = datetime.utcnow()

        await self.save_alert(alert)

        if status != AlertStatus.OPEN:
            await self.redis.srem("alert:open", alert_id)

        return alert

    async def count_open_alerts(self) -> int:
        await self.initialize()
        return await self.redis.scard("alert:open")


_store = AlertStore()


def get_alert_store() -> AlertStore:
    return _store
