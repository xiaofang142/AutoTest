from fastapi import APIRouter, HTTPException

from app.domain.exceptions import ScenarioNotFoundError
from app.services.scenario_service import ScenarioService

router = APIRouter(tags=["scenarios"])


def _get_service() -> ScenarioService:
    from app.dependencies import get_scenario_service
    return get_scenario_service()


@router.post("/projects/{project_id}/scenarios/generate")
async def generate_scenarios(project_id: str, body: dict | None = None):
    service = _get_service()
    platforms = (body or {}).get("platforms", ["web"])
    scenarios = await service.generate_scenarios(project_id, platforms)
    return {
        "code": 0,
        "data": {
            "task_id": f"scenario_gen_{project_id}",
            "status": "completed",
            "count": len(scenarios),
        },
    }


@router.get("/projects/{project_id}/scenarios")
async def list_scenarios(project_id: str):
    service = _get_service()
    scenarios = await service.get_scenarios(project_id)
    return {
        "code": 0,
        "data": {
            "items": [s.model_dump(mode="json") for s in scenarios],
            "total": len(scenarios),
        },
    }


@router.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str):
    service = _get_service()
    try:
        scenario = await service.get_scenario(scenario_id)
        return {"code": 0, "data": scenario.model_dump(mode="json")}
    except ScenarioNotFoundError as e:
        raise HTTPException(404, str(e))


@router.put("/scenarios/{scenario_id}")
async def update_scenario(scenario_id: str, body: dict):
    service = _get_service()
    try:
        scenario = await service.update_scenario(scenario_id, body)
        return {"code": 0, "data": scenario.model_dump(mode="json")}
    except ScenarioNotFoundError as e:
        raise HTTPException(404, str(e))
