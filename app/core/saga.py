import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class SagaStep:
    name: str
    action: Callable
    compensation: Callable
    args: tuple = ()
    kwargs: dict = None

    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}


class Saga:
    def __init__(self, name: str):
        self.name = name
        self.steps: list[SagaStep] = []
        self.completed_steps: list[SagaStep] = []

    def add_step(
        self,
        name: str,
        action: Callable,
        compensation: Callable,
        *args,
        **kwargs,
    ):
        step = SagaStep(name, action, compensation, args, kwargs)
        self.steps.append(step)
        return self

    async def execute(self) -> Any:
        result = None

        try:
            for step in self.steps:
                if asyncio.iscoroutinefunction(step.action):
                    result = await step.action(*step.args, **step.kwargs)
                else:
                    result = step.action(*step.args, **step.kwargs)

                self.completed_steps.append(step)

            return result

        except Exception as e:
            await self._compensate()
            raise SagaFailureError(f"Saga {self.name} failed: {e}") from e

    async def _compensate(self):
        for step in reversed(self.completed_steps):
            try:
                if asyncio.iscoroutinefunction(step.compensation):
                    step.compensation(*step.args, **step.kwargs)
                else:
                    step.compensation(*step.args, **step.kwargs)

            except Exception as e:
                logger.error(
                    f"Saga {self.name}: compensation failed for {step.name}: {e}"
                )


class SagaFailureError(Exception):
    pass