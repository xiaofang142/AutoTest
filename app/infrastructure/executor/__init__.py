import warnings
from typing import Optional
from app.interfaces.executor_client import ExecutorClient
from app.infrastructure.executor.mock_executor_client import MockExecutorClient
from app.config import settings


class ExecutorFactory:
    @staticmethod
    def create(platform: str = "web", mode: Optional[str] = None) -> ExecutorClient:
        mode = mode or settings.executor_mode
        if mode == "mock":
            return MockExecutorClient()
        if platform == "web":
            from app.infrastructure.executor.web_executor_client import WebExecutorClient
            return WebExecutorClient(base_url=settings.executor_web_url)
        raise ValueError(f"Unsupported platform: {platform}")

    @staticmethod
    async def health_check(platform: str = "web") -> bool:
        client = ExecutorFactory.create(platform=platform, mode="real")
        try:
            return await client.ping()
        except Exception:
            return False


def create_executor_client() -> ExecutorClient:
    """@deprecated: Use ExecutorFactory.create() instead"""
    warnings.warn(
        "create_executor_client() is deprecated, use ExecutorFactory.create()",
        DeprecationWarning,
        stacklevel=2,
    )
    return ExecutorFactory.create()
