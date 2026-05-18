from unittest.mock import AsyncMock

import pytest

from app.domain.exceptions import InvalidParameterError, ProjectNotFoundError
from app.services.project_service import ProjectService


@pytest.fixture
def repo_mock():
    repo = AsyncMock()
    repo.create = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    repo.list_projects = AsyncMock()
    return repo


@pytest.fixture
def service(repo_mock):
    return ProjectService(repo_mock)


@pytest.mark.asyncio
class TestCreateProject:
    async def test_success(self, service, repo_mock):
        repo_mock.create.return_value = AsyncMock(id="proj_test001")
        result = await service.create_project("测试项目", ["web"])
        assert result.id == "proj_test001"
        repo_mock.create.assert_called_once()

    async def test_empty_name(self, service):
        with pytest.raises(InvalidParameterError):
            await service.create_project("", ["web"])

    async def test_no_platform(self, service):
        with pytest.raises(InvalidParameterError):
            await service.create_project("test", [])

    async def test_invalid_platform(self, service):
        with pytest.raises(InvalidParameterError):
            await service.create_project("test", ["web", "blackberry"])

    @pytest.mark.parametrize("platforms", [["web"], ["android"], ["ios"], ["web", "android"]])
    async def test_valid_platforms(self, service, repo_mock, platforms):
        repo_mock.create.return_value = AsyncMock(id="proj_test")
        result = await service.create_project("test", platforms)
        assert result is not None


@pytest.mark.asyncio
class TestGetProject:
    async def test_found(self, service, repo_mock):
        repo_mock.get_by_id.return_value = AsyncMock(id="proj_001")
        result = await service.get_project("proj_001")
        assert result.id == "proj_001"

    async def test_not_found(self, service, repo_mock):
        repo_mock.get_by_id.return_value = None
        with pytest.raises(ProjectNotFoundError):
            await service.get_project("proj_nonexist")


@pytest.mark.asyncio
class TestDeleteProject:
    async def test_success(self, service, repo_mock):
        repo_mock.get_by_id.return_value = AsyncMock(id="proj_001", status="created")
        await service.delete_project("proj_001")
        repo_mock.delete.assert_called_once_with("proj_001")

    async def test_running_project(self, service, repo_mock):
        repo_mock.get_by_id.return_value = AsyncMock(id="proj_001", status="running")
        from app.domain.exceptions import OperationNotAllowedError
        with pytest.raises(OperationNotAllowedError):
            await service.delete_project("proj_001")
