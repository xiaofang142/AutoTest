"""Executor factory — creates WebExecutorClient for real browser execution."""
import asyncio
import os

import httpx

from app.config import settings
from app.interfaces.executor_client import ExecutorClient
from app.lib.logger import get_logger

logger = get_logger(__name__)


async def ensure_executor_running() -> bool:
    """Auto-detect executor-web, start it if not running.

    Returns True if executor is responsive, False otherwise.
    """
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{settings.executor_web_url}/health")
            if r.json().get("status") == "ok":
                logger.info("Executor-web already running")
                return True
    except Exception:
        logger.info("Executor-web not detected, auto-starting...")

    executor_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "executor", "web"
    )
    proc = await asyncio.create_subprocess_exec(
        "npx", "tsx", "src/index.ts",
        cwd=executor_dir,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    for _ in range(30):
        try:
            async with httpx.AsyncClient(timeout=2) as c:
                r = await c.get(f"{settings.executor_web_url}/health")
                if r.json().get("status") == "ok":
                    logger.info("Executor-web auto-started (pid=%d)", proc.pid)
                    return True
        except Exception:
            await asyncio.sleep(1)
    logger.warning("Executor-web failed to start, continuing without browser")
    return False


class ExecutorFactory:
    """Creates WebExecutorClient for real browser-based test execution."""

    @staticmethod
    def create(platform: str = "web") -> ExecutorClient:
        if platform == "web":
            from app.infrastructure.executor.web_executor_client import WebExecutorClient
            return WebExecutorClient(base_url=settings.executor_web_url)
        raise ValueError(f"Unsupported platform: {platform}")

    @staticmethod
    async def health_check(platform: str = "web") -> bool:
        client = ExecutorFactory.create(platform=platform)
        try:
            return await client.ping()
        except Exception:
            return False
