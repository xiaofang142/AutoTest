"""E2E 业务流1: QA工程师完整流程

模拟QA工程师操作:
  1. 打开首页 → 输入网址 → 创建任务
  2. 启动测试 → 等待各阶段完成
  3. 查看预检/理解/蓝图结果
  4. 查看缺陷列表
  5. 查看交付包(三类视图)
  6. 查看回归建议
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock

from app.domain.models.task import (
    TestTask, TaskInput, TaskMode, TaskGoal,
)
from app.domain.models.run import (
    StepExecutionRecord, ConsoleSnapshot, NetworkSnapshot,
    PageState, ConsoleLogEntry, NetworkEntry,
)
from app.engine.execution_engine import ExecutionEngine
from app.engine.task_orchestrator import TaskOrchestrator
from app.infrastructure.persistence.task_repo import InMemoryTaskRepository
from tests.mock_repos import MemRunRepo


@pytest.fixture
def task_repo():
    return InMemoryTaskRepository()


@pytest.fixture
def run_repo():
    return MemRunRepo()


@pytest.fixture
def mock_steps():
    steps_data = [
        {"step_index": i, "action": action, "status": "passed", "duration_ms": 200}
        for i, action in enumerate(["navigate to login page", "input username", "input password", "click login button", "wait for dashboard"])
    ]
    # 模拟第三步后出现API错误
    steps_data[3]["status"] = "failed"
    return steps_data


@pytest.fixture
def mock_engine_with_defects(mock_steps):
    eng = AsyncMock(spec=ExecutionEngine)
    eng.executor_ping.return_value = True
    eng.execute_run.return_value = {
        "run_id": "run_e2e_qa_001",
        "status": "completed_with_defects",
        "summary": {"total": 5, "passed": 4, "failed": 1, "defects": 2},
        "defects": [
            {"id": "def_001", "severity": "high", "title": "Login API 500",
             "type": "api_error", "evidence_count": 3},
            {"id": "def_002", "severity": "medium", "title": "Dashboard not loaded",
             "type": "ui_mismatch", "evidence_count": 2},
        ],
        "steps": mock_steps,
    }
    return eng


class TestQAEngineerE2EFlow:
    """QA工程师完整流程：一句话输入→全自动测试→可修复报告"""

    @pytest.mark.asyncio
    async def test_full_qa_workflow(self, task_repo, run_repo, mock_engine_with_defects):
        """=== 步骤1: QA工程师输入网址创建任务 ==="""
        task = TestTask(
            name="冒烟测试-登录功能",
            description="验证登录页面是否正常工作",
            input=TaskInput(
                target_url="https://example.com/login",
                target_type="web",
                environment="dev",
            ),
            mode=TaskMode.QUICK,
            goal=TaskGoal.SMOKE,
            source="web_ui",
        )
        task = await task_repo.create(task)
        assert task.id.startswith("task_"), "任务创建失败: ID格式不正确"
        assert task.status.value == "draft", f"初始状态应为draft, 当前={task.status}"
        assert task.input.target_url == "https://example.com/login"
        assert task.current_stage == "draft"

        """=== 步骤2: 启动测试 ==="""
        from app.domain.models.task import TaskStateMachine, TaskStatus
        assert TaskStateMachine.can_transition(task.status, TaskStatus.PRECHECKING)
        await task_repo.update_status(task.id, "prechecking", "prechecking")

        """=== 步骤3: 进入执行管线 ==="""
        orch = TaskOrchestrator(task_repo, mock_engine_with_defects, run_repo)
        pipeline_result = await orch.run_pipeline(task.id)
        assert pipeline_result["status"] == "completed_with_defects", \
            f"管线执行异常: {pipeline_result}"

        """=== 步骤4: 检查各阶段产物 ==="""
        updated = await task_repo.get_by_id(task.id)

        # 预检结果
        assert updated.environment_check is not None
        assert updated.environment_check.executor_online is True
        assert updated.environment_check.blocking_items == []
        print("[PASS] 环境预检: 执行器在线, 无阻塞项")

        # 理解结果
        assert updated.understanding is not None
        assert updated.understanding.completeness > 0
        assert updated.understanding.page_intent != ""
        print(f"[PASS] 页面理解: {updated.understanding.page_intent}")

        # 蓝图结果
        assert updated.blueprint is not None
        assert len(updated.blueprint.flow_chains) > 0
        print(f"[PASS] 测试蓝图: {len(updated.blueprint.all_steps)}个步骤")

        """=== 步骤5: 查看任务进度 ==="""
        assert updated.progress_percent == 100
        assert updated.current_stage in ("completed", "completed_with_defects")
        print(f"[PASS] 任务完成: {updated.current_stage}, 进度100%")

        """=== 步骤6: 查看自动化等级 ==="""
        assert updated.auto_level is not None
        print(f"[PASS] 自动化等级: {updated.auto_level.value}")

        """=== 步骤7: 查看缺陷列表 ==="""
        assert updated.defect_count == 2
        assert updated.high_risk_count == 1
        print(f"[PASS] 缺陷: {updated.defect_count}个 (高风险{updated.high_risk_count}个)")

        """=== 步骤8: 查看交付包 ==="""
        delivery = updated.delivery
        assert delivery is not None

        # 测试人员视图
        assert delivery.tester_view.summary != ""
        assert len(delivery.tester_view.defect_list) > 0
        print(f"[PASS] 测试人员视图: {delivery.tester_view.summary}")

        # 开发者视图
        assert len(delivery.developer_view.defect_details) > 0
        print(f"[PASS] 开发者视图: {len(delivery.developer_view.defect_details)}个缺陷")

        # AI助手视图
        assert len(delivery.ai_assistant_view.reproduction_steps) > 0
        print(f"[PASS] AI助手视图: {len(delivery.ai_assistant_view.reproduction_steps)}个步骤")

        """=== 步骤9: 查看回归建议 ==="""
        assert delivery.regression_entry is not None
        assert delivery.regression_entry.get("target_url") == task.input.target_url
        assert delivery.regression_entry.get("task_id") == task.id
        print(f"[PASS] 回归入口: {delivery.regression_entry['target_url']}")

        """=== 步骤10: 验证状态不可逆 ==="""
        assert TaskStateMachine.is_terminal(updated.status)
        assert not TaskStateMachine.can_transition(updated.status, TaskStatus.DRAFT)
        print("[PASS] 状态不可逆: 终态正确")

        print("\n========== QA工程师完整流程通过! ==========")
