from abc import ABC, abstractmethod
from app.domain.models.run import StepExecutionRecord
from app.domain.models.scenario import TestStep


class ExecutorClient(ABC):
    @abstractmethod
    async def execute_step(self, step: TestStep, context: dict) -> StepExecutionRecord:
        ...

    @abstractmethod
    async def take_screenshot(self) -> str:
        ...

    @abstractmethod
    async def get_page_state(self) -> dict:
        ...
