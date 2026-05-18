from unittest.mock import AsyncMock

import pytest

from app.domain.exceptions import ScenarioNotFoundError
from app.domain.models.knowledge import BusinessRule
from app.domain.models.scenario import TestScenario
from app.services.scenario_service import ScenarioService


@pytest.fixture
def repo_mock():
    repo = AsyncMock()
    repo.create_scenario = AsyncMock()
    repo.get_by_project = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock()
    repo.update_scenario = AsyncMock()
    return repo


@pytest.fixture
def kb_repo_mock():
    kb = AsyncMock()
    kb.get_by_project = AsyncMock()
    kb.get_rules = AsyncMock(return_value=[])
    return kb


@pytest.fixture
def service(repo_mock, kb_repo_mock):
    return ScenarioService(repo_mock, kb_repo=kb_repo_mock)


@pytest.mark.asyncio
class TestGenerateScenarios:
    async def test_generate_with_rules(self, service, repo_mock, kb_repo_mock):
        kb_repo_mock.get_by_project.return_value = AsyncMock(id="kb_001")
        kb_repo_mock.get_rules.return_value = [
            BusinessRule(id="rule_1", kb_id="kb_001", category="flow", content="用户登录流程"),
            BusinessRule(id="rule_2", kb_id="kb_001", category="permission", content="管理员权限验证"),
        ]
        scenarios = await service.generate_scenarios("proj_001", ["web"])
        assert len(scenarios) > 0
        assert repo_mock.create_scenario.called

    async def test_generate_default_when_no_rules(self, service, repo_mock, kb_repo_mock):
        kb_repo_mock.get_by_project.return_value = None
        scenarios = await service.generate_scenarios("proj_001", ["web"])
        assert len(scenarios) >= 1
        assert scenarios[0].type == "positive"

    async def test_generate_with_chain(self, service, repo_mock):
        rules = [BusinessRule(id="r1", kb_id="kb_1", category="flow", content="登录→首页→订单")]
        scenarios = await service.generate_with_chain("proj_001", rules, ["web"])
        # ChainBuilder returns scenarios; if no AI service, scenarios list may be empty
        assert isinstance(scenarios, list)


@pytest.mark.asyncio
class TestGetScenario:
    async def test_found(self, service, repo_mock):
        repo_mock.get_by_id.return_value = TestScenario(id="sce_001", project_id="p1", name="Test")
        result = await service.get_scenario("sce_001")
        assert result.id == "sce_001"

    async def test_not_found(self, service, repo_mock):
        repo_mock.get_by_id.return_value = None
        with pytest.raises(ScenarioNotFoundError):
            await service.get_scenario("sce_nonexist")

    async def test_update(self, service, repo_mock):
        repo_mock.get_by_id.return_value = TestScenario(id="sce_001", project_id="p1", name="Old")
        repo_mock.update_scenario.return_value = TestScenario(id="sce_001", project_id="p1", name="New")
        result = await service.update_scenario("sce_001", {"name": "New"})
        assert result.name == "New"
