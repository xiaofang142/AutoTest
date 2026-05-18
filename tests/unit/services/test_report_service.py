from unittest.mock import AsyncMock

import pytest

from app.domain.models.defect import Defect
from app.domain.models.run import RunRecord
from app.services.report_service import ReportService


@pytest.fixture
def run_repo_mock():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_project = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def defect_repo_mock():
    repo = AsyncMock()
    repo.get_by_run = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def service(run_repo_mock, defect_repo_mock):
    return ReportService(run_repo_mock, defect_repo_mock)


@pytest.mark.asyncio
class TestGetRunReport:
    async def test_summary_format(self, service, run_repo_mock, defect_repo_mock):
        run_repo_mock.get_by_id.return_value = RunRecord(
            id="run_001", project_id="p1", platforms=["web"], status="completed",
            total_cases=10, passed_count=8, failed_count=1, uncertain_count=1)
        defect_repo_mock.get_by_run.return_value = [
            Defect(id="def_001", run_id="run_001", title="API Error", severity="high")]
        report = await service.get_run_report("run_001", "summary")
        assert report["run_id"] == "run_001"
        assert report["total_cases"] == 10
        assert report["passed"] == 8
        assert report["failed"] == 1
        assert report["defect_count"] == 1
        assert report["pass_rate"] == 0.8

    async def test_full_format(self, service, run_repo_mock, defect_repo_mock):
        run_repo_mock.get_by_id.return_value = RunRecord(
            id="run_001", project_id="p1", platforms=["web"], status="completed",
            total_cases=5, passed_count=5, failed_count=0)
        defect_repo_mock.get_by_run.return_value = []
        report = await service.get_run_report("run_001", "full")
        assert "steps" in report

    async def test_not_found(self, service, run_repo_mock, defect_repo_mock):
        run_repo_mock.get_by_id.return_value = None
        report = await service.get_run_report("run_nonexist")
        assert "error" in report

    async def test_executive_summary(self, service, run_repo_mock, defect_repo_mock):
        run_repo_mock.get_by_id.return_value = RunRecord(
            id="run_001", project_id="p1", platforms=["web"], status="completed",
            total_cases=5, passed_count=4, failed_count=1)
        defect_repo_mock.get_by_run.return_value = [
            Defect(id="def_001", run_id="run_001", title="Bug", severity="medium")]
        summary = await service.get_executive_summary("run_001")
        assert "run_001" in summary
        assert "80.0%" in summary or "0.8" in summary
