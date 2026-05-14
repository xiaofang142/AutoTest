import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
class TestHealthAPI:
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"


@pytest.mark.asyncio
class TestProjectAPI:
    async def test_create_project(self, client):
        resp = await client.post("/api/v1/projects", json={
            "name": "集成测试项目",
            "platforms": ["web"],
            "entries": [{"platform": "web", "url": "https://example.com"}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "project" in data["data"]

    async def test_create_project_empty_name(self, client):
        resp = await client.post("/api/v1/projects", json={
            "name": "", "platforms": ["web"],
            "entries": [{"platform": "web", "url": "https://example.com"}],
        })
        assert resp.status_code == 422

    async def test_list_projects(self, client):
        resp = await client.get("/api/v1/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data["data"]

    async def test_get_project_not_found(self, client):
        resp = await client.get("/api/v1/projects/proj_nonexist")
        assert resp.status_code == 404

    async def test_full_crud(self, client):
        create_resp = await client.post("/api/v1/projects", json={
            "name": "CRUD测试", "platforms": ["web"],
            "entries": [{"platform": "web", "url": "https://example.com"}],
        })
        pid = create_resp.json()["data"]["project"]["id"]

        get_resp = await client.get(f"/api/v1/projects/{pid}")
        assert get_resp.status_code == 200

        put_resp = await client.put(f"/api/v1/projects/{pid}", json={"name": "CRUD测试-已更新"})
        assert put_resp.status_code == 200

        del_resp = await client.delete(f"/api/v1/projects/{pid}")
        assert del_resp.status_code == 204


@pytest.mark.asyncio
class TestDocumentAPI:
    async def test_add_document(self, client):
        create_resp = await client.post("/api/v1/projects", json={
            "name": "文档测试", "platforms": ["web"],
            "entries": [{"platform": "web", "url": "https://example.com"}],
        })
        pid = create_resp.json()["data"]["project"]["id"]

        resp = await client.post(f"/api/v1/projects/{pid}/documents", json={
            "url": "https://example.com/prd.md", "type": "prd",
        })
        assert resp.status_code == 200

    async def test_list_documents(self, client):
        create_resp = await client.post("/api/v1/projects", json={
            "name": "文档列表测试", "platforms": ["web"],
            "entries": [{"platform": "web", "url": "https://example.com"}],
        })
        pid = create_resp.json()["data"]["project"]["id"]

        resp = await client.get(f"/api/v1/projects/{pid}/documents")
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestRunAPI:
    async def test_create_run(self, client):
        create_resp = await client.post("/api/v1/projects", json={
            "name": "执行测试", "platforms": ["web"],
            "entries": [{"platform": "web", "url": "https://example.com"}],
        })
        pid = create_resp.json()["data"]["project"]["id"]

        resp = await client.post(f"/api/v1/projects/{pid}/runs", json={
            "platforms": ["web"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["status"] == "queued"

    async def test_run_progress(self, client):
        create_resp = await client.post("/api/v1/projects", json={
            "name": "进度测试", "platforms": ["web"],
            "entries": [{"platform": "web", "url": "https://example.com"}],
        })
        pid = create_resp.json()["data"]["project"]["id"]
        run_resp = await client.post(f"/api/v1/projects/{pid}/runs", json={"platforms": ["web"]})
        rid = run_resp.json()["data"]["id"]

        progress_resp = await client.get(f"/api/v1/runs/{rid}/progress")
        assert progress_resp.status_code == 200

    async def test_cancel_run(self, client):
        create_resp = await client.post("/api/v1/projects", json={
            "name": "取消测试", "platforms": ["web"],
            "entries": [{"platform": "web", "url": "https://example.com"}],
        })
        pid = create_resp.json()["data"]["project"]["id"]
        run_resp = await client.post(f"/api/v1/projects/{pid}/runs", json={"platforms": ["web"]})
        rid = run_resp.json()["data"]["id"]

        cancel_resp = await client.post(f"/api/v1/runs/{rid}/cancel")
        assert cancel_resp.status_code == 200
