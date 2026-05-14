"""Execution engine: navigates to target URL, executes steps, collects data, reports."""
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

        logger.info(f"Executing run {run_id} against {target_url or 'mock'}")

        # Real executor mode: delegate to executor server
        if hasattr(self._executor, 'mode') and self._executor.mode == "real":
            return await self._execute_via_executor(run_id, target_url, steps, entry)

        # Mock/local mode: sequential in-process execution
        return await self._execute_local(run, run_id, target_url, steps)

    async def _execute_via_executor(self, run_id: str, target_url: str,
                                     steps: list[TestStep] | None,
                                     entry: dict | None) -> dict:
        """Delegate execution to the Midscene executor server via REST + WS."""
        health_ok = await self._executor.ping()
        if not health_ok:
            logger.error(f"Executor health check failed for run {run_id}")
            await self._run_repo.update_status(run_id, "failed")
            return {"error": f"Executor not reachable", "run_id": run_id, "status": "failed"}

        logger.info(f"Executor health check passed for run {run_id}")

        # Create the run on the executor server
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
        ws_url = f"{ws_base}/run/{run_id}/events"
        ws_client = ExecutorWSClient(ws_url)

        def on_step_complete(payload: dict) -> None:
            step_idx = payload.get("stepIndex", 0)
            status = payload.get("status", "unknown")
            logger.info(f"WS event: step {step_idx} completed with status {status}")

        ws_client.on("step_complete", on_step_complete)
        ws_client_task = asyncio.ensure_future(ws_client.connect_with_reconnect())

        try:
            # Start the run
            start_result = await self._executor.start_run(run_id)
            logger.info(f"Run started on executor: {start_result}")

            # Poll for completion
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

        # Collect results
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

    async def _execute_local(self, run: RunRecord, run_id: str, target_url: str,
                              steps: list[TestStep] | None) -> dict:
        """Sequential in-process execution (mock mode)."""
        await self._run_repo.update_status(run_id, "running")

        # Generate test steps if not provided
        if not steps:
            steps = self._default_steps(target_url)

        results = []
        all_defects = []
        total = len(steps)

        if hasattr(self._executor, 'navigate') and target_url:
            try:
                nav_result = await self._executor.navigate(target_url)
                logger.info(f"Navigated to {target_url}")
            except Exception as e:
                logger.warning(f"Navigation failed (mock mode): {e}")

        for i, step in enumerate(steps):
            context = {"run_id": run_id, "platform": "web"}
            step_result = await self._executor.execute_step(step, context)
            defect = await self._analyzer.analyze(step_result)

            if defect:
                all_defects.append(defect)

            step_result.id = generate_id("step")
            step_result.run_id = run_id
            await self._run_repo.save_step(step_result)

            progress = {"total": total, "completed": i + 1,
                        "percent": int((i + 1) / total * 100)}
            await self._run_repo.update_progress(run_id, progress)

            results.append({
                "step_index": step.index,
                "status": step_result.status,
                "action": step_result.action,
                "target": step_result.page_state.current_url or "",
                "screenshots": {"after": step_result.screenshots.get("after", "")},
                "console_errors": len(step_result.console_snapshot.errors) if step_result.console_snapshot else 0,
                "api_calls": len(step_result.network_snapshot.requests) if step_result.network_snapshot else 0,
                "defect": defect.id if defect else None,
            })

        passed = sum(1 for r in results if r["status"] == "passed")
        failed = sum(1 for r in results if r["status"] == "failed")
        await self._run_repo.update_status(run_id, "completed")
        await self._run_repo.update_progress(run_id, {"total": total, "completed": total, "percent": 100})

        return {
            "run_id": run_id,
            "status": "completed",
            "target_url": target_url,
            "summary": {"total": total, "passed": passed, "failed": failed,
                        "pass_rate": passed / total if total else 0},
            "defect_count": len(all_defects),
            "defects": [{"id": d.id, "severity": d.severity, "title": d.title} for d in all_defects],
            "steps": results,
        }

    def _default_steps(self, url: str = "") -> list[TestStep]:
        if url:
            return [
                TestStep(index=1, action="打开页面", target=url, verifications=["ui", "console"]),
                TestStep(index=2, action="检查页面加载", target="页面应正常渲染无报错",
                        verifications=["ui", "console", "api"]),
                TestStep(index=3, action="验证页面标题", target="页面标题应存在",
                        verifications=["ui"]),
            ]
        return [
            TestStep(index=1, action="执行测试用例", target="默认测试",
                    verifications=["ui", "console", "api"]),
        ]
