import pytest
from app.domain.models.project import Project, PlatformEntry
from app.services.document_service import DocumentService
from app.services.scenario_service import ScenarioService
from app.services.knowledge_service import KnowledgeService
from tests.mock_repos import MemProjectRepo, MemDocRepo, MemKBRepo, MemScenarioRepo


@pytest.fixture
def project_repo():
    return MemProjectRepo()


@pytest.fixture
def doc_repo():
    return MemDocRepo()


@pytest.fixture
def kb_repo():
    return MemKBRepo()


@pytest.fixture
def scenario_repo():
    return MemScenarioRepo()


@pytest.fixture
async def sample_project(project_repo):
    p = Project(name="test", platforms=["web"],
                entries=[PlatformEntry(platform="web", url="https://x.com")])
    return await project_repo.create(p)


class TestDocFlow:
    @pytest.mark.asyncio
    async def test_create_project(self, project_repo):
        p = Project(name="test", platforms=["web"],
                    entries=[PlatformEntry(platform="web", url="https://x.com")])
        c = await project_repo.create(p)
        assert c.id is not None

    @pytest.mark.asyncio
    async def test_add_document(self, sample_project, doc_repo, kb_repo):
        svc = DocumentService(doc_repo, kb_repo=kb_repo)
        doc = await svc.add_document(sample_project.id, "https://prd.x.com", "prd")
        assert doc.id is not None

    @pytest.mark.asyncio
    async def test_knowledge(self, sample_project, kb_repo):
        kbs = KnowledgeService(kb_repo)
        kb = await kbs.create_knowledge_base(sample_project.id)
        assert kb is not None
        assert kb.project_id == sample_project.id

    @pytest.mark.asyncio
    async def test_scenarios(self, sample_project, kb_repo, scenario_repo):
        svc = ScenarioService(scenario_repo, kb_repo=kb_repo)
        scs = await svc.generate_scenarios(sample_project.id, platforms=["web"])
        for s in scs:
            assert s.project_id == sample_project.id
            for case in s.cases:
                for step in case.steps:
                    assert step.action
