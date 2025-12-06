import json
from datetime import datetime
from typing import Optional

from app.core.redis_client import get_redis_client


class EventStore:
    def __init__(self):
        self.redis = None

    async def initialize(self):
        if not self.redis:
            self.redis = await get_redis_client()

    async def append_event(self, topic: str, event_type: str, payload: dict) -> str:
        await self.initialize()

        event_id = f"{topic}:{int(datetime.utcnow().timestamp() * 1000000)}"
        event_data = {
            "id": event_id,
            "topic": topic,
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }

        key = f"events:{topic}"
        await self.redis.zadd(
            key,
            {json.dumps(event_data): int(datetime.utcnow().timestamp())},
        )
        await self.redis.expire(key, 86400)

        return event_id

    async def get_events(
        self, topic: str, start_time: Optional[datetime] = None, limit: int = 100
    ) -> list[dict]:
        await self.initialize()
        key = f"events:{topic}"

        min_score = int(start_time.timestamp()) if start_time else "-inf"

        results = await self.redis.zrangebyscore(
            key, min_score, "+inf", start=0, num=limit
        )

        return [json.loads(r) for r in results]


_store = EventStore()


def get_event_store() -> EventStore:
    return _store
