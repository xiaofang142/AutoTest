from fastapi import APIRouter, HTTPException

from app.domain.exceptions import (
    InvalidParameterError,
    OperationNotAllowedError,
    ProjectNotFoundError,
)
from app.services.project_service import ProjectService

router = APIRouter(tags=["projects"])


def _get_service() -> ProjectService:
    from app.dependencies import get_project_service
    return get_project_service()


@router.post("/projects")
async def create_project(body: dict):
    service = _get_service()
    try:
        project = await service.create_project(
            name=body.get("name", ""),
            platforms=body.get("platforms", ["web"]),
            entries=body.get("entries"),
            docs=body.get("document_refs"),
        )
        return {"code": 0, "data": {"project": project.model_dump(mode="json")}}
    except InvalidParameterError as e:
        raise HTTPException(422, str(e))


@router.get("/projects")
async def list_projects(status: str | None = None):
    service = _get_service()
    projects = await service.list_projects(status)
    return {
        "code": 0,
        "data": {
            "items": [p.model_dump(mode="json") for p in projects],
            "total": len(projects),
        },
    }


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    service = _get_service()
    try:
        project = await service.get_project(project_id)
        return {"code": 0, "data": project.model_dump(mode="json")}
    except ProjectNotFoundError as e:
        raise HTTPException(404, str(e))


@router.put("/projects/{project_id}")
async def update_project(project_id: str, body: dict):
    service = _get_service()
    try:
        project = await service.update_project(project_id, body)
        return {"code": 0, "data": project.model_dump(mode="json")}
    except ProjectNotFoundError as e:
        raise HTTPException(404, str(e))
    except InvalidParameterError as e:
        raise HTTPException(422, str(e))


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: str):
    service = _get_service()
    try:
        await service.delete_project(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(404, str(e))
    except OperationNotAllowedError as e:
        raise HTTPException(409, str(e))
