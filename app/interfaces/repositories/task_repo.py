"""TaskRepository 仓储接口。"""
from abc import ABC, abstractmethod
from app.domain.models.task import TestTask


class TaskRepository(ABC):
    @abstractmethod
    async def create(self, task: TestTask) -> TestTask:
        ...

    @abstractmethod
    async def get_by_id(self, task_id: str) -> TestTask | None:
        ...

    @abstractmethod
    async def list_tasks(
        self, project_id: str = "", status: str = "",
        page: int = 1, page_size: int = 20,
    ) -> dict:
        ...

    @abstractmethod
    async def update_status(self, task_id: str, status: str, stage: str = "") -> None:
        ...

    @abstractmethod
    async def update_progress(self, task_id: str, percent: int) -> None:
        ...

    @abstractmethod
    async def update_stage_result(self, task_id: str, stage: str, data: dict) -> None:
        ...

    @abstractmethod
    async def update_delivery(self, task_id: str, delivery: dict) -> None:
        ...

    @abstractmethod
    async def delete(self, task_id: str) -> None:
        ...
