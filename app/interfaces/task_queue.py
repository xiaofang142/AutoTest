from abc import ABC, abstractmethod


class TaskQueueService(ABC):
    @abstractmethod
    async def enqueue(self, task_type: str, payload: dict) -> str:
        ...

    @abstractmethod
    async def get_status(self, task_id: str) -> str:
        ...

    @abstractmethod
    async def cancel(self, task_id: str) -> None:
        ...
