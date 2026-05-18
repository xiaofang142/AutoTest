"""业务线: 任务全生命周期测试

流程: 创建Task → 启动 → 预检 → 理解 → 蓝图 → 执行 → 归因 → 交付
"""
import pytest
from unittest.mock import AsyncMock

from app.domain.models.task import (
    TestTask, TaskInput, TaskStatus, TaskMode, TaskStateMachine,
    EnvironmentCheck, UnderstandingResult,
)
from app.engine.execution_engine import ExecutionEngine
from app.engine.task_orchestrator import TaskOrchestrator
from app.infrastructure.persistence.task_repo import InMemoryTaskRepository
from tests.mock_repos import MemRunRepo as InMemoryRunRepository


@pytest.fixture
def task_repo():
    return InMemoryTaskRepository()


@pytest.fixture
def run_repo():
    return InMemoryRunRepository()


@pytest.fixture
def mock_engine():
    eng = AsyncMock(spec=ExecutionEngine)
    eng.executor_ping.return_value = True
    eng.execute_run.return_value = {
        "run_id": "run_test_001",
        "status": "completed",
        "summary": {"total": 3, "passed": 3, "failed": 0, "defects": 0},
        "defects": [],
        "steps": [
            {"step_index": i, "action": f"step_{i}", "status": "passed", "duration_ms": 100}
            for i in range(3)
        ],
    }
    return eng


class TestTaskBusinessFlow:
    """业务线1: 任务完整生命周期"""

    async def _create_task(self, repo) -> TestTask:
        task = TestTask(
            name="登录功能冒烟测试",
            description="验证登录页面核心功能",
            input=TaskInput(target_url="https://example.com/login"),
            mode=TaskMode.QUICK,
        )
        return await repo.create(task)

    @pytest.mark.asyncio
    async def test_1_create_task(self, task_repo):
        """创建任务 → 验证初始状态"""
        task = await self._create_task(task_repo)
        assert task.id.startswith("task_")
        assert task.status == TaskStatus.DRAFT
        assert task.input.target_url == "https://example.com/login"
        assert task.mode == TaskMode.QUICK
        assert task.current_stage == "draft"
        assert task.progress_percent == 0

    @pytest.mark.asyncio
    async def test_2_start_task(self, task_repo):
        """启动任务 → 状态变更为 prechecking"""
        task = await self._create_task(task_repo)
        assert TaskStateMachine.can_transition(task.status, TaskStatus.PRECHECKING)
        await task_repo.update_status(task.id, "prechecking", "prechecking")
        updated = await task_repo.get_by_id(task.id)
        assert updated.status == TaskStatus.PRECHECKING
        assert updated.current_stage == "prechecking"

    @pytest.mark.asyncio
    async def test_3_full_pipeline(self, task_repo, run_repo, mock_engine):
        """完整管线: precheck → understand → plan → execute → deliver"""
        task = await self._create_task(task_repo)
        orch = TaskOrchestrator(task_repo, mock_engine, run_repo)
        result = await orch.run_pipeline(task.id)

        assert result["status"] in ("completed", "completed_with_defects")
        updated = await task_repo.get_by_id(task.id)

        # 验证所有阶段产物
        assert updated.environment_check is not None
        assert updated.environment_check.executor_online is True
        assert updated.understanding is not None
        assert isinstance(updated.understanding, UnderstandingResult)
        assert updated.blueprint is not None
        assert updated.delivery is not None
        assert updated.delivery_ready is True
        assert updated.progress_percent == 100

        # 验证自动化等级
        assert updated.auto_level.value in ("A4", "A5")

        # 验证交付包内容
        delivery = updated.delivery
        assert delivery.tester_view.summary != ""
        assert delivery.regression_entry.get("target_url") == task.input.target_url
        assert delivery.regression_entry.get("task_id") == task.id

    @pytest.mark.asyncio
    async def test_4_pipeline_blocked(self, task_repo, run_repo):
        """执行器离线 → pipeline 阻塞"""
        eng = AsyncMock(spec=ExecutionEngine)
        eng.executor_ping.return_value = False

        task = await self._create_task(task_repo)
        orch = TaskOrchestrator(task_repo, eng, run_repo)
        result = await orch.run_pipeline(task.id)

        assert result["status"] == "blocked"
        updated = await task_repo.get_by_id(task.id)
        assert updated.status == TaskStatus.BLOCKED
        assert updated.current_stage == "prechecking"

    @pytest.mark.asyncio
    async def test_5_pipeline_error_recovery(self, task_repo, run_repo):
        """引擎异常 → pipeline 进入 error 状态"""
        eng = AsyncMock(spec=ExecutionEngine)
        eng.executor_ping.side_effect = RuntimeError("Executor crashed")

        task = await self._create_task(task_repo)
        orch = TaskOrchestrator(task_repo, eng, run_repo)
        result = await orch.run_pipeline(task.id)

        assert result["status"] == "error"
        updated = await task_repo.get_by_id(task.id)
        assert updated.status == TaskStatus.ERROR

    @pytest.mark.asyncio
    async def test_6_cancel_during_pipeline(self, task_repo):
        """中途取消 → 状态变更为 cancelled"""
        task = await self._create_task(task_repo)
        # 模拟在 prechecking 阶段取消
        await task_repo.update_status(task.id, "prechecking", "prechecking")
        await task_repo.update_status(task.id, "cancelled", "")
        updated = await task_repo.get_by_id(task.id)
        assert updated.status == TaskStatus.CANCELLED
        assert TaskStateMachine.is_terminal(updated.status)

    @pytest.mark.asyncio
    async def test_7_state_machine_all_transitions(self, task_repo):
        """验证所有合法的状态转换"""
        task = await self._create_task(task_repo)
        transitions = [
            (TaskStatus.DRAFT, TaskStatus.PRECHECKING),
            (TaskStatus.PRECHECKING, TaskStatus.UNDERSTANDING),
            (TaskStatus.UNDERSTANDING, TaskStatus.PLANNING),
            (TaskStatus.PLANNING, TaskStatus.RUNNING),
            (TaskStatus.RUNNING, TaskStatus.ANALYZING),
            (TaskStatus.ANALYZING, TaskStatus.COMPLETED),
            (TaskStatus.COMPLETED_WITH_DEFECTS, None),  # terminal
        ]
        current = task.status
        for src, tgt in transitions:
            if tgt is None:
                assert TaskStateMachine.is_terminal(src)
                continue
            assert TaskStateMachine.can_transition(src, tgt)
            await task_repo.update_status(task.id, tgt.value, tgt.value)
            current = tgt

    @pytest.mark.asyncio
    async def test_8_invalid_transitions(self, task_repo):
        """验证非法转换被拒绝"""
        task = await self._create_task(task_repo)
        invalid = [
            (TaskStatus.DRAFT, TaskStatus.COMPLETED),
            (TaskStatus.DRAFT, TaskStatus.ANALYZING),
            (TaskStatus.RUNNING, TaskStatus.DRAFT),
            (TaskStatus.CANCELLED, TaskStatus.PRECHECKING),
            (TaskStatus.ERROR, TaskStatus.COMPLETED),
        ]
        for src, tgt in invalid:
            assert not TaskStateMachine.can_transition(src, tgt), f"{src} -> {tgt} should be invalid"

    @pytest.mark.asyncio
    async def test_9_view_delivery_after_pipeline(self, task_repo, run_repo, mock_engine):
        """管线完成后 → 查看交付内容包含三类视图"""
        task = await self._create_task(task_repo)
        orch = TaskOrchestrator(task_repo, mock_engine, run_repo)
        await orch.run_pipeline(task.id)

        updated = await task_repo.get_by_id(task.id)
        delivery = updated.delivery

        assert delivery.tester_view.summary != ""
        assert delivery.developer_view is not None
        assert delivery.ai_assistant_view is not None
        assert len(delivery.ai_assistant_view.reproduction_steps) > 0
        assert delivery.ai_assistant_view.task_summary == task.name


class TestRunRecordFlow:
    """业务线2: RunRecord 创建与关联"""

    @pytest.mark.asyncio
    async def test_run_record_created_with_task_id(self, task_repo, run_repo, mock_engine):
        task = TestTask(name="test", input=TaskInput(target_url="https://x.com"))
        task = await task_repo.create(task)
        orch = TaskOrchestrator(task_repo, mock_engine, run_repo)
        await orch.run_pipeline(task.id)

        # The RunRecord created by TaskOrchestrator uses "run_{task.id}" pattern
        expected_run_id = f"run_{task.id}"
        run = await run_repo.get_by_id(expected_run_id)
        assert run is not None, f"RunRecord {expected_run_id} not found"
        assert run.task_id == task.id

    @pytest.mark.asyncio
    async def test_auto_level_calculated(self, task_repo, run_repo, mock_engine):
        task = TestTask(name="test", input=TaskInput(target_url="https://x.com"))
        task = await task_repo.create(task)
        orch = TaskOrchestrator(task_repo, mock_engine, run_repo)
        await orch.run_pipeline(task.id)

        updated = await task_repo.get_by_id(task.id)
        assert updated.auto_level is not None
        assert updated.auto_level.value in ("A0", "A1", "A2", "A3", "A4", "A5")
