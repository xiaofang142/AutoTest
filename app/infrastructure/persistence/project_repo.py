from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.project import Project
from app.infrastructure.persistence.models import ProjectModel
from app.interfaces.repositories.project_repo import ProjectRepository


class PostgresProjectRepository(ProjectRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, project: Project) -> Project:
        model = ProjectModel(
            id=project.id,
            name=project.name,
            description=project.description,
            status=project.status,
            platforms=project.platforms,
            entries=[e.model_dump() for e in project.entries],
            config=project.config.model_dump(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self._session.add(model)
        await self._session.commit()
        return project

    async def get_by_id(self, project_id: str) -> Project | None:
        result = await self._session.execute(
            select(ProjectModel).where(ProjectModel.id == project_id, ProjectModel.deleted_at.is_(None))
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._model_to_domain(model)

    async def update(self, project: Project) -> Project:
        model = await self._session.get(ProjectModel, project.id)
        if model:
            model.name = project.name
            model.description = project.description
            model.status = project.status
            model.platforms = project.platforms
            model.entries = [e.model_dump() for e in project.entries]
            model.updated_at = datetime.now()
            await self._session.commit()
        return project

    async def delete(self, project_id: str) -> None:
        model = await self._session.get(ProjectModel, project_id)
        if model:
            model.deleted_at = datetime.now()
            await self._session.commit()

    async def list_projects(self, status: str | None = None) -> list[Project]:
        query = select(ProjectModel).where(ProjectModel.deleted_at.is_(None))
        if status:
            query = query.where(ProjectModel.status == status)
        query = query.order_by(ProjectModel.created_at.desc())
        result = await self._session.execute(query)
        models = result.scalars().all()
        return [self._model_to_domain(m) for m in models]

    def _model_to_domain(self, model: ProjectModel) -> Project:
        from app.domain.models.project import PlatformEntry, ProjectConfig

        entries = [PlatformEntry(**e) for e in (model.entries or [])]
        config = ProjectConfig(**(model.config or {}))
        return Project(
            id=model.id,
            name=model.name,
            description=model.description or "",
            status=model.status,
            platforms=model.platforms or ["web"],
            entries=entries,
            config=config,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
