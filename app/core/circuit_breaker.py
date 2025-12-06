import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = None,
        timeout_seconds: int = None,
        half_open_max_calls: int = None,
    ):
        self.name = name
        settings = get_settings()
        self.failure_threshold = (
            failure_threshold or settings.circuit_breaker_failure_threshold
        )
        self.timeout_seconds = (
            timeout_seconds or settings.circuit_breaker_timeout_seconds
        )
        self.half_open_max_calls = (
            half_open_max_calls or settings.circuit_breaker_half_open_max_calls
        )

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                self.success_count = 0
            else:
                raise CircuitBreakerOpenError(f"Circuit breaker {self.name} is open")

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker {self.name} half-open limit reached"
                )
            self.half_open_calls += 1

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.success_count = 0
                self.failure_count = 0
        else:
            self.failure_count = 0

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.success_count = 0
            self.half_open_calls = 0
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        if not self.last_failure_time:
            return True

        elapsed = datetime.utcnow() - self.last_failure_time
        return elapsed > timedelta(seconds=self.timeout_seconds)

    def get_state(self) -> CircuitState:
        return self.state


class CircuitBreakerOpenError(Exception):
    pass


_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name)
    return _circuit_breakers[name]
