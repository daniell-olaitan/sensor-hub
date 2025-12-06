import asyncio
import logging
from collections import defaultdict
from typing import Callable

from app.config.settings import get_settings
from app.storage.event_store import get_event_store

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self):
        self.subscribers: dict[str, list[Callable]] = defaultdict(list)
        self.settings = get_settings()
        self.queue: asyncio.Queue = None
        self.workers: list[asyncio.Task] = []
        self.running = False
        self.event_store = get_event_store()

    async def start(self):
        self.queue = asyncio.Queue(maxsize=self.settings.event_bus_queue_max_size)
        self.running = True

        for i in range(self.settings.event_bus_worker_count):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)

        logger.info(
            f"Event bus started with {self.settings.event_bus_worker_count} workers"
        )

    async def stop(self):
        self.running = False

        for worker in self.workers:
            worker.cancel()

        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

        logger.info("Event bus stopped")

    def subscribe(self, topic: str, handler: Callable):
        self.subscribers[topic].append(handler)

    async def publish(self, topic: str, event_type: str, payload: dict):
        event = {
            "topic": topic,
            "type": event_type,
            "payload": payload,
        }

        await self.event_store.append_event(topic, event_type, payload)

        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.error(f"Event queue full, dropping event: {topic}/{event_type}")

    async def _worker(self, worker_id: int):
        logger.info(f"Event bus worker {worker_id} started")

        while self.running:
            try:
                event = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                await self._process_event(event)
                self.queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")

        logger.info(f"Event bus worker {worker_id} stopped")

    async def _process_event(self, event: dict):
        topic = event["topic"]
        handlers = self.subscribers.get(topic, [])

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in event handler for {topic}: {e}", exc_info=True)

    def get_queue_size(self) -> int:
        return self.queue.qsize() if self.queue else 0


_event_bus = EventBus()


def get_event_bus() -> EventBus:
    return _event_bus
