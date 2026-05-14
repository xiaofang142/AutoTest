from app.domain.models.scenario import TestScenario, TestCase, CoverageInfo
from app.domain.exceptions import ScenarioNotFoundError
from app.interfaces.repositories.scenario_repo import ScenarioRepository
from app.lib.id_generator import generate_id
from app.lib.logger import get_logger

logger = get_logger(__name__)


class ScenarioService:
    def __init__(self, scenario_repo: ScenarioRepository):
        self._repo = scenario_repo

    async def generate_scenarios(self, project_id: str, platforms: list[str] | None = None) -> list[TestScenario]:
        logger.info(f"Scenario generation triggered: project={project_id}")
        return []

    async def get_scenarios(self, project_id: str) -> list[TestScenario]:
        return await self._repo.get_by_project(project_id)

    async def get_scenario(self, scenario_id: str) -> TestScenario:
        scenario = await self._repo.get_by_id(scenario_id)
        if not scenario:
            raise ScenarioNotFoundError(scenario_id)
        return scenario

    async def update_scenario(self, scenario_id: str, updates: dict) -> TestScenario:
        scenario = await self.get_scenario(scenario_id)
        for key, value in updates.items():
            if hasattr(scenario, key):
                setattr(scenario, key, value)
        return await self._repo.update_scenario(scenario)
