# AutoTest Full Implementation Plan

> **For agentic workers:** Use `superpowers:subagent-driven-development`. Full system development in parallel streams.

**Goal:** Build complete AutoTest backend (FastAPI) with domain models, DB persistence, API endpoints, AI service integration, and MCP server.

**Architecture:** 6-layer DDD architecture: API → Service → Domain → Repository Interface → Repository Impl → Executor/AI. Async Python 3.11+ with FastAPI + SQLAlchemy 2.0 async.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, LiteLLM, Celery, Redis, PostgreSQL 15, Alembic

---

## File Structure

```
app/
├── __init__.py
├── main.py                     # FastAPI app + lifespan
├── config.py                   # Settings from env
├── dependencies.py             # DI container
│
├── api/
│   ├── __init__.py
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── projects.py
│   │   ├── documents.py
│   │   ├── knowledge.py
│   │   ├── scenarios.py
│   │   ├── runs.py
│   │   ├── reports.py
│   │   └── defects.py
│   ├── mcp/
│   │   ├── __init__.py
│   │   └── server.py
│   └── websocket/
│       ├── __init__.py
│       └── run_progress.py
│
├── domain/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── project.py
│   │   ├── document.py
│   │   ├── knowledge.py
│   │   ├── scenario.py
│   │   ├── run.py
│   │   └── defect.py
│   ├── events.py
│   └── exceptions.py
│
├── services/
│   ├── __init__.py
│   ├── project_service.py
│   ├── document_service.py
│   ├── knowledge_service.py
│   ├── scenario_service.py
│   ├── run_service.py
│   ├── analysis_service.py
│   └── report_service.py
│
├── interfaces/
│   ├── __init__.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── project_repo.py
│   │   ├── document_repo.py
│   │   ├── knowledge_repo.py
│   │   ├── scenario_repo.py
│   │   ├── run_repo.py
│   │   └── defect_repo.py
│   ├── ai_service.py
│   ├── executor_client.py
│   ├── file_service.py
│   └── task_queue.py
│
├── infrastructure/
│   ├── __init__.py
│   ├── persistence/
│   │   ├── __init__.py
│   │   ├── models.py          # SQLAlchemy ORM
│   │   ├── project_repo.py
│   │   ├── document_repo.py
│   │   ├── knowledge_repo.py
│   │   ├── scenario_repo.py
│   │   ├── run_repo.py
│   │   └── defect_repo.py
│   ├── ai/
│   │   ├── __init__.py
│   │   └── lite_llm_service.py
│   ├── executor/
│   │   └── web_executor_client.py
│   └── file/
│       └── s3_file_service.py
│
├── workers/
│   ├── __init__.py
│   ├── celery_app.py
│   ├── parse_docs.py
│   ├── gen_scenarios.py
│   └── execute_run.py
│
└── lib/
    ├── __init__.py
    ├── logger.py
    ├── id_generator.py
    └── retry.py

tests/
├── __init__.py
├── conftest.py
├── factories.py
├── unit/
│   ├── domain/
│   ├── services/
│   └── lib/
└── integration/
    ├── test_project_api.py
    └── conftest.py

migrations/
├── env.py
├── alembic.ini
└── versions/

pyproject.toml
requirements.txt
requirements-dev.txt
Dockerfile
docker-compose.yml
.env.example
```

---

## Phase 1A: Core Infrastructure (Project Skeleton + Domain + Config)

**Dependencies:** None - foundational layer

Files to create:
- `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`
- `.env.example`, `Dockerfile`, `docker-compose.yml`
- `app/__init__.py`, `app/main.py`, `app/config.py`, `app/dependencies.py`
- `app/domain/models/*` (all 6 domain models)
- `app/domain/events.py`, `app/domain/exceptions.py`
- `app/lib/logger.py`, `app/lib/id_generator.py`, `app/lib/retry.py`

## Phase 1B: Data Layer (Interfaces + SQLAlchemy + Alembic)

**Dependencies:** Phase 1A (domain models)

Files to create:
- `app/infrastructure/persistence/models.py` (SQLAlchemy ORM models)
- `app/interfaces/repositories/*` (6 repository interfaces)
- `app/infrastructure/persistence/*` (6 repository implementations)
- `migrations/env.py`, `migrations/alembic.ini`, `migrations/versions/001_init.py`

## Phase 1C: API + Services

**Dependencies:** Phase 1B (repositories)

Files to create:
- `app/services/*` (7 service classes)
- `app/api/v1/*` (7 router modules)
- `app/interfaces/ai_service.py`, `app/infrastructure/ai/lite_llm_service.py`
- `app/interfaces/executor_client.py`, `app/infrastructure/executor/web_executor_client.py`
- `app/interfaces/file_service.py`, `app/infrastructure/file/s3_file_service.py`
- `app/interfaces/task_queue.py`

## Phase 1D: Workers + MCP + WebSocket

**Dependencies:** Phase 1C (services)

Files to create:
- `app/workers/celery_app.py`, `app/workers/parse_docs.py`
- `app/workers/gen_scenarios.py`, `app/workers/execute_run.py`
- `app/api/mcp/server.py`
- `app/api/websocket/run_progress.py`

## Phase 1E: Tests

**Dependencies:** Phase 1C (services + API)

Files to create:
- `tests/conftest.py`, `tests/factories.py`
- `tests/unit/domain/test_project.py`
- `tests/unit/services/test_project_service.py`
- `tests/integration/test_project_api.py`

---

## Execution Order (Parallel Groups)

```
Group A ─── Phase 1A (skeleton + domain + config + lib)
   │
Group B ─── Phase 1B (DB models + repos + alembic) [after A]
   │
Group C ─── Phase 1C (services + API + infrastructure) [after B]
   │
Group D ─── Phase 1D (workers + MCP + WebSocket) [after C]
   │
Group E ─── Phase 1E (tests) [after C]
   │
Group F ─── Integration verification [after D+E]
```

Each group uses parallel subagents where files within the group are independent.
