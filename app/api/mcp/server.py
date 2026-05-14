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
