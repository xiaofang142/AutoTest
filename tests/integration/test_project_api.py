import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def sync_client():
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    return client


@pytest.mark.asyncio
class TestHealthAPI:
    async def test_health(self, sync_client):
        async with sync_client as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"

    async def test_version(self, sync_client):
        async with sync_client as client:
            resp = await client.get("/health")
            assert resp.json()["version"] == "0.1.0"


@pytest.mark.asyncio
class TestProjectAPI:
    async def test_create(self, sync_client):
        async with sync_client as client:
            resp = await client.post("/api/v1/projects", json={
                "name": "测试项目", "platforms": ["web"],
                "entries": [{"platform": "web", "url": "https://example.com"}],
            })
            assert resp.status_code == 200
            assert resp.json()["code"] == 0
            assert "project" in resp.json()["data"]

    async def test_create_empty_name_fails(self, sync_client):
        async with sync_client as client:
            resp = await client.post("/api/v1/projects", json={"name": "", "platforms": ["web"]})
            assert resp.status_code == 422

    async def test_list(self, sync_client):
        async with sync_client as client:
            resp = await client.get("/api/v1/projects")
            assert resp.status_code == 200
            assert "items" in resp.json()["data"]

    async def test_get_not_found(self, sync_client):
        async with sync_client as client:
            resp = await client.get("/api/v1/projects/proj_nonexist")
            assert resp.status_code == 404

    async def test_crud_cycle(self, sync_client):
        async with sync_client as client:
            create = await client.post("/api/v1/projects", json={
                "name": "CRUD", "platforms": ["web"],
                "entries": [{"platform": "web", "url": "https://x.com"}],
            })
            pid = create.json()["data"]["project"]["id"]
            get = await client.get(f"/api/v1/projects/{pid}")
            assert get.status_code == 200
            put = await client.put(f"/api/v1/projects/{pid}", json={"name": "已更新"})
            assert put.status_code == 200
            d = await client.delete(f"/api/v1/projects/{pid}")
            assert d.status_code == 204


@pytest.mark.asyncio
class TestDocumentAPI:
    async def test_add(self, sync_client):
        async with sync_client as client:
            proj = await client.post("/api/v1/projects", json={
                "name": "文档", "platforms": ["web"],
                "entries": [{"platform": "web", "url": "https://x.com"}],
            })
            pid = proj.json()["data"]["project"]["id"]
            resp = await client.post(f"/api/v1/projects/{pid}/documents", json={
                "url": "https://example.com/prd.md", "type": "prd",
            })
            assert resp.status_code == 200

    async def test_list(self, sync_client):
        async with sync_client as client:
            proj = await client.post("/api/v1/projects", json={
                "name": "文档列表", "platforms": ["web"],
            })
            pid = proj.json()["data"]["project"]["id"]
            resp = await client.get(f"/api/v1/projects/{pid}/documents")
            assert resp.status_code == 200


@pytest.mark.asyncio
class TestRunAPI:
    async def test_create_and_manage(self, sync_client):
        async with sync_client as client:
            proj = await client.post("/api/v1/projects", json={
                "name": "执行测试", "platforms": ["web"],
            })
            pid = proj.json()["data"]["project"]["id"]
            create = await client.post(f"/api/v1/projects/{pid}/runs", json={"platforms": ["web"]})
            assert create.status_code == 200
            rid = create.json()["data"]["id"]
            progress = await client.get(f"/api/v1/runs/{rid}/progress")
            assert progress.status_code == 200
            cancel = await client.post(f"/api/v1/runs/{rid}/cancel")
            assert cancel.status_code == 200
