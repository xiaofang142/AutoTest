from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.scenario import TestCase, TestScenario, TestStep
from app.infrastructure.persistence.models import ScenarioModel, TestCaseModel
from app.interfaces.repositories.scenario_repo import ScenarioRepository
from app.lib.logger import get_logger

logger = get_logger(__name__)


class SqlScenarioRepository(ScenarioRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_scenario(self, scenario: TestScenario) -> TestScenario:
        model = ScenarioModel(
            id=scenario.id, project_id=scenario.project_id,
            business_line=scenario.business_line, name=scenario.name,
            description=scenario.description, type=scenario.type,
            role=scenario.role, status=scenario.status,
            coverage=scenario.coverage.model_dump() if hasattr(scenario.coverage, "model_dump") else {},
        )
        self._session.add(model)
        await self._session.commit()
        return scenario

    async def get_by_project(self, project_id: str) -> list[TestScenario]:
        result = await self._session.execute(
            select(ScenarioModel).where(ScenarioModel.project_id == project_id)
        )
        models = result.scalars().all()
        return [TestScenario(id=m.id, project_id=m.project_id, name=m.name,
                             type=m.type, role=m.role or "", status=m.status,
                             business_line=m.business_line or "")
                for m in models]

    async def get_by_id(self, scenario_id: str) -> TestScenario | None:
        model = await self._session.get(ScenarioModel, scenario_id)
        if not model:
            return None
        return TestScenario(id=model.id, project_id=model.project_id, name=model.name,
                            type=model.type, description=model.description or "",
                            status=model.status, business_line=model.business_line or "")

    async def update_scenario(self, scenario: TestScenario) -> TestScenario:
        model = await self._session.get(ScenarioModel, scenario.id)
        if model:
            model.name = scenario.name
            model.status = scenario.status
            await self._session.commit()
        return scenario

    async def create_case(self, case: TestCase) -> TestCase:
        model = TestCaseModel(
            id=case.id, scenario_id=case.scenario_id, project_id=case.project_id,
            name=case.name, description=case.description,
            steps=[s.model_dump() for s in case.steps],
        )
        self._session.add(model)
        await self._session.commit()
        return case

    async def get_case(self, case_id: str) -> TestCase | None:
        model = await self._session.get(TestCaseModel, case_id)
        if not model:
            return None
        steps = [TestStep(**s) for s in (model.steps or [])]
        return TestCase(id=model.id, name=model.name, steps=steps)
