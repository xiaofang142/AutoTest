# AutoTest 全自动 AI 测试 — 实施路线图分解

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 AutoTest 从 Project 中心架构重构为 TestTask 中心架构，完整实现八阶段闭环 + 缺陷归因 + 基础设施 + 测试覆盖

**Architecture:** 保持现有三层架构（API → Service → Domain/Persistence），新增 TestTask 聚合根，将 Project 降级为归档容器。执行器层不变，通过 Engine 层桥接新旧对象。

**Tech Stack:** Python FastAPI, Vue 3 + Element Plus, TypeScript Playwright, PostgreSQL/SQLite, Celery, Redis

---

## Phase 1 (P1): 核心主线重构 — TestTask + 八阶段闭环

### Task 1.1: TestTask 领域模型

**Files:**
- Create: `app/domain/models/task.py`
- Test: `tests/unit/domain/test_task.py`

**设计说明：**
TestTask 是产品一等聚合根，包含 7 个子对象。所有子对象在 task.py 中定义，初期可为简单 dataclass/Pydantic 模型。

- [ ] **Step 1: 定义 TaskStatus 枚举 + TaskMode 枚举**

```python
from enum import Enum

class TaskStatus(str, Enum):
    DRAFT = "draft"
    PRECHECKING = "prechecking"
    UNDERSTANDING = "understanding"
    PLANNING = "planning"
    RUNNING = "running"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    COMPLETED_WITH_DEFECTS = "completed_with_defects"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    ERROR = "error"

class TaskMode(str, Enum):
    QUICK = "quick"
    DOCUMENT_DRIVEN = "document_driven"
    MIXED = "mixed"

class TaskGoal(str, Enum):
    SMOKE = "smoke"
    REGRESSION = "regression"
    BUSINESS = "business"
    DEFECT_RE_TEST = "defect_re_test"

class TaskDepth(str, Enum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    DEEP = "deep"

class AutoLevel(str, Enum):
    A0 = "A0"  # 仅收集输入
    A1 = "A1"  # 完成预检
    A2 = "A2"  # 已生成蓝图
    A3 = "A3"  # 已自动执行
    A4 = "A4"  # 已执行+校验+归因
    A5 = "A5"  # 已形成 AI 可消费修复上下文
```

- [ ] **Step 2: 定义 TaskInput 模型**

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class TaskInput(BaseModel):
    target_type: str = "web"  # web / h5 / android / ios
    target_url: str = ""
    target_app: str = ""
    environment: str = "dev"
    scope: str = ""  # 全站/指定模块/指定页面
    documents: list[str] = []  # 文档 ID 列表
    account_info: dict = {}
    platform_config: dict = {}
    user_notes: str = ""
    priority_targets: list[str] = []
```

- [ ] **Step 3: 定义 EnvironmentCheck 模型**

```python
class EnvironmentCheck(BaseModel):
    executor_online: bool = False
    browser_available: bool = False
    network_ok: bool = False
    login_ready: bool = False
    ocr_available: bool = False
    ai_available: bool = False
    console_capture: bool = False
    network_capture: bool = False
    auto_fixable_items: list[str] = []
    blocking_items: list[str] = []
    auto_level: str = "A0"
    summary: str = ""
```

- [ ] **Step 4: 定义 UnderstandingResult 模型**

```python
class UnderstandingResult(BaseModel):
    page_intent: str = ""
    document_intent: str = ""
    key_roles: list[str] = []
    key_flows: list[str] = []
    risk_points: list[str] = []
    must_test_assertions: list[str] = []
    page_objects: list[dict] = []
    doc_page_conflicts: list[str] = []
    completeness: float = 0.0  # 0-1
```

- [ ] **Step 5: 定义 TestBlueprint 模型**

```python
class BlueprintStep(BaseModel):
    index: int
    action: str
    target: str = ""
    value: str = ""
    assert_ui: bool = True
    assert_console: bool = True
    assert_api: bool = True
    assert_business: bool = False
    expected_url: str = ""
    expected_text: str = ""
    priority: int = 1  # 1-5
    risk_point: str = ""

class TestBlueprint(BaseModel):
    targets: list[dict] = []
    flow_chains: list[list[BlueprintStep]] = []
    all_steps: list[BlueprintStep] = []
    assertions: list[dict] = []
    confidence: float = 0.0
    risk_coverage: str = ""
    min_executable_set: list[int] = []  # step indexes
```

- [ ] **Step 6: 定义 DeliveryPackage 模型**

```python
class TesterView(BaseModel):
    summary: str = ""
    defect_list: list[dict] = []
    steps_with_screenshots: list[dict] = []

class DeveloperView(BaseModel):
    defect_details: list[dict] = []
    evidence_chains: list[dict] = []
    root_cause: str = ""
    fix_suggestion: str = ""

class AIAssistantView(BaseModel):
    task_summary: str = ""
    defect_summary: str = ""
    reproduction_steps: list[str] = []
    console_errors: list[str] = []
    network_failures: list[dict] = []
    page_state: dict = {}
    root_cause_candidates: list[str] = []
    repair_suggestion: str = ""

class DeliveryPackage(BaseModel):
    tester_view: TesterView = TesterView()
    developer_view: DeveloperView = DeveloperView()
    ai_assistant_view: AIAssistantView = AIAssistantView()
    regression_entry: dict = {}
    created_at: datetime = Field(default_factory=datetime.now)
```

- [ ] **Step 7: 定义 TestTask 主模型**

```python
class TestTask(BaseModel):
    id: str = ""
    project_id: str = ""
    name: str = ""
    description: str = ""
    source: str = "web_ui"  # web_ui / cli / api / mcp
    created_by: str = ""

    # 输入
    input: TaskInput = TaskInput()
    mode: TaskMode = TaskMode.QUICK
    goal: TaskGoal = TaskGoal.SMOKE
    depth: TaskDepth = TaskDepth.STANDARD

    # 状态
    status: TaskStatus = TaskStatus.DRAFT
    current_stage: str = "draft"
    stage_started_at: Optional[datetime] = None
    progress_percent: int = 0
    blocked_reason: str = ""
    error_summary: str = ""

    # 阶段产物
    environment_check: Optional[EnvironmentCheck] = None
    understanding: Optional[UnderstandingResult] = None
    blueprint: Optional[TestBlueprint] = None
    run_id: str = ""  # 关联 ExecutionRun

    # 结果
    final_status: str = ""
    summary: str = ""
    defect_count: int = 0
    high_risk_count: int = 0
    auto_level: AutoLevel = AutoLevel.A0
    delivery_ready: bool = False
    delivery: Optional[DeliveryPackage] = None

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
```

- [ ] **Step 8: 实现状态机验证**

```python
class TaskStateMachine:
    """TestTask 状态机 — 验证状态转换合法性"""

    VALID_TRANSITIONS = {
        TaskStatus.DRAFT: {TaskStatus.PRECHECKING, TaskStatus.CANCELLED},
        TaskStatus.PRECHECKING: {TaskStatus.UNDERSTANDING, TaskStatus.BLOCKED, TaskStatus.CANCELLED, TaskStatus.ERROR},
        TaskStatus.UNDERSTANDING: {TaskStatus.PLANNING, TaskStatus.BLOCKED, TaskStatus.CANCELLED, TaskStatus.ERROR},
        TaskStatus.PLANNING: {TaskStatus.RUNNING, TaskStatus.BLOCKED, TaskStatus.CANCELLED, TaskStatus.ERROR},
        TaskStatus.RUNNING: {TaskStatus.ANALYZING, TaskStatus.BLOCKED, TaskStatus.CANCELLED, TaskStatus.ERROR},
        TaskStatus.ANALYZING: {TaskStatus.COMPLETED, TaskStatus.COMPLETED_WITH_DEFECTS, TaskStatus.BLOCKED, TaskStatus.ERROR},
        TaskStatus.COMPLETED: set(),
        TaskStatus.COMPLETED_WITH_DEFECTS: set(),
        TaskStatus.BLOCKED: {TaskStatus.DRAFT, TaskStatus.CANCELLED},
        TaskStatus.CANCELLED: set(),
        TaskStatus.ERROR: {TaskStatus.DRAFT},
    }

    @classmethod
    def can_transition(cls, current: TaskStatus, target: TaskStatus) -> bool:
        return target in cls.VALID_TRANSITIONS.get(current, set())
```

- [ ] **Step 9: 写单元测试**

```python
# tests/unit/domain/test_task.py
def test_task_created_in_draft():
    task = TestTask(name="test", input=TaskInput(target_url="https://example.com"))
    assert task.status == TaskStatus.DRAFT

def test_task_valid_transition():
    assert TaskStateMachine.can_transition(TaskStatus.DRAFT, TaskStatus.PRECHECKING)
    assert not TaskStateMachine.can_transition(TaskStatus.DRAFT, TaskStatus.COMPLETED)

def test_task_invalid_transition():
    assert not TaskStateMachine.can_transition(TaskStatus.DRAFT, TaskStatus.RUNNING)
```

- [ ] **Step 10: 运行测试验证**

Run: `pytest tests/unit/domain/test_task.py -v` → PASS

- [ ] **Step 11: Commit**

```bash
git add app/domain/models/task.py tests/unit/domain/test_task.py
git commit -m "feat(task): add TestTask domain model with 8-phase state machine"
```

---

### Task 1.2: TestTask 仓储接口 + 内存实现

**Files:**
- Create: `app/interfaces/repositories/task_repo.py`
- Modify: `app/infrastructure/persistence/task_repo.py` (Create)
- Modify: `app/dependencies.py`
- Test: `tests/unit/infrastructure/test_task_repo.py`

- [ ] **Step 1: 定义 TaskRepository 接口**

```python
# app/interfaces/repositories/task_repo.py
from abc import ABC, abstractmethod
from app.domain.models.task import TestTask

class TaskRepository(ABC):
    @abstractmethod
    async def create(self, task: TestTask) -> TestTask: ...
    @abstractmethod
    async def get_by_id(self, task_id: str) -> TestTask | None: ...
    @abstractmethod
    async def list_tasks(self, project_id: str = "", status: str = "", page: int = 1, page_size: int = 20) -> dict: ...
    @abstractmethod
    async def update_status(self, task_id: str, status: str, stage: str = "") -> None: ...
    @abstractmethod
    async def update_progress(self, task_id: str, percent: int) -> None: ...
    @abstractmethod
    async def update_stage_result(self, task_id: str, stage: str, data: dict) -> None: ...
    @abstractmethod
    async def delete(self, task_id: str) -> None: ...
```

- [ ] **Step 2: 实现内存版 TaskRepository**

```python
# app/infrastructure/persistence/task_repo.py
from app.domain.models.task import TestTask
from app.interfaces.repositories.task_repo import TaskRepository
from app.lib.id_generator import generate_id

class InMemoryTaskRepository(TaskRepository):
    def __init__(self):
        self._tasks: dict[str, TestTask] = {}

    async def create(self, task: TestTask) -> TestTask:
        task.id = generate_id("task")
        self._tasks[task.id] = task
        return task

    async def get_by_id(self, task_id: str) -> TestTask | None:
        return self._tasks.get(task_id)

    async def list_tasks(self, project_id: str = "", status: str = "", page: int = 1, page_size: int = 20) -> dict:
        items = list(self._tasks.values())
        if project_id:
            items = [t for t in items if t.project_id == project_id]
        if status:
            items = [t for t in items if t.status == status]
        items.sort(key=lambda t: t.created_at, reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        return {"items": items[start:start+page_size], "total": total, "page": page, "page_size": page_size}

    async def update_status(self, task_id: str, status: str, stage: str = "") -> None:
        task = self._tasks.get(task_id)
        if task:
            task.status = status
            if stage:
                task.current_stage = stage

    async def update_progress(self, task_id: str, percent: int) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.progress_percent = percent

    async def update_stage_result(self, task_id: str, stage: str, data: dict) -> None:
        task = self._tasks.get(task_id)
        if task:
            setattr(task, stage, data)

    async def delete(self, task_id: str) -> None:
        self._tasks.pop(task_id, None)
```

- [ ] **Step 3: 注入到依赖**

```python
# app/dependencies.py 添加
from app.infrastructure.persistence.task_repo import InMemoryTaskRepository

_task_repo: TaskRepository | None = None

def get_task_repo() -> TaskRepository:
    global _task_repo
    if _task_repo is None:
        _task_repo = InMemoryTaskRepository()
    return _task_repo
```

- [ ] **Step 4: 写单元测试**

```python
# tests/unit/infrastructure/test_task_repo.py
@pytest.mark.asyncio
async def test_create_and_get_task():
    repo = InMemoryTaskRepository()
    task = TestTask(name="test", input=TaskInput(target_url="https://example.com"))
    created = await repo.create(task)
    assert created.id.startswith("task_")
    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.name == "test"

@pytest.mark.asyncio
async def test_update_status():
    repo = InMemoryTaskRepository()
    task = await repo.create(TestTask(name="t"))
    await repo.update_status(task.id, "prechecking", "prechecking")
    updated = await repo.get_by_id(task.id)
    assert updated.status == "prechecking"
    assert updated.current_stage == "prechecking"
```

- [ ] **Step 5: 运行测试**

Run: `pytest tests/unit/infrastructure/test_task_repo.py -v` → PASS

- [ ] **Step 6: Commit**

```bash
git add app/interfaces/repositories/task_repo.py app/infrastructure/persistence/task_repo.py app/dependencies.py tests/unit/infrastructure/test_task_repo.py
git commit -m "feat(task): add TaskRepository interface and InMemory implementation"
```

---

### Task 1.3: 任务驱动 API

**Files:**
- Create: `app/api/v1/tasks.py`
- Modify: `app/main.py`（注册路由）
- Test: `tests/unit/api/test_tasks_api.py`

- [ ] **Step 1: 实现 POST /api/v1/tasks**

```python
# app/api/v1/tasks.py
from fastapi import APIRouter, Depends
from app.domain.models.task import TestTask, TaskInput, TaskMode, TaskGoal, TaskDepth
from app.interfaces.repositories.task_repo import TaskRepository
from app.dependencies import get_task_repo
from app.lib.id_generator import generate_id

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

@router.post("")
async def create_task(
    name: str,
    target_url: str = "",
    mode: str = "quick",
    goal: str = "smoke",
    depth: str = "standard",
    project_id: str = "",
    doc_ids: list[str] = [],
    task_repo: TaskRepository = Depends(get_task_repo),
):
    task = TestTask(
        id=generate_id("task"),
        name=name,
        project_id=project_id,
        input=TaskInput(target_url=target_url, documents=doc_ids),
        mode=TaskMode(mode),
        goal=TaskGoal(goal),
        depth=TaskDepth(depth),
    )
    created = await task_repo.create(task)
    return {"code": 0, "data": {"task": created.model_dump(mode="json")}}
```

- [ ] **Step 2: 实现 GET /api/v1/tasks + GET /api/v1/tasks/{task_id}**

```python
@router.get("")
async def list_tasks(
    project_id: str = "",
    status: str = "",
    page: int = 1,
    page_size: int = 20,
    task_repo: TaskRepository = Depends(get_task_repo),
):
    result = await task_repo.list_tasks(project_id, status, page, page_size)
    return {"code": 0, "data": result}

@router.get("/{task_id}")
async def get_task(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    if not task:
        return {"code": 40001, "message": "Task not found"}
    return {"code": 0, "data": {"task": task.model_dump(mode="json")}}
```

- [ ] **Step 3: 实现 POST /api/v1/tasks/{task_id}/start**

```python
from app.domain.models.task import TaskStatus, TaskStateMachine

@router.post("/{task_id}/start")
async def start_task(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    if not task:
        return {"code": 40001, "message": "Task not found"}
    if not TaskStateMachine.can_transition(task.status, TaskStatus.PRECHECKING):
        return {"code": 40003, "message": f"Cannot start task in status {task.status}"}
    await task_repo.update_status(task_id, "prechecking", "prechecking")
    # 异步触发执行引擎
    return {"code": 0, "data": {"task_id": task_id, "status": "prechecking"}}
```

- [ ] **Step 4: 实现 POST cancel + 剩余 GET endpoints**

```python
@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    if not task:
        return {"code": 40001, "message": "Task not found"}
    await task_repo.update_status(task_id, "cancelled", "")
    return {"code": 0, "data": {"task_id": task_id, "status": "cancelled"}}

@router.get("/{task_id}/timeline")
async def get_task_timeline(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    if not task:
        return {"code": 40001, "message": "Task not found"}
    return {"code": 0, "data": {"task_id": task_id, "current_stage": task.current_stage, "progress": task.progress_percent}}

@router.get("/{task_id}/delivery")
async def get_task_delivery(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    if not task or not task.delivery:
        return {"code": 40001, "message": "Delivery not ready"}
    return {"code": 0, "data": task.delivery.model_dump(mode="json")}

@router.get("/{task_id}/defects")
async def get_task_defects(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    if not task:
        return {"code": 40001, "message": "Task not found"}
    return {"code": 0, "data": {"defect_count": task.defect_count, "high_risk_count": task.high_risk_count}}

@router.get("/{task_id}/environment-check")
async def get_task_environment_check(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    return {"code": 0, "data": task.environment_check.model_dump(mode="json") if task.environment_check else {}}

@router.get("/{task_id}/understanding")
async def get_task_understanding(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    return {"code": 0, "data": task.understanding.model_dump(mode="json") if task.understanding else {}}

@router.get("/{task_id}/blueprint")
async def get_task_blueprint(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    return {"code": 0, "data": task.blueprint.model_dump(mode="json") if task.blueprint else {}}

@router.get("/{task_id}/repair-context")
async def get_task_repair_context(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    # 简化版：从 delivery 中提取 AI 助手视图
    task = await task_repo.get_by_id(task_id)
    if not task or not task.delivery:
        return {"code": 40001, "message": "Not available"}
    return {"code": 0, "data": task.delivery.ai_assistant_view.model_dump(mode="json")}
```

- [ ] **Step 5: 注册到 main.py**

在 `app/main.py` 添加：
```python
from app.api.v1 import tasks
app.include_router(tasks.router, prefix="/api/v1")
# 更新 OpenAPI tags
{"name": "tasks", "description": "自动测试任务管理 — 创建/启动/查看/取消自动测试任务"},
```

- [ ] **Step 6: 测试 API**

```bash
curl -X POST http://localhost:8000/api/v1/tasks -H "Content-Type: application/json" -d '{"name": "冒烟测试", "target_url": "https://example.com", "mode": "quick"}'
curl http://localhost:8000/api/v1/tasks
curl http://localhost:8000/api/v1/tasks/{task_id}
```

- [ ] **Step 7: Commit**

```bash
git add app/api/v1/tasks.py app/main.py
git commit -m "feat(task): add task-driven REST API endpoints"
```

---

### Task 1.4: 执行引擎接入 TestTask 状态机

**Files:**
- Create: `app/engine/task_orchestrator.py`
- Modify: `app/engine/execution_engine.py`
- Test: `tests/unit/engine/test_task_orchestrator.py`

- [ ] **Step 1: 实现 TaskOrchestrator — 八阶段编排器**

```python
# app/engine/task_orchestrator.py
"""八阶段闭环编排器：把 TestTask 状态机连接到实际执行引擎。"""
from app.domain.models.task import TestTask, TaskStatus, EnvironmentCheck, UnderstandingResult, TestBlueprint
from app.interfaces.repositories.task_repo import TaskRepository
from app.engine.execution_engine import ExecutionEngine
from app.lib.logger import get_logger

logger = get_logger(__name__)

class TaskOrchestrator:
    """协调 TestTask 走完 8 个阶段。每个阶段一个方法。"""

    def __init__(self, task_repo: TaskRepository, engine: ExecutionEngine):
        self._task_repo = task_repo
        self._engine = engine

    async def run_pipeline(self, task_id: str) -> dict:
        task = await self._task_repo.get_by_id(task_id)
        if not task:
            return {"error": "Task not found"}

        # 阶段 1: 环境预检
        await self._task_repo.update_status(task_id, "prechecking", "prechecking")
        check = await self._precheck(task)
        await self._task_repo.update_stage_result(task_id, "environment_check", check.model_dump())
        if check.blocking_items:
            await self._task_repo.update_status(task_id, "blocked", "prechecking")
            return {"status": "blocked", "reason": check.blocking_items}
        task.environment_check = check

        # 阶段 2: 测试对象理解
        await self._task_repo.update_status(task_id, "understanding", "understanding")
        understanding = await self._understand(task)
        await self._task_repo.update_stage_result(task_id, "understanding", understanding.model_dump())
        task.understanding = understanding

        # 阶段 3: 测试蓝图生成
        await self._task_repo.update_status(task_id, "planning", "planning")
        blueprint = await self._plan(task, understanding)
        await self._task_repo.update_stage_result(task_id, "blueprint", blueprint.model_dump())
        task.blueprint = blueprint

        # 阶段 4: 执行编排
        await self._task_repo.update_status(task_id, "running", "running")
        run_result = await self._execute(task, blueprint)

        # 阶段 5: 多维校验 + 缺陷归因
        await self._task_repo.update_status(task_id, "analyzing", "analyzing")
        final_status = await self._analyze_and_deliver(task, run_result)

        await self._task_repo.update_status(task_id, final_status, final_status)
        return {"status": final_status, "task_id": task_id}

    async def _precheck(self, task: TestTask) -> EnvironmentCheck:
        """阶段 1: 环境预检"""
        # 实际实现需要对接 ExecutorFactory
        return EnvironmentCheck(executor_online=True, browser_available=True, auto_level="A1", summary="All checks passed")

    async def _understand(self, task: TestTask) -> UnderstandingResult:
        """阶段 2: 页面/文档理解"""
        return UnderstandingResult(page_intent=f"Page: {task.input.target_url}", completeness=0.8)

    async def _plan(self, task: TestTask, understanding: UnderstandingResult) -> TestBlueprint:
        """阶段 3: 蓝图生成"""
        from app.engine.chain_builder import ChainBuilder
        builder = ChainBuilder()
        return builder.build_smoke_blueprint(task)

    async def _execute(self, task: TestTask, blueprint: TestBlueprint) -> dict:
        """阶段 4: 执行"""
        steps = []
        for chain in blueprint.flow_chains:
            steps.extend(chain)
        result = await self._engine.execute_run(
            run_id=f"run_{task.id}",
            target_url=task.input.target_url,
            steps=steps,
            entry={"url": task.input.target_url},
        )
        return result

    async def _analyze_and_deliver(self, task: TestTask, run_result: dict) -> str:
        """阶段 5-8: 校验+归因+交付"""
        has_defects = run_result.get("summary", {}).get("defects", 0) > 0
        return TaskStatus.COMPLETED_WITH_DEFECTS if has_defects else TaskStatus.COMPLETED
```

- [ ] **Step 2: 测试编排器**

```python
# tests/unit/engine/test_task_orchestrator.py
@pytest.mark.asyncio
async def test_orchestrator_full_pipeline():
    repo = InMemoryTaskRepository()
    engine = AsyncMock(spec=ExecutionEngine)
    engine.execute_run.return_value = {"summary": {"defects": 0, "total": 0, "passed": 0, "failed": 0}}
    orch = TaskOrchestrator(repo, engine)
    task = await repo.create(TestTask(name="test", input=TaskInput(target_url="https://x.com")))
    result = await orch.run_pipeline(task.id)
    assert result["status"] in ("completed", "completed_with_defects")
```

- [ ] **Step 3: Commit**

```bash
git add app/engine/task_orchestrator.py tests/unit/engine/test_task_orchestrator.py
git commit -m "feat(task): add TaskOrchestrator with 8-phase pipeline"
```

---

### Task 1.5: 前端 — 新首页（新建自动测试任务入口）

**Files:**
- Modify: `web/src/views/Dashboard.vue`（替换为新首页）
- Modify: `web/src/router.ts`
- Create: `web/src/api/taskApi.ts`

- [ ] **Step 1: 创建 taskApi.ts**

```typescript
// web/src/api/taskApi.ts
import { apiPost, apiGet } from './index';

export interface CreateTaskParams {
  name: string;
  target_url: string;
  mode?: 'quick' | 'document_driven' | 'mixed';
  goal?: string;
  depth?: string;
  project_id?: string;
  doc_ids?: string[];
}

export async function createTask(params: CreateTaskParams) {
  return apiPost('/api/v1/tasks', params);
}

export async function listTasks(params?: { project_id?: string; status?: string; page?: number }) {
  return apiGet('/api/v1/tasks', params);
}

export async function getTask(taskId: string) {
  return apiGet(`/api/v1/tasks/${taskId}`);
}

export async function startTask(taskId: string) {
  return apiPost(`/api/v1/tasks/${taskId}/start`, {});
}

export async function cancelTask(taskId: string) {
  return apiPost(`/api/v1/tasks/${taskId}/cancel`, {});
}
```

- [ ] **Step 2: 改造首页 — 新建自动测试为主入口**

```vue
<!-- web/src/views/Dashboard.vue — 替换为新的首页 -->
<template>
  <div>
    <!-- 主入口卡片：新建自动测试任务 -->
    <el-card shadow="never" style="margin-bottom: 20px; border: 2px dashed #409eff;">
      <div style="text-align: center; padding: 30px 0;">
        <h2 style="margin-bottom: 20px;">🚀 新建自动测试任务</h2>
        <p style="color: #909399; margin-bottom: 24px;">输入网址即可自动完成测试 → 产出可直接修复的缺陷报告</p>
        <el-form :inline="true" @submit.prevent="goToCreate">
          <el-form-item>
            <el-input v-model="quickUrl" placeholder="输入被测网址，例如 https://example.com" style="width: 420px" clearable />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="goToCreate" size="large">一键开始</el-button>
          </el-form-item>
        </el-form>
        <div style="margin-top: 12px;">
          <el-tag type="success" style="margin-right: 8px;">零脚本</el-tag>
          <el-tag type="warning" style="margin-right: 8px;">零维护</el-tag>
          <el-tag type="info">零配置</el-tag>
        </div>
      </div>
    </el-card>

    <!-- 近期任务列表 -->
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between;">
          <span>📋 近期任务</span>
          <el-button text type="primary" @click="$router.push('/tasks')">查看全部</el-button>
        </div>
      </template>
      <el-table :data="recentTasks" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="任务名称" min-width="180" />
        <el-table-column prop="input.target_url" label="目标地址" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="140">
          <template #default="{ row }"><el-tag :type="statusType(row.status)">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="defect_count" label="缺陷" width="80" />
        <el-table-column prop="created_at" label="时间" width="160" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }"><el-button text @click="$router.push(`/tasks/${row.id}`)">查看</el-button></template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
```

- [ ] **Step 3: 修改路由**

```typescript
// web/src/router.ts
const routes = [
  { path: "/", component: () => import("./views/Dashboard.vue") },  // 新首页
  { path: "/tasks", component: () => import("./views/TaskList.vue") },
  { path: "/tasks/:id", component: () => import("./views/TaskDetail.vue") },
  { path: "/projects", component: () => import("./views/ProjectList.vue") },
  { path: "/projects/:id", component: () => import("./views/ProjectDetail.vue") },
  { path: "/runs/:id", component: () => import("./views/RunDetail.vue") },
  { path: "/defects/:id", component: () => import("./views/DefectDetail.vue") },
  { path: "/knowledge", component: () => import("./views/KnowledgeCenter.vue") },
  { path: "/settings", component: () => import("./views/Settings.vue") },
];
```

- [ ] **Step 4: Commit**

```bash
git add web/src/views/Dashboard.vue web/src/router.ts web/src/api/taskApi.ts
git commit -m "feat(ui): redesign homepage with 'new auto test task' as primary entry"
```

---

### Task 1.6: 前端 — TaskList + TaskDetail 视图

**Files:**
- Create: `web/src/views/TaskList.vue`
- Create: `web/src/views/TaskDetail.vue`
- Modify: `web/src/stores/`（创建 task store）

- [ ] **Step 1: 创建 TaskList.vue**

```vue
<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
      <h3>测试任务</h3>
      <el-button type="primary" @click="$router.push('/')">+ 新建任务</el-button>
    </div>

    <!-- 过滤栏 -->
    <el-card shadow="never" style="margin-bottom: 16px;">
      <el-form :inline="true">
        <el-form-item label="状态">
          <el-select v-model="filter.status" clearable placeholder="全部状态">
            <el-option v-for="s in statuses" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="loadTasks">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 任务列表 -->
    <el-table :data="tasks" v-loading="loading" style="width: 100%">
      <el-table-column prop="name" label="任务名称" min-width="180" />
      <el-table-column prop="input.target_url" label="目标" min-width="200" show-overflow-tooltip />
      <el-table-column prop="mode" label="模式" width="120" />
      <el-table-column prop="status" label="阶段" width="120">
        <template #default="{ row }"><el-tag :type="tagType(row.status)" size="small">{{ row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="auto_level" label="自动化等级" width="100" />
      <el-table-column prop="defect_count" label="缺陷" width="60" />
      <el-table-column prop="progress_percent" label="进度" width="120">
        <template #default="{ row }"><el-progress :percentage="row.progress_percent" :status="row.progress_percent >= 100 ? 'success' : ''" /></template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button text @click="$router.push(`/tasks/${row.id}`)">详情</el-button>
          <el-button v-if="row.status === 'draft'" text type="danger" @click="cancelTask(row.id)">取消</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination v-if="total > pageSize" :total="total" :page-size="pageSize" @current-change="onPageChange" style="margin-top: 16px" />
  </div>
</template>
```

- [ ] **Step 2: 创建 TaskDetail.vue（多标签详情）**

```vue
<template>
  <div v-loading="loading">
    <el-page-header @back="$router.push('/tasks')" :content="task?.name || '任务详情'" style="margin-bottom: 16px;" />

    <el-steps :active="activeStep" finish-status="success" style="margin-bottom: 24px;">
      <el-step title="入口" />
      <el-step title="预检" />
      <el-step title="理解" />
      <el-step title="蓝图" />
      <el-step title="执行" />
      <el-step title="归因" />
      <el-step title="交付" />
    </el-steps>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="概览" name="overview">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务名称">{{ task?.name }}</el-descriptions-item>
          <el-descriptions-item label="状态"><el-tag :type="tagType(task?.status)">{{ task?.status }}</el-tag></el-descriptions-item>
          <el-descriptions-item label="目标地址">{{ task?.input?.target_url }}</el-descriptions-item>
          <el-descriptions-item label="模式">{{ task?.mode }}</el-descriptions-item>
          <el-descriptions-item label="自动化等级"><el-tag>{{ task?.auto_level }}</el-tag></el-descriptions-item>
          <el-descriptions-item label="缺陷数">{{ task?.defect_count }}</el-descriptions-item>
          <el-descriptions-item label="进度"><el-progress :percentage="task?.progress_percent || 0" style="width: 200px" /></el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ task?.created_at }}</el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>
      <el-tab-pane label="预检结果" name="precheck">（等待实现）</el-tab-pane>
      <el-tab-pane label="理解结果" name="understanding">（等待实现）</el-tab-pane>
      <el-tab-pane label="测试蓝图" name="blueprint">（等待实现）</el-tab-pane>
      <el-tab-pane label="执行过程" name="execution">（等待实现）</el-tab-pane>
      <el-tab-pane label="缺陷与交付" name="defects">（等待实现）</el-tab-pane>
    </el-tabs>
  </div>
</template>
```

- [ ] **Step 3: Commit**

```bash
git add web/src/views/TaskList.vue web/src/views/TaskDetail.vue
git commit -m "feat(ui): add TaskList and TaskDetail views with multi-tab layout"
```

---

### Task 1.7: WebSocket 任务级事件

**Files:**
- Create: `app/api/websocket/task_progress.py`
- Modify: `app/main.py`

- [ ] **Step 1: 实现任务级 WebSocket**

```python
# app/api/websocket/task_progress.py
from fastapi import WebSocket, WebSocketDisconnect
from app.lib.logger import get_logger

logger = get_logger(__name__)

class TaskWebSocketManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, task_id: str, ws: WebSocket):
        await ws.accept()
        if task_id not in self._connections:
            self._connections[task_id] = []
        self._connections[task_id].append(ws)

    def disconnect(self, task_id: str, ws: WebSocket):
        if task_id in self._connections:
            self._connections[task_id] = [c for c in self._connections[task_id] if c != ws]

    async def broadcast(self, task_id: str, event: dict):
        for ws in self._connections.get(task_id, []):
            try:
                await ws.send_json(event)
            except Exception:
                pass

task_ws_manager = TaskWebSocketManager()

# 事件类型：
# task_precheck_started / task_precheck_completed
# task_understanding_started / task_understanding_completed
# task_planning_started / task_planning_completed
# task_execution_started / task_step_completed
# task_defect_found / task_completed / task_blocked / task_error
```

- [ ] **Step 2: 注册到 main.py**

```python
from app.api.websocket.task_progress import task_ws_manager

@app.websocket("/api/v1/ws/tasks/{task_id}")
async def task_websocket(websocket: WebSocket, task_id: str):
    await task_ws_manager.connect(task_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        task_ws_manager.disconnect(task_id, websocket)
```

- [ ] **Step 3: 在 TaskOrchestrator 中广播事件**

在每个阶段切换时调用 `task_ws_manager.broadcast(task_id, {"type": "...", "data": {...}})`

- [ ] **Step 4: Commit**

```bash
git add app/api/websocket/task_progress.py app/main.py
git commit -m "feat(task): add task-level WebSocket event broadcasting"
```

---

## Phase 2 (P2): 缺陷归因与 AI 交付

### Task 2.1: CausalRuleEngine + LLMCausalJudge

**Files:**
- Create: `app/services/causal_engine.py`
- Modify: `app/services/analysis_service.py`

- [ ] **Step 1: 实现 CausalRuleEngine**

```python
# app/services/causal_engine.py
"""确定性因果规则引擎，处理 80% 常见因果模式，无需 LLM 介入。"""
from datetime import datetime, timedelta
from typing import Any

class CausalRuleEngine:
    """根据已知因果关系模式判断异常关联。"""

    def __init__(self):
        self._time_windows = {
            ("api_error", "console_error"): timedelta(seconds=2),
            ("api_error", "ui_broken"): timedelta(seconds=5),
            ("console_error", "ui_broken"): timedelta(seconds=3),
        }

    def is_causally_related(self, event_a: dict, event_b: dict) -> bool:
        ts_a = event_a.get("timestamp")
        ts_b = event_b.get("timestamp")
        if not ts_a or not ts_b:
            return False
        diff = ts_b - ts_a
        if diff < timedelta(milliseconds=50):  # 太接近视为并发
            return False
        key = (event_a.get("dimension"), event_b.get("dimension"))
        window = self._time_windows.get(key, timedelta(seconds=5))
        if diff > window:
            return False
        # 规则检查
        if key == ("api_error", "console_error"):
            return self._check_api_to_console(event_a, event_b)
        if key == ("api_error", "ui_broken"):
            return self._check_api_to_ui(event_a, event_b)
        if key == ("console_error", "ui_broken"):
            return self._check_console_to_ui(event_a, event_b)
        if key == ("api_error", "api_error"):
            return self._check_api_cascade(event_a, event_b)
        return False

    def _check_api_to_console(self, a: dict, b: dict) -> bool:
        api_url = a.get("data", {}).get("url", "")
        console_msg = b.get("data", {}).get("message", "")
        path = api_url.split("/")[-1] if "/" in api_url else api_url
        return path in console_msg if path else False

    def _check_api_to_ui(self, a: dict, b: dict) -> bool:
        texts = b.get("data", {}).get("visible_texts", [])
        error_patterns = ["系统错误", "网络错误", "加载失败", "请稍后重试", "error"]
        return any(any(p in t.lower() for p in error_patterns) for t in texts)

    def _check_console_to_ui(self, a: dict, b: dict) -> bool:
        msg = a.get("data", {}).get("message", "")
        return "Uncaught" in msg or "unhandled" in msg.lower()

    def _check_api_cascade(self, a: dict, b: dict) -> bool:
        return a.get("data", {}).get("status") == 401 and b.get("data", {}).get("status") == 401
```

- [ ] **Step 2: 实现 LLMCausalJudge**

```python
class LLMCausalJudge:
    """LLM 兜底判断边缘场景因果关系。"""

    def __init__(self, ai_service=None):
        self._ai = ai_service

    async def judge(self, event_a: dict, event_b: dict) -> bool:
        if not self._ai:
            return False
        prompt = f"""判断以下两个异常事件是否有因果关系。
事件 A（先发生）: 维度={event_a.get('dimension')} 类型={event_a.get('type')} 详情={event_a.get('data')}
事件 B（后发生）: 维度={event_b.get('dimension')} 类型={event_b.get('type')} 详情={event_b.get('data')}

标准: (1) A 是否可能导致 B? (2) 涉及同一模块? (3) 时间差合理?
回答: YES 或 NO"""
        try:
            result = await self._ai.analyze_merged({"causal_question": prompt})
            return "YES" in str(result).upper()
        except Exception:
            return False
```

- [ ] **Step 3: 集成到 analysis_service.py**

修改 `_build_evidence_chains` 使用 CausalRuleEngine 代替简单排序。

- [ ] **Step 4: 写测试**

```python
def test_api_error_to_console_error():
    engine = CausalRuleEngine()
    a = {"dimension": "api_error", "timestamp": datetime.now(), "data": {"url": "/api/v1/orders", "status": 500}}
    b = {"dimension": "console_error", "timestamp": datetime.now() + timedelta(seconds=1), "data": {"message": "orderId is undefined"}}
    assert engine.is_causally_related(a, b)

def test_unrelated_not_linked():
    engine = CausalRuleEngine()
    a = {"dimension": "console_error", "timestamp": datetime.now(), "data": {"message": "deprecated api"}}
    b = {"dimension": "ui_broken", "timestamp": datetime.now() + timedelta(seconds=10), "data": {"visible_texts": []}}
    assert not engine.is_causally_related(a, b)
```

- [ ] **Step 5: Commit**

```bash
git add app/services/causal_engine.py app/services/analysis_service.py tests/unit/services/test_causal_engine.py
git commit -m "feat(analysis): add CausalRuleEngine and LLMCausalJudge for defect attribution"
```

---

### Task 2.2: RepairContext + EvidenceChain 强化

**Files:**
- Create: `app/domain/models/repair_context.py`
- Modify: `app/domain/models/task.py`
- Modify: `app/engine/task_orchestrator.py`

- [ ] **Step 1: RepairContext 模型**

```python
# app/domain/models/repair_context.py
from pydantic import BaseModel
from datetime import datetime

class RepairContext(BaseModel):
    """交付给开发者与 AI 助手的修复上下文。"""
    defect_title: str = ""
    task_background: str = ""
    business_goal: str = ""
    reproduction_steps: list[str] = []
    actual_behavior: str = ""
    expected_result: str = ""
    console_errors: list[str] = []
    network_anomalies: list[dict] = []
    root_cause_candidates: list[str] = []
    root_cause_confidence: float = 0.0
    repair_suggestions: list[str] = []
    regression_entries: list[str] = []
    created_at: datetime = Field(default_factory=datetime.now)
```

- [ ] **Step 2: 实现 BuildRepairContext 服务逻辑**

```python
class RepairContextBuilder:
    def from_defect(self, defect: Defect) -> RepairContext:
        return RepairContext(
            defect_title=defect.title,
            reproduction_steps=[str(s) for s in defect.evidence_chains[0].propagation] if defect.evidence_chains else [],
            console_errors=[str(e) for e in defect.console_logs.get("errors", [])],
            network_anomalies=[{"url": a.get("url"), "status": a.get("status")} for a in defect.api_calls],
            root_cause_candidates=[defect.ai_analysis.get("root_cause", "")] if defect.ai_analysis else [],
            repair_suggestions=[defect.fix_suggestion.description] if defect.fix_suggestion else [],
        )
```

- [ ] **Step 3: 集成到 DeliveryPackage**

在 `_analyze_and_deliver` 中构造 `DeliveryPackage` 并挂载到 `TestTask.delivery`。

- [ ] **Step 4: Commit**

```bash
git add app/domain/models/repair_context.py app/engine/task_orchestrator.py
git commit -m "feat(repair): add RepairContext model and delivery integration"
```

---

### Task 2.3: MCP 工具补全

**Files:**
- Modify: `app/api/mcp/server.py`

- [ ] **Step 1: 添加 4 个缺失的 MCP 工具**

```python
@mcp.tool()
async def get_task(task_id: str) -> dict: ...

@mcp.tool()
async def get_task_delivery(task_id: str) -> dict: ...

@mcp.tool()
async def list_task_defects(task_id: str, severity: str = "") -> list[dict]: ...

@mcp.tool()
async def get_repair_context(defect_id: str) -> dict: ...

@mcp.resource("task://{task_id}/delivery")
async def task_delivery_resource(task_id: str) -> str: ...

@mcp.resource("repair-context://{defect_id}")
async def repair_context_resource(defect_id: str) -> str: ...
```

- [ ] **Step 2: Commit**

```bash
git add app/api/mcp/server.py
git commit -m "feat(mcp): add task/delivery/repair-context MCP tools"
```

---

### Task 2.4: 前端缺陷详情页强化

**Files:**
- Modify: `web/src/views/DefectDetail.vue`

- [ ] **Step 1: 按固定模板重构**

实现文档要求的 10 个区块：缺陷概览 → 现象描述 → 复现步骤 → 页面证据 → 控制台证据 → 网络证据 → 根因推断 → 修复建议 → 回归建议 → AI 交付数据预览

- [ ] **Step 2: Commit**

```bash
git add web/src/views/DefectDetail.vue
git commit -m "feat(ui): restructure defect detail page with fixed template"
```

---

## Phase 3 (P3): 基础设施增强

### Task 3.1: 领域事件总线

**Files:**
- Create: `app/lib/event_bus.py`

```python
from collections import defaultdict
from typing import Callable, Any
from datetime import datetime
from app.lib.logger import get_logger

logger = get_logger(__name__)

class DomainEvent:
    def __init__(self, event_type: str, payload: dict, source: str = ""):
        self.event_id = f"evt_{datetime.now().timestamp()}"
        self.event_type = event_type
        self.timestamp = datetime.now()
        self.source = source
        self.payload = payload

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable):
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent):
        for handler in self._handlers.get(event.event_type, []):
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Event handler failed: {handler.__name__} for {event.event_type}: {e}")

event_bus = EventBus()

# 预注册事件类型
TASK_EVENTS = {
    "task_created", "task_precheck_started", "task_precheck_completed",
    "task_understanding_started", "task_understanding_completed",
    "task_planning_started", "task_planning_completed",
    "task_execution_started", "task_step_completed",
    "task_analysis_started", "task_defect_found",
    "task_completed", "task_blocked", "task_cancelled", "task_error",
}
```

- [ ] Commit

---

### Task 3.2: AI 调用缓存

**Files:**
- Create: `app/infrastructure/cache/ai_cache.py`

基于 prompt hash 做 Redis/内存缓存，TTL 3600s，文档更新时按前缀失效。

- [ ] Commit

---

### Task 3.3: 查询缓存

**Files:**
- Create: `app/infrastructure/cache/query_cache.py`

基于 Redis 的查询缓存，支持分布式锁防缓存击穿。

- [ ] Commit

---

### Task 3.4: Webhook 回调系统

**Files:**
- Create: `app/api/webhooks.py`
- Create: `app/services/webhook_service.py`

支持注册/注销 Webhook，事件订阅，HMAC-SHA256 签名，指数退避重试（5 次）。

- [ ] Commit

---

### Task 3.5: Feature Flag 系统

**Files:**
- Create: `app/lib/feature_flags.py`

基于 system_configs 表的动态功能开关。

- [ ] Commit

---

### Task 3.6: Rate Limiting

**Files:**
- Create: `app/api/middleware/rate_limit.py`

基于 Redis 令牌桶算法的限流中间件。

- [ ] Commit

---

### Task 3.7: 补齐 SQLAlchemy 缺失表

**Files:**
- Modify: `app/infrastructure/persistence/models.py`

添加 evidence_chains / async_tasks / audit_logs / system_configs 四个表的 ORM 模型。

- [ ] Commit

---

### Task 3.8: Alembic 初始化

```bash
cd migrations && alembic init alembic
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

- [ ] Commit

---

### Task 3.9: Celery 异步任务实现

**Files:**
- Modify: `app/workers/parse_docs.py`
- Modify: `app/workers/gen_scenarios.py`
- Modify: `app/workers/execute_run.py`

把现有同步逻辑包装为 Celery task，支持进度上报和重试。

- [ ] Commit

---

### Task 3.10: Midscene AI 视觉集成

**Files:**
- Modify: `executor/web/src/step-executor.ts`

在 Level 0 之前添加 AI 视觉定位：调用 Midscene Agent 识别元素 → 置信度 ≥0.6 则使用 → 否则降级到 DOM Level 0/1/2。

- [ ] Commit

---

### Task 3.11: Flaky Test 管理

**Files:**
- Create: `app/services/flaky_service.py`

自动识别 flaky test（同用例 5 次执行通过率 <100%），支持自动重试和分析。

- [ ] Commit

---

### Task 3.12: 知识库版本化 + 增量更新

**Files:**
- Modify: `app/services/knowledge_service.py`

版本号递增，增量更新（只处理变更文档），对比规则变更。

- [ ] Commit

---

### Task 3.13: 规则冲突检测

**Files:**
- Modify: `app/services/knowledge_service.py`

语义去重（embedding 相似度≥0.85）、矛盾检测、自动消解策略。

- [ ] Commit

---

## Phase 4 (P4): 测试覆盖

### Task 4.1: 单元测试补全

| 缺失文件 | 新增测试内容 |
|---------|------------|
| `tests/unit/domain/test_project.py` | Project 状态机、CRUD 验证 |
| `tests/unit/domain/test_knowledge.py` | KnowledgeBase 版本化 |
| `tests/unit/domain/test_scenario.py` | Scenario 生成验证 |
| `tests/unit/domain/test_run.py` | Run 状态转换 |
| `tests/unit/domain/test_task.py` | Task 状态机（已完成） |
| `tests/unit/api/test_tasks_api.py` | 全部 task API 端点 |
| `tests/unit/api/test_settings_api.py` | 设置 API |

- [ ] **Step 1**: 创建 `tests/unit/domain/test_project.py`（~10 个测试用例）
- [ ] **Step 2**: 创建 `tests/unit/api/test_tasks_api.py`（~8 个测试用例）
- [ ] **Step 3**: 创建 `tests/unit/api/test_settings_api.py`（~4 个测试用例）
- [ ] **Step 4**: 运行 `pytest tests/unit/ --cov=app --cov-fail-under=80` → PASS

---

### Task 4.2: 集成测试补全

| 缺失文件 | 新增测试内容 |
|---------|------------|
| `tests/integration/test_run_execution.py` | 创建执行→进度→完成 |
| `tests/integration/test_analysis_engine.py` | 综合分析 |
| `tests/integration/test_mcp_server.py` | MCP 工具 |
| `tests/integration/test_knowledge_api.py` | 知识库 API |
| `tests/integration/test_executor_client.py` | 执行器通信 |

- [ ] **Step 1-5**: 逐个创建，总共 ~20 个测试用例
- [ ] **Step 6**: `pytest tests/integration/ -v` → PASS

---

### Task 4.3: E2E 测试

**Files:**
- Create: `tests/e2e/test_full_pipeline.py`

测试完整流程：CreateTask → Start → Precheck → Understand → Plan → Execute → Analyze → Delivery

- [ ] **Step 1**: 写 E2E test（~5 个测试函数）
- [ ] **Step 2**: `pytest tests/e2e/ -v` → PASS

---

### Task 4.4: 测试数据工厂

**Files:**
- Create: `tests/factories.py`

为 TestTask、Project、Run、Defect 等核心对象提供 factory。

- [ ] Commit

---

## Phase 5 (P5): 前端强化 & 文档同步

### Task 5.1: 知识中心前端

**Files:**
- Create: `web/src/views/KnowledgeCenter.vue`

文档摘要、提取规则、风险点清单、蓝图映射关系。

- [ ] Commit

---

### Task 5.2: 自动化完成度可视化

**Files:**
- Modify: `web/src/views/Dashboard.vue`

在首页展示：自动准备/理解/执行/诊断完成度、需人工介入点数量。

- [ ] Commit

---

### Task 5.3: 最终导航重构

```typescript
// 最终导航顺序
1. 🚀 新建自动测试（首页）
2. 📋 测试任务
3. 📖 知识/文档
4. 🐛 缺陷中心
5. ⚙️ 系统设置
```

旧的 `Projects` 入口挪到设置页面或归档区。

- [ ] Commit

---

### Task 5.4: 文档同步回写

- [ ] **Step 1**: 更新 `REQUIREMENTS.md` — 确认 TestTask 已实现，补充新的功能需求
- [ ] **Step 2**: 更新 `ARCHITECTURE.md` — 加入 TaskOrchestrator 流程图
- [ ] **Step 3**: 更新 `API接口规范.md` — 确认任务 API 已实现
- [ ] **Step 4**: 更新 `全自动AI测试文档总览.md` — 状态改为已落地
- [ ] Commit

---

### Task 5.5: CSV 报告导出

**Files:**
- Create: `web/src/views/ReportExport.vue`

支持缺陷列表、执行报告导出为 CSV/JSON。

- [ ] Commit

---

## 附录：文件变更总清单

### 新建文件（共 ~30 个）

```
app/domain/models/task.py              # TestTask 聚合根
app/domain/models/repair_context.py     # 修复上下文
app/interfaces/repositories/task_repo.py
app/infrastructure/persistence/task_repo.py
app/api/v1/tasks.py                    # 任务 API
app/engine/task_orchestrator.py         # 八阶段编排器
app/services/causal_engine.py           # 因果规则引擎
app/api/websocket/task_progress.py      # 任务 WebSocket
app/api/webhooks.py                     # Webhook 系统
app/services/webhook_service.py
app/lib/event_bus.py                    # 事件总线
app/lib/feature_flags.py                # Feature Flag
app/infrastructure/cache/ai_cache.py    # AI 缓存
app/infrastructure/cache/query_cache.py # 查询缓存
app/api/middleware/rate_limit.py        # 限流中间件
app/services/flaky_service.py           # Flaky 管理
web/src/api/taskApi.ts                  # 前端 task API
web/src/views/TaskList.vue              # 任务列表
web/src/views/TaskDetail.vue            # 任务详情
web/src/views/KnowledgeCenter.vue       # 知识中心
web/src/views/ReportExport.vue          # 报告导出
tests/factories.py                      # 测试工厂
tests/e2e/test_full_pipeline.py         # E2E 测试
tests/unit/domain/test_task.py          # Task 单元测试
tests/unit/api/test_tasks_api.py        # Task API 测试
tests/unit/api/test_settings_api.py     # 设置 API 测试
tests/unit/services/test_causal_engine.py
tests/integration/test_run_execution.py
tests/integration/test_analysis_engine.py
tests/integration/test_mcp_server.py
tests/integration/test_executor_client.py
```

### 修改文件（共 ~12 个）

```
app/main.py                  # 注册 task routes + WS + middleware
app/dependencies.py           # 注入 task repo
app/services/analysis_service.py  # 集成 CausalRuleEngine
app/engine/execution_engine.py     # 兼容 TestTask
app/infrastructure/persistence/models.py  # 新增表
app/workers/parse_docs.py       # 实现
app/workers/gen_scenarios.py    # 实现
app/workers/execute_run.py      # 实现
app/api/mcp/server.py           # 补齐工具
web/src/router.ts               # 新导航结构
web/src/views/Dashboard.vue     # 新首页
web/src/views/DefectDetail.vue  # 强化
docs/ 下的 4 个文档             # 同步更新
```

---

## 执行顺序建议

```
Week 1-2:  P1 (Tasks 1.1-1.4)  → 后端核心主线
Week 2-3:  P1 (Tasks 1.5-1.7)  → 前端 + WebSocket
Week 3-4:  P2 (Tasks 2.1-2.2)  → 缺陷归因引擎
Week 4:    P2 (Tasks 2.3-2.4)  → MCP + 前端缺陷页
Week 5-6:  P3 (Tasks 3.1-3.7)  → 基础设施（可并行）
Week 6-7:  P3 (Tasks 3.8-3.13) → 异步任务 + 知识库（可并行）
Week 7-9:  P4 (All)            → 测试覆盖
Week 9-10: P5 (All)            → 前端强化 + 文档同步
```

每个 Task 都是独立可提交的增量。建议用 `task()` 分配的并行 agent 实现独立 Task。
