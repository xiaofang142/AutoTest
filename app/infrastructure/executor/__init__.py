from app.interfaces.executor_client import ExecutorClient
from app.infrastructure.executor.web_executor_client import WebExecutorClient
from app.config import settings


class ExecutorFactory:
    """执行器工厂 — 始终创建真实 WebExecutorClient"""

    @staticmethod
    def create(platform: str = "web") -> ExecutorClient:
        if platform == "web":
            return WebExecutorClient(base_url=settings.executor_web_url)
        raise ValueError(f"Unsupported platform: {platform}")

    @staticmethod
    async def health_check(platform: str = "web") -> bool:
        client = ExecutorFactory.create(platform=platform)
        try:
            return await client.ping()
        except Exception:
            return False
