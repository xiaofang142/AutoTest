from abc import ABC, abstractmethod
from typing import Optional
from app.domain.models.run import StepExecutionRecord
from app.domain.models.scenario import TestStep


class ExecutorClient(ABC):
    @property
    @abstractmethod
    def mode(self) -> str:
        """返回执行器类型，始终为 'real'"""
        ...

    @abstractmethod
    async def ping(self) -> bool:
        """健康检查"""
        ...

    @abstractmethod
    async def execute_step(self, step: TestStep, context: Optional[dict] = None) -> StepExecutionRecord:
        ...

    @abstractmethod
    async def take_screenshot(self) -> str:
        ...

    @abstractmethod
    async def get_page_state(self) -> dict:
        ...
