"""Execution engine: navigates to target URL, executes steps via real executor, collects data."""
import asyncio
from typing import Optional
from app.domain.models.run import StepExecutionRecord, RunRecord
from app.domain.models.scenario import TestStep
from app.interfaces.repositories.run_repo import RunRepository
from app.interfaces.repositories.scenario_repo import ScenarioRepository
from app.interfaces.repositories.defect_repo import DefectRepository
from app.interfaces.executor_client import ExecutorClient
from app.services.analysis_service import CrossDimensionAnalyzer
from app.infrastructure.executor import ExecutorFactory
from app.infrastructure.executor.ws_client import ExecutorWSClient
from app.lib.id_generator import generate_id
from app.lib.logger import get_logger

logger = get_logger(__name__)


class ExecutionEngine:
    def __init__(self, run_repo: RunRepository, scenario_repo: ScenarioRepository,
                 defect_repo: DefectRepository, executor=None, analyzer=None):
        self._run_repo = run_repo
        self._scenario_repo = scenario_repo
        self._defect_repo = defect_repo
        self._executor = executor or ExecutorFactory.create()
        self._analyzer = analyzer or CrossDimensionAnalyzer(defect_repo)

    async def execute_run(self, run_id: str, target_url: str = "",
                           steps: list[TestStep] | None = None,
                           entry: dict | None = None) -> dict:
        run = await self._run_repo.get_by_id(run_id)
        if not run:
            return {"error": f"Run {run_id} not found"}

        logger.info(f"Executing run {run_id} against {target_url}")

        health_ok = await self._executor.ping()
        if not health_ok:
            logger.error(f"Executor not reachable for run {run_id}")
            await self._run_repo.update_status(run_id, "failed")
            return {"error": "Executor not reachable — ensure executor-web is running at http://localhost:3100",
                    "run_id": run_id, "status": "failed"}

        return await self._execute_on_executor(run_id, target_url, steps, entry)

    async def _execute_on_executor(self, run_id: str, target_url: str,
                                    steps: list[TestStep] | None,
                                    entry: dict | None) -> dict:
        """Delegate execution to the Midscene executor server via REST + WS."""
        await self._run_repo.update_status(run_id, "running")

        cases = []
        if steps:
            cases = [{"id": "default", "name": "Default", "steps": steps}]

        run_config = await self._executor.create_run(
            run_id=run_id,
            entry=entry or {"url": target_url} if target_url else {},
            cases=cases,
        )
        logger.info(f"Run created on executor: {run_config}")

        # Connect WebSocket for real-time events
        ws_base = self._executor.base_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_base}/ws/run/{run_id}"
        ws_client = ExecutorWSClient(ws_url)

        def on_step_complete(payload: dict) -> None:
            step_idx = payload.get("stepIndex", 0)
            status = payload.get("status", "unknown")
            logger.info(f"WS event: step {step_idx} completed with status {status}")

        ws_client.on("step_complete", on_step_complete)
        ws_client_task = asyncio.ensure_future(ws_client.connect_with_reconnect())

        try:
            start_result = await self._executor.start_run(run_id)
            logger.info(f"Run started on executor: {start_result}")

            while True:
                await asyncio.sleep(1)
                progress = await self._executor.get_run_progress(run_id)
                pct = progress.get("progress", {}).get("percent", 0)
                status = progress.get("status", "running")
                await self._run_repo.update_progress(run_id, progress.get("progress", {}))
                logger.info(f"Run progress: {pct}% status={status}")
                if status in ("completed", "failed", "cancelled"):
                    break
        finally:
            await ws_client.disconnect()
            ws_client_task.cancel()

        await self._run_repo.update_status(run_id, status)

        return {
            "run_id": run_id,
            "status": status,
            "target_url": target_url or "",
            "summary": progress.get("summary", {}),
            "defect_count": 0,
            "defects": [],
            "steps": progress.get("steps", []),
        }
