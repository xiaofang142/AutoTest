from fastapi import APIRouter

from app.services.report_service import ReportService

router = APIRouter(tags=["reports"])


def _get_service() -> ReportService:
    from app.dependencies import get_report_service
    return get_report_service()


@router.get("/runs/{run_id}/report")
async def get_report(run_id: str, format: str = "summary"):
    service = _get_service()
    report = await service.get_run_report(run_id, format)
    return {"code": 0, "data": report}


@router.get("/runs/{run_id}/report/export")
async def export_report(run_id: str, format: str = "json"):
    service = _get_service()
    report = await service.get_run_report(run_id, "full" if format == "full" else "summary")
    return {"code": 0, "data": report}
