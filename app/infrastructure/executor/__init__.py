from app.infrastructure.executor.web_executor_client import WebExecutorClient
from app.infrastructure.executor.mock_executor_client import MockExecutorClient


def create_executor_client():
    from app.config import settings
    if settings.executor_mode == "mock":
        return MockExecutorClient()
    return WebExecutorClient()
