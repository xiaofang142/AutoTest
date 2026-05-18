from unittest.mock import AsyncMock

import pytest

from app.domain.exceptions import KnowledgeBaseNotFoundError
from app.domain.models.knowledge import BusinessRule, Conflict, KnowledgeBase
from app.services.knowledge_service import KnowledgeService


@pytest.fixture
def repo_mock():
    repo = AsyncMock()
    repo.create = AsyncMock()
    repo.get_by_project = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock()
    repo.get_rules = AsyncMock(return_value=[])
    repo.create_rule = AsyncMock()
    repo.update_rule = AsyncMock()
    repo.get_conflicts = AsyncMock(return_value=[])
    repo.resolve_conflict = AsyncMock()
    return repo


@pytest.fixture
def service(repo_mock):
    return KnowledgeService(repo_mock)


@pytest.mark.asyncio
class TestKnowledgeBase:
    async def test_create(self, service, repo_mock):
        repo_mock.create.return_value = KnowledgeBase(id="kb_001", project_id="p1")
        result = await service.create_knowledge_base("p1")
        assert result.id == "kb_001"

    async def test_get_by_project_found(self, service, repo_mock):
        repo_mock.get_by_project.return_value = KnowledgeBase(id="kb_001", project_id="p1")
        result = await service.get_knowledge_base("p1")
        assert result.id == "kb_001"

    async def test_get_by_project_not_found(self, service, repo_mock):
        repo_mock.get_by_project.return_value = None
        with pytest.raises(KnowledgeBaseNotFoundError):
            await service.get_knowledge_base("p1")


@pytest.mark.asyncio
class TestRules:
    async def test_get_rules(self, service, repo_mock):
        repo_mock.get_rules.return_value = [
            BusinessRule(id="r1", kb_id="kb_001", category="flow", content="login flow", status="confirmed"),
        ]
        rules = await service.get_rules("kb_001")
        assert len(rules) == 1

    async def test_update_rule(self, service, repo_mock):
        repo_mock.update_rule.return_value = BusinessRule(id="r1", kb_id="", content="new", status="confirmed")
        result = await service.update_rule("r1", "new content", "confirmed")
        assert result.status == "confirmed"


@pytest.mark.asyncio
class TestConflicts:
    async def test_get_conflicts(self, service, repo_mock):
        repo_mock.get_conflicts.return_value = [
            Conflict(id="c1", kb_id="kb_001", description="Contradiction in rules"),
        ]
        conflicts = await service.get_conflicts("kb_001")
        assert len(conflicts) == 1

    async def test_resolve_conflict(self, service, repo_mock):
        repo_mock.resolve_conflict.return_value = Conflict(id="c1", kb_id="", status="resolved", resolution="fixed")
        result = await service.resolve_conflict("c1", "merged rules")
        assert result.status == "resolved"
