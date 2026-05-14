import pytest
import os
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def executor_url() -> str:
    """Executor service URL (can be overridden via env var)"""
    return os.environ.get("EXECUTOR_TEST_URL", "http://localhost:3100")
