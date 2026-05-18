from abc import ABC, abstractmethod

from app.domain.models.scenario import TestCase, TestScenario


class ScenarioRepository(ABC):
    @abstractmethod
    async def create_scenario(self, scenario: TestScenario) -> TestScenario:
        ...

    @abstractmethod
    async def get_by_project(self, project_id: str) -> list[TestScenario]:
        ...

    @abstractmethod
    async def get_by_id(self, scenario_id: str) -> TestScenario | None:
        ...

    @abstractmethod
    async def update_scenario(self, scenario: TestScenario) -> TestScenario:
        ...

    @abstractmethod
    async def create_case(self, case: TestCase) -> TestCase:
        ...

    @abstractmethod
    async def get_case(self, case_id: str) -> TestCase | None:
        ...
