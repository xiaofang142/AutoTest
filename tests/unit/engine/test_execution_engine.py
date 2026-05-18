"""Tests for ExecutionEngine — the core test execution orchestrator."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.models.run import RunRecord, StepExecutionRecord
from app.domain.models.scenario import TestStep
from app.engine.execution_engine import ExecutionEngine


@pytest.fixture
def run_repo_mock():
    repo = AsyncMock()
    repo.get_by_id.return_value = RunRecord(id="run_001", project_id="p1", platforms=["web"])
    return repo


@pytest.fixture
def scenario_repo_mock():
    return AsyncMock()


@pytest.fixture
def defect_repo_mock():
    repo = AsyncMock()
    repo.create = AsyncMock(side_effect=lambda x: x)
    return repo


@pytest.fixture
def executor_mock():
    executor = AsyncMock()
    executor.ping.return_value = True
    executor.navigate.return_value = MagicMock(success=True, current_url="https://example.com")
    executor.execute_step.return_value = StepExecutionRecord(
        id="step_001", run_id="run_001", case_id="tc_1",
        step_index=0, action="click", status="passed",
    )
    return executor


@pytest.fixture
def analyzer_mock():
    analyzer = AsyncMock()
    analyzer.analyze.return_value = None  # no defect
    return analyzer


@pytest.fixture
def engine(run_repo_mock, scenario_repo_mock, defect_repo_mock, executor_mock, analyzer_mock):
    return ExecutionEngine(
        run_repo=run_repo_mock,
        scenario_repo=scenario_repo_mock,
        defect_repo=defect_repo_mock,
        executor=executor_mock,
        analyzer=analyzer_mock,
    )


class TestExecuteRun:
    @pytest.mark.asyncio
    async def test_success_path(self, engine, run_repo_mock, executor_mock):
        """Happy path: ping → navigate → execute step → complete."""
        steps = [TestStep(index=1, action="click", target="登录")]
        result = await engine.execute_run("run_001", target_url="https://example.com", steps=steps)

        executor_mock.ping.assert_called_once()
        executor_mock.navigate.assert_called_once_with("https://example.com")
        executor_mock.execute_step.assert_called_once()
        run_repo_mock.update_status.assert_called_with("run_001", "completed")
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_executor_unreachable(self, engine, executor_mock):
        """Executor ping fails → return error."""
        executor_mock.ping.return_value = False
        result = await engine.execute_run("run_001")
        assert "error" in result
        assert "not reachable" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_navigation_failure(self, engine, executor_mock):
        """Navigation raises exception → return error."""
        executor_mock.navigate.side_effect = RuntimeError("Navigation timeout")
        result = await engine.execute_run("run_001", target_url="https://example.com")
        assert "error" in result
        assert "Navigation" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_multiple_steps_tracked(self, engine, executor_mock):
        """Multiple steps → all executed and counted."""
        steps = [
            TestStep(index=1, action="click", target="登录"),
            TestStep(index=2, action="type", target="密码", value="123"),
        ]
        result = await engine.execute_run("run_001", target_url="https://example.com", steps=steps)
        assert executor_mock.execute_step.call_count == 2
        assert result["summary"]["total"] == 2

    @pytest.mark.asyncio
    async def test_defect_collected(self, engine, analyzer_mock, defect_repo_mock):
        """Analyzer detects defect → it appears in results."""
        from app.domain.models.defect import Defect
        fake_defect = Defect(id="def_001", run_id="run_001", severity="medium", title="Console error")
        analyzer_mock.analyze.return_value = fake_defect

        steps = [TestStep(index=1, action="click", target="登录")]
        result = await engine.execute_run("run_001", target_url="https://example.com", steps=steps)
        assert len(result["defects"]) == 1
        assert result["defects"][0]["id"] == "def_001"

    @pytest.mark.asyncio
    async def test_run_not_found(self, engine, run_repo_mock):
        """Run ID doesn't exist → return error."""
        run_repo_mock.get_by_id.return_value = None
        result = await engine.execute_run("nonexistent")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_progress_updates(self, engine, run_repo_mock, executor_mock):
        """Progress should be updated after each step."""
        steps = [TestStep(index=1, action="click", target="登录")]
        await engine.execute_run("run_001", target_url="https://example.com", steps=steps)
        update_calls = [c for c in run_repo_mock.update_progress.call_args_list]
        assert len(update_calls) >= 1
        last_update = update_calls[-1][0][1]
        assert last_update["percent"] == 100
