from fastapi import APIRouter, HTTPException

from app.domain.exceptions import RunNotFoundError, InvalidParameterError
from app.services.run_service import RunService

router = APIRouter(tags=["runs"])


def _get_service() -> RunService:
    from app.dependencies import get_run_service
    return get_run_service()


@router.post("/projects/{project_id}/runs")
async def create_run(project_id: str, body: dict):
    service = _get_service()
    try:
        run = await service.create_run(
            project_id=project_id,
            platforms=body.get("platforms", ["web"]),
            scenario_ids=body.get("scenario_ids"),
        )
        return {"code": 0, "data": run.model_dump(mode="json")}
    except InvalidParameterError as e:
        raise HTTPException(422, str(e))


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    service = _get_service()
    try:
        run = await service.get_run(run_id)
        return {"code": 0, "data": run.model_dump(mode="json")}
    except RunNotFoundError as e:
        raise HTTPException(404, str(e))


@router.get("/runs/{run_id}/progress")
async def get_run_progress(run_id: str):
    service = _get_service()
    try:
        progress = await service.get_run_progress(run_id)
        return {"code": 0, "data": progress}
    except RunNotFoundError as e:
        raise HTTPException(404, str(e))


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    service = _get_service()
    try:
        await service.cancel_run(run_id)
        return {"code": 0, "data": {"run_id": run_id, "status": "cancelled"}}
    except RunNotFoundError as e:
        raise HTTPException(404, str(e))


@router.post("/runs/{run_id}/retry")
async def retry_run(run_id: str, body: dict | None = None):
    service = _get_service()
    try:
        new_run = await service.retry_run(run_id, (body or {}).get("case_ids"))
        return {"code": 0, "data": new_run.model_dump(mode="json")}
    except RunNotFoundError as e:
        raise HTTPException(404, str(e))
