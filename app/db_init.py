"""Database initialization — auto-creates SQLite (default) or connects PostgreSQL.

Strategy:
  1. Default (no DATABASE_URL or sqlite://): auto-create SQLite at data/autotest.db
  2. PostgreSQL (postgresql://): connect and run migrations via Alembic
  3. Tables are auto-created for SQLite; Postgres uses Alembic migrations

The existing Postgres*Repository classes work with any SQLAlchemy-supported backend
(SQLite included) since SQLAlchemy abstracts all dialect differences.
"""
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.dependencies import init_services
from app.infrastructure.persistence.defect_repo import SqlDefectRepository
from app.infrastructure.persistence.document_repo import SqlDocumentRepository
from app.infrastructure.persistence.knowledge_repo import SqlKnowledgeBaseRepository
from app.infrastructure.persistence.models import Base
from app.infrastructure.persistence.project_repo import SqlProjectRepository
from app.infrastructure.persistence.run_repo import SqlRunRepository
from app.infrastructure.persistence.scenario_repo import SqlScenarioRepository
from app.lib.logger import get_logger

logger = get_logger(__name__)

_engine = None
_session_factory = None


def _resolve_db_url() -> str:
    """Determine database URL: env var → default SQLite."""
    env_url = os.environ.get("DATABASE_URL") or settings.database_url or ""
    # Empty or example Postgres URL → use SQLite
    if not env_url or "postgresql+asyncpg://autotest:autotest@localhost:5432/autotest" in env_url:
        return _ensure_sqlite_url()
    # If user explicitly set sqlite://, use it directly
    if env_url.startswith("sqlite"):
        return env_url
    # PostgreSQL URL
    return env_url


def _ensure_sqlite_url() -> str:
    """Create data/ directory and return SQLite URL."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "autotest.db"
    logger.info("Using SQLite database: %s", db_path)
    return f"sqlite+aiosqlite:///{db_path}"


def get_engine():
    global _engine
    if _engine is None:
        url = _resolve_db_url()
        _engine = create_async_engine(url, echo=False)
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


async def init_database():
    """Initialize database: create engine, tables, and wire up repositories.

    Call this once at startup in the lifespan.
    """
    engine = get_engine()
    url = str(engine.url)

    # Create all tables (works for SQLite; Postgres uses Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified on %s", url.split("//")[0] + "//...")

    # Create session and wire up all repositories
    factory = get_session_factory()
    async with factory() as session:
        project_repo = SqlProjectRepository(session)
        document_repo = SqlDocumentRepository(session)
        kb_repo = SqlKnowledgeBaseRepository(session)
        scenario_repo = SqlScenarioRepository(session)
        run_repo = SqlRunRepository(session)
        defect_repo = SqlDefectRepository(session)
        init_services(project_repo, document_repo, kb_repo, scenario_repo, run_repo, defect_repo)

    logger.info("Database initialized — services switched to persistent storage")
