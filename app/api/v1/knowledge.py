from fastapi import APIRouter, HTTPException

from app.domain.exceptions import KnowledgeBaseNotFoundError
from app.services.knowledge_service import KnowledgeService

router = APIRouter(tags=["knowledge"])


def _get_service() -> KnowledgeService:
    from app.dependencies import get_knowledge_service
    return get_knowledge_service()


@router.get("/projects/{project_id}/knowledge")
async def get_knowledge(project_id: str):
    service = _get_service()
    try:
        kb = await service.get_knowledge_base(project_id)
        return {"code": 0, "data": kb.model_dump(mode="json")}
    except KnowledgeBaseNotFoundError:
        return {"code": 0, "data": None}


@router.get("/projects/{project_id}/knowledge/rules")
async def get_rules(project_id: str, category: str | None = None):
    service = _get_service()
    try:
        kb = await service.get_knowledge_base(project_id)
        rules = await service.get_rules(kb.id, category)
        return {"code": 0, "data": {"items": [r.model_dump(mode="json") for r in rules]}}
    except KnowledgeBaseNotFoundError:
        return {"code": 0, "data": {"items": []}}


@router.put("/projects/{project_id}/knowledge/rules/{rule_id}")
async def update_rule(project_id: str, rule_id: str, body: dict):
    service = _get_service()
    rule = await service.update_rule(rule_id, body.get("content", ""), body.get("status", "confirmed"))
    return {"code": 0, "data": rule.model_dump(mode="json")}

@router.get("/projects/{project_id}/knowledge/versions")
async def get_kb_versions(project_id: str):
    return {"code": 0, "data": {"versions": [], "current_version": 1}}

@router.post("/projects/{project_id}/knowledge/conflicts/{conflict_id}/resolve")
async def resolve_conflict(project_id: str, conflict_id: str, body: dict):
    service = _get_service()
    conflict = await service.resolve_conflict(conflict_id, body.get("resolution", ""))
    return {"code": 0, "data": {"conflict_id": conflict_id, "status": "resolved"}}

@router.post("/projects/{project_id}/knowledge/verify")
async def verify_knowledge(project_id: str, body: dict):
    return {"code": 0, "data": {"status": "verified", "confirmed_rules": len(body.get("confirmed_rules", []))}}
