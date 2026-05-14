from app.domain.models.project import Project
from app.domain.exceptions import (
    ProjectNotFoundError,
    InvalidParameterError,
    OperationNotAllowedError,
)
from app.interfaces.repositories.project_repo import ProjectRepository
from app.lib.id_generator import generate_id
from app.lib.logger import get_logger

logger = get_logger(__name__)

VALID_PLATFORMS = {"web", "android", "ios"}
VALID_TRANSITIONS = {
    "created": {"parsing", "archived"},
    "parsing": {"ready", "parsing"},
    "ready": {"running", "archived"},
    "running": {"completed", "ready"},
    "completed": {"ready", "archived"},
    "archived": set(),
}


class ProjectService:
    def __init__(self, project_repo: ProjectRepository):
        self._repo = project_repo

    async def create_project(
        self, name: str, platforms: list[str],
        entries: list | None = None, docs: list | None = None,
    ) -> Project:
        if not name or not name.strip():
            raise InvalidParameterError("Project name cannot be empty")
        if not platforms:
            raise InvalidParameterError("At least one platform required")
        invalid = set(platforms) - VALID_PLATFORMS
        if invalid:
            raise InvalidParameterError(f"Unsupported platforms: {invalid}")

        project = Project(
            id=generate_id("project"),
            name=name.strip(),
            platforms=platforms,
            entries=entries or [],
            document_refs=docs or [],
        )
        created = await self._repo.create(project)
        logger.info(f"Project created: {created.id}")
        return created

    async def get_project(self, project_id: str) -> Project:
        project = await self._repo.get_by_id(project_id)
        if not project:
            raise ProjectNotFoundError(project_id)
        return project

    async def update_project(self, project_id: str, updates: dict) -> Project:
        project = await self.get_project(project_id)
        for key, value in updates.items():
            if hasattr(project, key):
                setattr(project, key, value)
        updated = await self._repo.update(project)
        logger.info(f"Project updated: {project_id}")
        return updated

    async def delete_project(self, project_id: str) -> None:
        project = await self.get_project(project_id)
        if project.status == "running":
            raise OperationNotAllowedError("Cannot delete a running project")
        await self._repo.delete(project_id)
        logger.info(f"Project deleted: {project_id}")

    async def list_projects(self, status: str | None = None) -> list[Project]:
        return await self._repo.list_projects(status)

    async def validate_transition(self, project_id: str, target: str) -> bool:
        project = await self.get_project(project_id)
        return target in VALID_TRANSITIONS.get(project.status, set())
