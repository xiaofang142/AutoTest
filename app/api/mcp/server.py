from fastmcp import FastMCP

from app.domain.models.defect import Defect
from app.interfaces.repositories.defect_repo import DefectRepository

mcp = FastMCP("AutoTest MCP Server")


def _get_defect_repo():
    from app.infrastructure.persistence.defect_repo import PostgresDefectRepository
    return PostgresDefectRepository()


@mcp.tool()
async def get_defect(defect_id: str, format: str = "full") -> dict:
    """Get complete defect reference data with reproduction steps, evidence, and AI analysis.
    Use 'compact' format to exclude screenshot base64 data (lower token usage).
    """
    repo = _get_defect_repo()
    defect = await repo.get_by_id(defect_id)
    if not defect:
        return {"error": f"Defect {defect_id} not found"}

    data = defect.model_dump(mode="json")
    if format == "compact":
        data.pop("screenshots", None)
    return data


@mcp.tool()
async def list_defects(run_id: str, severity: str | None = None) -> list[dict]:
    """List all defects found in a test run. Optionally filter by severity."""
    repo = _get_defect_repo()
    defects = await repo.get_by_run(run_id, severity)
    return [
        {"id": d.id, "type": d.type, "severity": d.severity,
         "title": d.title, "created_at": d.created_at.isoformat() if d.created_at else ""}
        for d in defects
    ]


@mcp.tool()
async def create_run(project_id: str, platforms: list[str] | None = None) -> dict:
    """Create and start a test execution run."""
    from app.services.run_service import RunService
    from app.infrastructure.persistence.run_repo import PostgresRunRepository
    from app.infrastructure.persistence.scenario_repo import PostgresScenarioRepository

    repo = PostgresRunRepository()
    scenario_repo = PostgresScenarioRepository()
    service = RunService(repo, scenario_repo)
    run = await service.create_run(project_id, platforms or ["web"])
    return {"run_id": run.id, "status": run.status}


@mcp.tool()
async def get_demo_report(run_id: str, format: str = "compact") -> dict:
    """Get the full demo execution report including summary, scenarios, defects, and coverage.
    Use 'compact' format to exclude screenshot data (lower token usage).
    Use 'full' format to include all screenshots and evidence.
    """
    from app.services.report_service import ReportService
    from app.infrastructure.persistence.run_repo import PostgresRunRepository
    from app.infrastructure.persistence.defect_repo import PostgresDefectRepository
    from app.infrastructure.persistence.scenario_repo import PostgresScenarioRepository

    run_repo = PostgresRunRepository()
    defect_repo = PostgresDefectRepository()
    scenario_repo = PostgresScenarioRepository()
    service = ReportService(run_repo, defect_repo, scenario_repo)
    report = await service.get_run_report(run_id)

    if format == "compact":
        for d in report.get("defects", []):
            d.pop("screenshots", None)

    return report


@mcp.tool()
async def get_defect_summary(defect_id: str) -> dict:
    """Get a concise defect summary with root cause and fix suggestion (no screenshots)."""
    repo = _get_defect_repo()
    defect = await repo.get_by_id(defect_id)
    if not defect:
        return {"error": f"Defect {defect_id} not found"}

    return {
        "id": defect.id,
        "severity": defect.severity,
        "title": defect.title,
        "root_cause": defect.ai_analysis.get("root_cause", "") if defect.ai_analysis else "",
        "fix_suggestion": defect.fix_suggestion.description if defect.fix_suggestion else "",
        "evidence_summary": defect.synthesis.summary if defect.synthesis else "",
        "created_at": defect.created_at.isoformat() if defect.created_at else "",
    }


@mcp.tool()
async def get_run_health(run_id: str) -> dict:
    """Get the health status and quality metrics of a test run."""
    from app.infrastructure.persistence.run_repo import PostgresRunRepository
    repo = PostgresRunRepository()
    run = await repo.get_by_id(run_id)
    if not run:
        return {"error": f"Run {run_id} not found"}

    passed = run.summary.passed if run.summary else 0
    total = run.summary.total_cases if run.summary else 0
    pass_rate = round(passed / total * 100, 1) if total > 0 else 0

    return {
        "run_id": run.id,
        "status": run.status,
        "pass_rate": pass_rate,
        "total_cases": total,
        "passed": passed,
        "failed": run.summary.failed if run.summary else 0,
        "progress": run.progress.get("percent", 0) if run.progress else 0,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }
