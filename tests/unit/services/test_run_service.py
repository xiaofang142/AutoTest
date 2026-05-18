from unittest.mock import AsyncMock

import pytest

from app.domain.exceptions import InvalidParameterError, RunNotFoundError
from app.domain.models.run import RunRecord, StepExecutionRecord
from app.domain.models.scenario import TestScenario
from app.services.run_service import RunService


@pytest.fixture
def run_repo_mock():
    repo = AsyncMock()
    repo.create = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_project = AsyncMock(return_value=[])
    repo.update_status = AsyncMock()
    repo.update_progress = AsyncMock()
    repo.save_step = AsyncMock()
    return repo


@pytest.fixture
def scenario_repo_mock():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def service(run_repo_mock, scenario_repo_mock):
    return RunService(run_repo_mock, scenario_repo_mock)


@pytest.mark.asyncio
class TestCreateRun:
    async def test_success(self, service, run_repo_mock):
        run_repo_mock.create.return_value = RunRecord(id="run_001", project_id="p1", platforms=["web"])
        result = await service.create_run("p1", ["web"])
        assert result.id == "run_001"
        assert result.platforms == ["web"]

    async def test_no_platform(self, service):
        with pytest.raises(InvalidParameterError):
            await service.create_run("p1", [])

    async def test_with_scenario_ids(self, service, run_repo_mock, scenario_repo_mock):
        from app.domain.models.scenario import TestCase, TestStep
        scenario_repo_mock.get_by_id.return_value = TestScenario(
            id="sce_001", project_id="p1", name="Test",
            cases=[TestCase(id="tc_1", name="Case 1", steps=[TestStep(index=1, action="click")])])
        run_repo_mock.create.return_value = RunRecord(id="run_002", project_id="p1", platforms=["web"], total_cases=1)
        result = await service.create_run("p1", ["web"], scenario_ids=["sce_001"])
        assert result.total_cases == 1


@pytest.mark.asyncio
class TestGetRun:
    async def test_found(self, service, run_repo_mock):
        run_repo_mock.get_by_id.return_value = RunRecord(id="run_001", project_id="p1", platforms=["web"])
        result = await service.get_run("run_001")
        assert result.id == "run_001"

    async def test_not_found(self, service, run_repo_mock):
        run_repo_mock.get_by_id.return_value = None
        with pytest.raises(RunNotFoundError):
            await service.get_run("run_nonexist")


@pytest.mark.asyncio
class TestRunLifecycle:
    async def test_cancel_run(self, service, run_repo_mock):
        run_repo_mock.get_by_id.return_value = RunRecord(id="run_001", project_id="p1", platforms=["web"])
        await service.cancel_run("run_001")
        run_repo_mock.update_status.assert_called_with("run_001", "cancelled")

    async def test_save_step(self, service, run_repo_mock):
        step = StepExecutionRecord(id="step_001", run_id="run_001", case_id="tc_1", step_index=1,
                                    action="click", status="passed")
        result = await service.save_step(step)
        run_repo_mock.save_step.assert_called_once()

    async def test_retry_run(self, service, run_repo_mock):
        run_repo_mock.get_by_id.return_value = RunRecord(id="run_001", project_id="p1", platforms=["web"])
        run_repo_mock.create.return_value = RunRecord(id="run_002", project_id="p1", platforms=["web"], name=" (retry)")
        result = await service.retry_run("run_001")
        assert "(retry)" in result.name

    async def test_get_run_history(self, service, run_repo_mock):
        run_repo_mock.get_by_project.return_value = [
            RunRecord(id="r1", project_id="p1", platforms=["web"], status="completed"),
            RunRecord(id="r2", project_id="p1", platforms=["web"], status="failed"),
        ]
        history = await service.get_run_history("p1")
        assert len(history) == 2
