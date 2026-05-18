"""InMemory TaskRepository 实现。"""
import asyncio

from app.domain.models.task import (
    TestTask, EnvironmentCheck, UnderstandingResult, TestBlueprint, DeliveryPackage,
)
from app.interfaces.repositories.task_repo import TaskRepository
from app.lib.id_generator import generate_id

_MAX_TASKS = 10000


class InMemoryTaskRepository(TaskRepository):
    def __init__(self):
        self._tasks: dict[str, TestTask] = {}
        self._lock = asyncio.Lock()

    async def create(self, task: TestTask) -> TestTask:
        async with self._lock:
            if len(self._tasks) >= _MAX_TASKS:
                oldest = min(self._tasks.keys(), key=lambda k: self._tasks[k].created_at)
                del self._tasks[oldest]
            task.id = generate_id("task")
            self._tasks[task.id] = task
            return task

    async def get_by_id(self, task_id: str) -> TestTask | None:
        async with self._lock:
            return self._tasks.get(task_id)

    async def list_tasks(
        self, project_id: str = "", status: str = "",
        page: int = 1, page_size: int = 20,
    ) -> dict:
        async with self._lock:
            items = list(self._tasks.values())
            if project_id:
                items = [t for t in items if t.project_id == project_id]
            if status:
                items = [t for t in items if t.status == status]
            items.sort(key=lambda t: t.created_at, reverse=True)
            total = len(items)
            start = (page - 1) * page_size
            return {
                "items": [t.model_dump(mode="json") for t in items[start:start + page_size]],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    async def update_status(self, task_id: str, status: str, stage: str = "") -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = status
                if stage:
                    task.current_stage = stage

    async def update_progress(self, task_id: str, percent: int) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.progress_percent = percent

    async def update_stage_result(self, task_id: str, stage: str, data: dict) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                model_map = {
                    "environment_check": EnvironmentCheck,
                    "understanding": UnderstandingResult,
                    "blueprint": TestBlueprint,
                }
                model_cls = model_map.get(stage)
                if model_cls:
                    setattr(task, stage, model_cls(**data))
                else:
                    setattr(task, stage, data)

    async def update_delivery(self, task_id: str, delivery: dict) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.delivery = DeliveryPackage(**delivery)
                task.delivery_ready = True

    async def delete(self, task_id: str) -> None:
        async with self._lock:
            self._tasks.pop(task_id, None)
