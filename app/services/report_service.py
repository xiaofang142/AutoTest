from app.interfaces.repositories.defect_repo import DefectRepository
from app.interfaces.repositories.run_repo import RunRepository
from app.lib.logger import get_logger

logger = get_logger(__name__)


class ReportService:
    def __init__(self, run_repo: RunRepository, defect_repo: DefectRepository):
        self._run_repo = run_repo
        self._defect_repo = defect_repo

    async def get_run_report(self, run_id: str, format: str = "summary") -> dict:
        run = await self._run_repo.get_by_id(run_id)
        defects = await self._defect_repo.get_by_run(run_id)

        if not run:
            return {"error": f"Run {run_id} not found"}

        base = {
            "run_id": run.id,
            "project_id": run.project_id,
            "status": run.status,
            "total_cases": run.total_cases,
            "passed": run.passed_count,
            "failed": run.failed_count,
            "uncertain": run.uncertain_count,
            "pass_rate": (run.passed_count / run.total_cases) if run.total_cases else 0,
            "defect_count": len(defects),
            "defects": [{"id": d.id, "severity": d.severity, "title": d.title} for d in defects],
            "created_at": run.created_at.isoformat() if run.created_at else "",
        }

        if format == "summary":
            return base
        elif format == "full":
            base["steps"] = []
            return base
        return base

    async def get_executive_summary(self, run_id: str) -> str:
        report = await self.get_run_report(run_id)
        return (
            f"## Run {report['run_id']}\n"
            f"- Status: {report['status']}\n"
            f"- Pass rate: {report['pass_rate']:.1%}\n"
            f"- Defects: {report['defect_count']}"
        )
