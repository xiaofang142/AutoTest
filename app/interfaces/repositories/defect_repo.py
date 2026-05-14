from abc import ABC, abstractmethod
from app.domain.models.defect import Defect


class DefectRepository(ABC):
    @abstractmethod
    async def create(self, defect: Defect) -> Defect:
        ...

    @abstractmethod
    async def get_by_id(self, defect_id: str) -> Defect | None:
        ...

    @abstractmethod
    async def get_by_run(self, run_id: str, severity: str | None = None) -> list[Defect]:
        ...

    @abstractmethod
    async def update(self, defect: Defect) -> Defect:
        ...
