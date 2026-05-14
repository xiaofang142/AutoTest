import httpx
import pytest

EXECUTOR_URL = "http://localhost:3100"


def is_executor_running() -> bool:
    try:
        r = httpx.get(f"{EXECUTOR_URL}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


executor_available = pytest.mark.skipif(
    not is_executor_running(),
    reason=f"Executor not running on {EXECUTOR_URL}",
)


@pytest.mark.integration
@pytest.mark.executor
@executor_available
class TestExecutorConnectivity:
    """Direct HTTP tests against the executor service (MCP integration)."""

    @pytest.mark.asyncio
    async def test_health(self):
        async with httpx.AsyncClient() as c:
            resp = await c.get(f"{EXECUTOR_URL}/health", timeout=10)
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_navigate(self):
        async with httpx.AsyncClient() as c:
            resp = await c.post(
                f"{EXECUTOR_URL}/agent/navigate",
                json={"url": "https://example.com"},
                timeout=30,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("success") is True
            assert "example" in data.get("url", "")

    @pytest.mark.asyncio
    async def test_create_run(self):
        async with httpx.AsyncClient() as c:
            resp = await c.post(f"{EXECUTOR_URL}/run/create", json={
                "run_id": "test_create_001",
                "entry": {"url": "https://example.com", "cases": []},
            }, timeout=10)
            assert resp.status_code == 200
            assert resp.json().get("status") == "created"

    @pytest.mark.asyncio
    async def test_start_and_poll(self):
        async with httpx.AsyncClient() as c:
            create_resp = await c.post(f"{EXECUTOR_URL}/run/create", json={
                "run_id": "test_poll_001",
                "entry": {"url": "https://example.com", "cases": []},
            }, timeout=10)
            assert create_resp.status_code == 200
            run_id = create_resp.json().get("run_id", "")

            start_resp = await c.post(
                f"{EXECUTOR_URL}/run/{run_id}/start",
                timeout=10,
            )
            assert start_resp.status_code == 200

            poll_resp = await c.get(
                f"{EXECUTOR_URL}/run/{run_id}/progress",
                timeout=10,
            )
            status = poll_resp.json().get("status", "")
            assert status in ("completed", "failed", "running", "queued", "error")


@pytest.mark.integration
@pytest.mark.executor
@executor_available
class TestWebExecutorClient:
    """Tests using the WebExecutorClient interface directly."""

    @pytest.mark.asyncio
    async def test_ping(self):
        from app.infrastructure.executor import WebExecutorClient

        client = WebExecutorClient(base_url=EXECUTOR_URL)
        result = await client.ping()
        assert result is True

    @pytest.mark.asyncio
    async def test_navigate_result(self):
        from app.infrastructure.executor import WebExecutorClient

        client = WebExecutorClient(base_url=EXECUTOR_URL)
        result = await client.navigate("https://example.com")
        assert result.success is True
