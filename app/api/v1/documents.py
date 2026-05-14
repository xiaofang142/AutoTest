from fastapi import APIRouter, HTTPException

from app.domain.exceptions import DocumentNotFoundError, InvalidParameterError
from app.services.document_service import DocumentService

router = APIRouter(tags=["documents"])


def _get_service() -> DocumentService:
    from app.dependencies import get_document_service
    return get_document_service()


@router.post("/projects/{project_id}/documents")
async def add_document(project_id: str, body: dict):
    service = _get_service()
    try:
        doc = await service.add_document(
            project_id=project_id,
            url=body.get("url", ""),
            doc_type=body.get("type", "prd"),
            description=body.get("description", ""),
        )
        return {"code": 0, "data": doc.model_dump(mode="json")}
    except InvalidParameterError as e:
        raise HTTPException(422, str(e))


@router.get("/projects/{project_id}/documents")
async def list_documents(project_id: str):
    service = _get_service()
    docs = await service.get_project_documents(project_id)
    return {"code": 0, "data": {"items": [d.model_dump(mode="json") for d in docs]}}


@router.post("/projects/{project_id}/documents/parse")
async def parse_documents(project_id: str, body: dict | None = None):
    service = _get_service()
    doc_ids = (body or {}).get("document_ids", [])
    parsed = []
    for did in doc_ids:
        try:
            doc = await service.parse_document(did)
            parsed.append(doc)
        except DocumentNotFoundError:
            continue
    return {
        "code": 0,
        "data": {
            "task_id": f"parse_task_{project_id}",
            "status": "processing",
            "documents": [d.model_dump(mode="json") for d in parsed],
        },
    }
