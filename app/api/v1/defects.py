from fastapi import APIRouter, HTTPException

from app.services.report_service import ReportService

router = APIRouter(tags=["defects"])


def _get_report_service() -> ReportService:
    from app.dependencies import get_report_service
    return get_report_service()


@router.get("/runs/{run_id}/defects")
async def list_defects(run_id: str, severity: str | None = None):
    service = _get_report_service()
    report = await service.get_run_report(run_id)
    return {"code": 0, "data": {"items": report.get("defects", []), "total": report.get("defect_count", 0)}}


@router.get("/defects/{defect_id}")
async def get_defect(defect_id: str):
    from app.interfaces.repositories.defect_repo import DefectRepository

    repo: DefectRepository = _get_defect_repo()
    defect = await repo.get_by_id(defect_id)
    if not defect:
        raise HTTPException(404, f"Defect not found: {defect_id}")
    return {"code": 0, "data": defect.model_dump(mode="json")}


@router.get("/defects/{defect_id}/evidence")
async def get_evidence(defect_id: str, format: str = "full"):
    from app.interfaces.repositories.defect_repo import DefectRepository

    repo: DefectRepository = _get_defect_repo()
    defect = await repo.get_by_id(defect_id)
    if not defect:
        raise HTTPException(404, f"Defect not found: {defect_id}")

    evidence = {
        "step_context": defect.step_context,
        "screenshots": defect.screenshots if format == "full" else {},
        "console_logs": defect.console_logs,
        "api_calls": defect.api_calls,
        "page_state": defect.page_state,
        "evidence_chains": [c.model_dump(mode="json") for c in defect.evidence_chains],
    }
    return {"code": 0, "data": evidence}


def _get_defect_repo():
    from app.dependencies import get_analyzer
    return get_analyzer()._defect_repo
