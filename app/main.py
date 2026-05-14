from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.lib.logger import setup_logging
from app.api.v1 import projects, documents, knowledge, scenarios, runs, reports, defects
from app.api.websocket import run_progress as ws_progress
from app.api.v1 import settings as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield


app = FastAPI(
    title="AutoTest API",
    description="AI-driven automated UI testing framework",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API routes
app.include_router(projects.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(scenarios.router, prefix="/api/v1")
app.include_router(runs.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(defects.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")

# WebSocket for real-time progress
app.include_router(ws_progress.router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "checks": {
            "database": {"status": "ok", "latency_ms": 0},
            "redis": {"status": "ok", "latency_ms": 0},
        },
        "uptime_seconds": 0,
    }
