"""TestTask — 全自动 AI 测试任务的一等聚合根。

承载一次完整测试生命周期：
  输入目标 → 环境预检 → 测试理解 → 蓝图生成 → 执行 → 校验 → 归因 → 交付

对应文档：
  - 全自动AI测试闭环设计.md  §8  状态机
  - 自动测试任务模型设计.md  §5  模型定义
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Enums ────────────────────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    """任务状态 — 对应八阶段闭环的 11 种状态。"""
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
    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"
    A5 = "A5"


# ── 子对象模型 ───────────────────────────────────────────────────────────────

class TaskInput(BaseModel):
    target_type: str = "web"
    target_url: str = ""
    target_app: str = ""
    code_dir: str = ""  # 本地项目源码目录路径, 用于代码分析
    environment: str = "dev"
    scope: str = ""
    documents: list[str] = Field(default_factory=list)
    account_info: dict = Field(default_factory=dict)
    platform_config: dict = Field(default_factory=dict)
    user_notes: str = ""
    priority_targets: list[str] = Field(default_factory=list)


class EnvironmentCheck(BaseModel):
    """环境与能力预检结果。"""
    executor_online: bool = False
    browser_available: bool = False
    network_ok: bool = False
    login_ready: bool = False
    ocr_available: bool = False
    ai_available: bool = False
    console_capture: bool = False
    network_capture: bool = False
    auto_fixable_items: list[str] = Field(default_factory=list)
    blocking_items: list[str] = Field(default_factory=list)
    auto_level: str = "A0"
    summary: str = ""


class UnderstandingResult(BaseModel):
    """页面 + 文档理解结果。"""
    page_intent: str = ""
    document_intent: str = ""
    key_roles: list[str] = Field(default_factory=list)
    key_flows: list[str] = Field(default_factory=list)
    risk_points: list[str] = Field(default_factory=list)
    must_test_assertions: list[str] = Field(default_factory=list)
    page_objects: list[dict] = Field(default_factory=list)
    doc_page_conflicts: list[str] = Field(default_factory=list)
    completeness: float = 0.0


class BlueprintStep(BaseModel):
    """蓝图中一个测试步骤。"""
    index: int = 0
    action: str = ""
    target: str = ""
    value: str = ""
    assert_ui: bool = True
    assert_console: bool = True
    assert_api: bool = True
    assert_business: bool = False
    expected_url: str = ""
    expected_text: str = ""
    priority: int = 1
    risk_point: str = ""


class TestBlueprint(BaseModel):
    """自动生成的测试蓝图。"""
    __test__ = False
    targets: list[dict] = Field(default_factory=list)
    flow_chains: list[list[BlueprintStep]] = Field(default_factory=list)
    all_steps: list[BlueprintStep] = Field(default_factory=list)
    assertions: list[dict] = Field(default_factory=list)
    confidence: float = 0.0
    risk_coverage: str = ""
    min_executable_set: list[int] = Field(default_factory=list)


class TesterView(BaseModel):
    """面向测试人员的交付视图。"""
    summary: str = ""
    defect_list: list[dict] = Field(default_factory=list)
    steps_with_screenshots: list[dict] = Field(default_factory=list)


class DeveloperView(BaseModel):
    """面向开发者的交付视图。"""
    defect_details: list[dict] = Field(default_factory=list)
    evidence_chains: list[dict] = Field(default_factory=list)
    root_cause: str = ""
    fix_suggestion: str = ""


class AIAssistantView(BaseModel):
    """面向 AI 助手的结构化交付视图。"""
    task_summary: str = ""
    defect_summary: str = ""
    reproduction_steps: list[str] = Field(default_factory=list)
    console_errors: list[str] = Field(default_factory=list)
    network_failures: list[dict] = Field(default_factory=list)
    page_state: dict = Field(default_factory=dict)
    root_cause_candidates: list[str] = Field(default_factory=list)
    repair_suggestion: str = ""


class DeliveryPackage(BaseModel):
    """三类交付结果 + 回归入口。"""
    tester_view: TesterView = Field(default_factory=TesterView)
    developer_view: DeveloperView = Field(default_factory=DeveloperView)
    ai_assistant_view: AIAssistantView = Field(default_factory=AIAssistantView)
    regression_entry: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)


# ── TestTask 主模型 ──────────────────────────────────────────────────────────

class TestTask(BaseModel):
    __test__ = False
    model_config = {"extra": "forbid"}
    # 基础信息
    id: str = ""
    project_id: str = ""
    name: str = ""
    description: str = ""
    source: str = "web_ui"
    created_by: str = ""

    # 输入与模式
    input: TaskInput = Field(default_factory=TaskInput)
    mode: TaskMode = TaskMode.QUICK
    goal: TaskGoal = TaskGoal.SMOKE
    depth: TaskDepth = TaskDepth.STANDARD

    # 阶段状态
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
    run_id: str = ""

    # 结果
    final_status: str = ""
    summary: str = ""
    defect_count: int = 0
    high_risk_count: int = 0
    auto_level: AutoLevel = AutoLevel.A0
    delivery_ready: bool = False
    delivery: Optional[DeliveryPackage] = None

    # 元数据
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None


# ── 状态机 ────────────────────────────────────────────────────────────────────

class TaskStateMachine:
    """TestTask 状态机 — 验证状态转换合法性。

    状态流转:
      draft → prechecking → understanding → planning → running → analyzing
        → completed / completed_with_defects
      任意阶段 → blocked / cancelled / error
    """

    VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
        TaskStatus.DRAFT: {TaskStatus.PRECHECKING, TaskStatus.CANCELLED},
        TaskStatus.PRECHECKING: {TaskStatus.UNDERSTANDING, TaskStatus.BLOCKED,
                                  TaskStatus.CANCELLED, TaskStatus.ERROR},
        TaskStatus.UNDERSTANDING: {TaskStatus.PLANNING, TaskStatus.BLOCKED,
                                    TaskStatus.CANCELLED, TaskStatus.ERROR},
        TaskStatus.PLANNING: {TaskStatus.RUNNING, TaskStatus.BLOCKED,
                               TaskStatus.CANCELLED, TaskStatus.ERROR},
        TaskStatus.RUNNING: {TaskStatus.ANALYZING, TaskStatus.BLOCKED,
                              TaskStatus.CANCELLED, TaskStatus.ERROR},
        TaskStatus.ANALYZING: {TaskStatus.COMPLETED, TaskStatus.COMPLETED_WITH_DEFECTS,
                                TaskStatus.BLOCKED, TaskStatus.ERROR},
        TaskStatus.COMPLETED: set(),
        TaskStatus.COMPLETED_WITH_DEFECTS: set(),
        TaskStatus.BLOCKED: {TaskStatus.DRAFT, TaskStatus.CANCELLED},
        TaskStatus.CANCELLED: set(),
        TaskStatus.ERROR: {TaskStatus.DRAFT},
    }

    @classmethod
    def can_transition(cls, current: TaskStatus, target: TaskStatus) -> bool:
        return target in cls.VALID_TRANSITIONS.get(current, set())

    @classmethod
    def allowed_actions(cls, status: TaskStatus) -> list[str]:
        actions = {
            TaskStatus.DRAFT: ["start", "cancel"],
            TaskStatus.PRECHECKING: ["wait"],
            TaskStatus.UNDERSTANDING: ["wait"],
            TaskStatus.PLANNING: ["wait"],
            TaskStatus.RUNNING: ["wait", "cancel"],
            TaskStatus.ANALYZING: ["wait"],
            TaskStatus.COMPLETED: ["view_report"],
            TaskStatus.COMPLETED_WITH_DEFECTS: ["view_report", "view_defects"],
            TaskStatus.BLOCKED: ["retry", "cancel"],
            TaskStatus.CANCELLED: ["delete"],
            TaskStatus.ERROR: ["retry", "cancel"],
        }
        return actions.get(status, [])

    @classmethod
    def is_terminal(cls, status: TaskStatus) -> bool:
        return status in (TaskStatus.COMPLETED, TaskStatus.COMPLETED_WITH_DEFECTS,
                          TaskStatus.CANCELLED)
