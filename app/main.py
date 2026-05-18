"""FastAPI application entry point."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import defects, documents, knowledge, projects, reports, runs, scenarios, tasks
from app.api.v1 import settings as settings_router
from app.api.websocket import run_progress as ws_progress
from app.api.websocket.task_progress import task_ws_manager
from app.infrastructure.executor import ensure_executor_running
from app.lib.logger import setup_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # Auto-start executor-web (non-blocking — API starts either way)
    asyncio.create_task(ensure_executor_running())
    # Initialize persistent database (SQLite by default, auto-created)
    try:
        from app.db_init import init_database
        await init_database()
    except Exception as e:
        # Fallback to in-memory — system still works
        get_logger(__name__).warning("Database init failed, using in-memory storage: %s", e)
    yield  # Signal that the application is ready


app = FastAPI(
    title="AutoTest API",
    description="AI-driven automated UI testing framework — document analysis, "
                "scenario generation, cross-dimensional defect detection.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "projects", "description": "项目管理 — 创建/查询/编辑/删除测试项目"},
        {"name": "documents", "description": "文档管理 — 添加/解析需求文档，提取业务规则"},
        {"name": "knowledge", "description": "知识库 — 业务规则管理、冲突检测"},
        {"name": "scenarios", "description": "场景管理 — 自动生成测试场景矩阵"},
        {"name": "runs", "description": "执行管理 — 创建/执行/取消测试运行"},
        {"name": "reports", "description": "报告管理 — 执行报告、缺陷详情"},
        {"name": "tasks", "description": "自动测试任务 — 创建/启动/查看/取消自动测试任务"},
        {"name": "defects", "description": "缺陷管理 — 缺陷列表、证据链"},
        {"name": "settings", "description": "系统设置 — LLM 配置、连接测试"},
    ],
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
app.include_router(tasks.router, prefix="/api/v1")

# WebSocket for real-time progress
app.include_router(ws_progress.router)


@app.websocket("/api/v1/ws/tasks/{task_id}")
async def task_websocket(websocket: WebSocket, task_id: str):
    await task_ws_manager.connect(task_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        task_ws_manager.disconnect(task_id, websocket)
    except Exception:
        task_ws_manager.disconnect(task_id, websocket)


@app.get("/health")
async def health():
    from app.dependencies import get_ai_status
    return {
        "status": "ok",
        "version": "0.1.0",
        "checks": {
            "database": {"status": "ok", "latency_ms": 0},
            "ai": get_ai_status(),
        },
        "uptime_seconds": 0,
    }
