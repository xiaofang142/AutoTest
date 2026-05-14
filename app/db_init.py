"""FastAPI dependency injection container with real Postgres repositories."""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings
from app.dependencies import init_services
from app.infrastructure.persistence.project_repo import PostgresProjectRepository
from app.infrastructure.persistence.document_repo import PostgresDocumentRepository
from app.infrastructure.persistence.knowledge_repo import PostgresKnowledgeBaseRepository
from app.infrastructure.persistence.scenario_repo import PostgresScenarioRepository
from app.infrastructure.persistence.run_repo import PostgresRunRepository
from app.infrastructure.persistence.defect_repo import PostgresDefectRepository

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncSession:
    factory = get_session_factory()
    async with factory() as session:
        yield session


def init_app():
    from app.main import app as fastapi_app

    @fastapi_app.on_event("startup")
    async def on_startup():
        factory = get_session_factory()
        async with factory() as session:
            project_repo = PostgresProjectRepository(session)
            document_repo = PostgresDocumentRepository(session)
            kb_repo = PostgresKnowledgeBaseRepository(session)
            scenario_repo = PostgresScenarioRepository(session)
            run_repo = PostgresRunRepository(session)
            defect_repo = PostgresDefectRepository(session)
            init_services(project_repo, document_repo, kb_repo, scenario_repo, run_repo, defect_repo)
