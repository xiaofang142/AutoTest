from abc import ABC, abstractmethod
from app.domain.models.run import RunRecord, StepExecutionRecord


class RunRepository(ABC):
    @abstractmethod
    async def create(self, run: RunRecord) -> RunRecord:
        ...

    @abstractmethod
    async def get_by_id(self, run_id: str) -> RunRecord | None:
        ...

    @abstractmethod
    async def get_by_project(self, project_id: str) -> list[RunRecord]:
        ...

    @abstractmethod
    async def update_status(self, run_id: str, status: str) -> None:
        ...

    @abstractmethod
    async def update_progress(self, run_id: str, progress: dict) -> None:
        ...

    @abstractmethod
    async def save_step(self, step: StepExecutionRecord) -> StepExecutionRecord:
        ...

    @abstractmethod
    async def get_steps(self, run_id: str) -> list[StepExecutionRecord]:
        ...
