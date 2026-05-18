from unittest.mock import AsyncMock, patch

import pytest

from app.domain.exceptions import DocumentNotFoundError, DocumentParseError, InvalidParameterError
from app.domain.models.document import Document
from app.services.document_service import DocumentService


@pytest.fixture
def repo_mock():
    repo = AsyncMock()
    repo.create = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_project = AsyncMock(return_value=[])
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def service(repo_mock):
    return DocumentService(repo_mock)


@pytest.mark.asyncio
class TestAddDocument:
    async def test_success(self, service, repo_mock):
        repo_mock.create.return_value = Document(id="doc_001", project_id="p1", url="https://example.com/prd.md")
        result = await service.add_document("p1", "https://example.com/prd.md", "prd")
        assert result.id == "doc_001"
        assert result.type == "prd"

    async def test_empty_url(self, service):
        with pytest.raises(InvalidParameterError):
            await service.add_document("p1", "", "prd")


@pytest.mark.asyncio
class TestGetDocument:
    async def test_found(self, service, repo_mock):
        repo_mock.get_by_id.return_value = Document(id="doc_001", project_id="p1", url="https://x.md")
        result = await service.get_document("doc_001")
        assert result.id == "doc_001"

    async def test_not_found(self, service, repo_mock):
        repo_mock.get_by_id.return_value = None
        with pytest.raises(DocumentNotFoundError):
            await service.get_document("doc_nonexist")


@pytest.mark.asyncio
class TestParseDocument:
    async def test_parse_success(self, service, repo_mock):
        repo_mock.get_by_id.return_value = Document(id="doc_001", project_id="p1", url="https://example.com/doc.md")
        with patch.object(service, '_fetch_content', return_value="# Test Doc\n\n登录流程:\n1. 用户输入账号密码\n2. 点击登录"):
            result = await service.parse_document("doc_001")
            assert result.status == "completed"

    async def test_parse_fetch_fails(self, service, repo_mock):
        repo_mock.get_by_id.return_value = Document(id="doc_001", project_id="p1", url="https://invalid.url")
        with patch.object(service, '_fetch_content', return_value=""):
            with pytest.raises(DocumentParseError):
                await service.parse_document("doc_001")

    async def test_get_project_documents(self, service, repo_mock):
        repo_mock.get_by_project.return_value = [Document(id="d1", project_id="p1", url="https://x.md")]
        docs = await service.get_project_documents("p1")
        assert len(docs) == 1
