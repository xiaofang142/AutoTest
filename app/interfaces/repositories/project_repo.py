from abc import ABC, abstractmethod

from app.domain.models.project import Project


class ProjectRepository(ABC):
    @abstractmethod
    async def create(self, project: Project) -> Project:
        ...

    @abstractmethod
    async def get_by_id(self, project_id: str) -> Project | None:
        ...

    @abstractmethod
    async def update(self, project: Project) -> Project:
        ...

    @abstractmethod
    async def delete(self, project_id: str) -> None:
        ...

    @abstractmethod
    async def list_projects(self, status: str | None = None) -> list[Project]:
        ...
