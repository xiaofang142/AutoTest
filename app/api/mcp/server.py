"""MCP server providing AI-agent-consumable tools for defect and run data.

Uses dependency injection from app.dependencies for consistent data access
across in-memory and SQLite modes.
"""
from fastmcp import FastMCP

mcp = FastMCP("AutoTest MCP Server")


def _get_defect_repo():
    from app.dependencies import get_analyzer
    return get_analyzer()._defect_repo


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
    from app.dependencies import get_run_service
    service = get_run_service()
    run = await service.create_run(project_id, platforms or ["web"])
    return {"run_id": run.id, "status": run.status}


@mcp.tool()
async def get_demo_report(run_id: str, format: str = "compact") -> dict:
    """Get the full demo execution report including summary, scenarios, defects, and coverage.
    Use 'compact' to exclude screenshot data (lower token usage).
    Use 'full' to include all screenshots and evidence.
    """
    from app.dependencies import get_report_service
    service = get_report_service()
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


def _get_task_repo():
    from app.dependencies import get_task_repo
    return get_task_repo()


@mcp.tool()
async def get_task(task_id: str) -> dict:
    """Get full task details by ID."""
    repo = _get_task_repo()
    task = await repo.get_by_id(task_id)
    if not task:
        return {"error": f"Task {task_id} not found"}
    return task.model_dump(mode="json")


@mcp.tool()
async def list_task_defects(task_id: str, severity: str = "") -> list[dict]:
    """List defects from a task's delivery. Optionally filter by severity."""
    repo = _get_task_repo()
    task = await repo.get_by_id(task_id)
    if not task:
        return [{"error": f"Task {task_id} not found"}]
    if not task.delivery:
        return []

    defects = []
    if task.delivery.tester_view and task.delivery.tester_view.defect_list:
        defects.extend(task.delivery.tester_view.defect_list)
    if task.delivery.developer_view and task.delivery.developer_view.defect_details:
        defects.extend(task.delivery.developer_view.defect_details)

    if severity:
        defects = [d for d in defects if d.get("severity", "").lower() == severity.lower()]
    return defects


@mcp.tool()
async def get_repair_context(defect_id: str) -> dict:
    """Get compact repair context for a defect: title, root cause, fix suggestion, evidence summary."""
    repo = _get_defect_repo()
    defect = await repo.get_by_id(defect_id)
    if not defect:
        return {"error": f"Defect {defect_id} not found"}

    return {
        "id": defect.id,
        "title": defect.title,
        "severity": defect.severity,
        "root_cause": defect.ai_analysis.get("root_cause", "") if defect.ai_analysis else "",
        "fix_suggestion": defect.fix_suggestion.description if defect.fix_suggestion else "",
        "evidence_summary": defect.synthesis.summary if defect.synthesis else "",
    }


@mcp.tool()
async def get_task_delivery(task_id: str) -> dict:
    """Get the delivery package for a completed task."""
    repo = _get_task_repo()
    task = await repo.get_by_id(task_id)
    if not task:
        return {"error": f"Task {task_id} not found"}
    if not task.delivery:
        return {"error": "Delivery not ready"}
    return task.delivery.model_dump(mode="json")


@mcp.tool()
async def get_run_health(run_id: str) -> dict:
    """Get the health status and quality metrics of a test run."""
    from app.dependencies import get_run_service
    try:
        run = await get_run_service().get_run(run_id)
    except Exception:
        return {"error": f"Run {run_id} not found"}

    total = run.total_cases or 0
    passed = run.passed_count or 0
    pass_rate = round(passed / total * 100, 1) if total > 0 else 0

    return {
        "run_id": run.id,
        "status": run.status,
        "pass_rate": pass_rate,
        "total_cases": total,
        "passed": passed,
        "failed": run.failed_count or 0,
        "progress": run.progress.get("percent", 0) if run.progress else 0,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }
