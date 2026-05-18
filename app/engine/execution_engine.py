"""Execution engine: navigates to target URL, executes steps via executor, collects + analyzes data.

Replaces the previous WebSocket-based approach with direct HTTP calls to the executor
(see demo.py for the proven pattern). Each step is executed synchronously, analyzed
immediately, and recorded.
"""
from app.domain.models.scenario import TestStep
from app.infrastructure.executor import ExecutorFactory
from app.interfaces.repositories.defect_repo import DefectRepository
from app.interfaces.repositories.run_repo import RunRepository
from app.interfaces.repositories.scenario_repo import ScenarioRepository
from app.lib.logger import get_logger
from app.services.analysis_service import CrossDimensionAnalyzer

logger = get_logger(__name__)


class ExecutionEngine:
    """Orchestrates test execution: navigate → execute steps → analyze → report.

    Uses synchronous HTTP calls to the executor (no WebSocket dependency).
    Each step produces a StepExecutionRecord which is immediately analyzed
    by CrossDimensionAnalyzer for defect detection.
    """

    def __init__(self, run_repo: RunRepository, scenario_repo: ScenarioRepository,
                 defect_repo: DefectRepository, executor=None, analyzer=None):
        self._run_repo = run_repo
        self._scenario_repo = scenario_repo
        self._defect_repo = defect_repo
        self._executor = executor or ExecutorFactory.create()
        self._analyzer = analyzer or CrossDimensionAnalyzer(defect_repo)

    async def executor_ping(self) -> bool:
        """Check if executor is reachable."""
        try:
            return await self._executor.ping()
        except Exception:
            return False

    async def execute_run(self, run_id: str, target_url: str = "",
                          steps: list[TestStep] | None = None,
                          entry: dict | None = None,
                          case_id: str = "default") -> dict:
        """Execute a test run against a target URL.

        Flow: ping → navigate → for each step: execute → analyze → save → report.
        """
        run = await self._run_repo.get_by_id(run_id)
        if not run:
            return {"error": f"Run {run_id} not found"}

        logger.info("Executing run %s against %s", run_id, target_url)

        # 1. Health check
        health_ok = await self._executor.ping()
        if not health_ok:
            logger.error("Executor not reachable for run %s", run_id)
            await self._run_repo.update_status(run_id, "failed")
            return {"error": "Executor not reachable — ensure executor-web is running at http://localhost:3100",
                    "run_id": run_id, "status": "failed"}

        await self._run_repo.update_status(run_id, "running")
        url = target_url or (entry or {}).get("url", "")
        step_list = steps or []
        total = len(step_list)
        passed = failed = 0
        step_records = []
        defects = []

        # 2. Navigate to target URL
        if url:
            try:
                nav = await self._executor.navigate(url)
                logger.info("Navigated to %s -> %s", url, nav.current_url or url)
            except Exception as e:
                await self._run_repo.update_status(run_id, "failed")
                return {"error": f"Navigation failed: {e}", "run_id": run_id, "status": "failed"}

        # 3. Execute each step
        for step in step_list:
            context = {"run_id": run_id, "case_id": case_id}
            record = await self._executor.execute_step(step, context)
            step_records.append(record)

            # 4. Cross-dimension analysis
            try:
                defect = await self._analyzer.analyze(record)
                if defect:
                    defects.append(defect)
            except Exception as e:
                logger.error("Analysis failed for step %d: %s", step.index, e)

            # 5. Progress tracking
            if record.status == "passed":
                passed += 1
            else:
                failed += 1
            pct = round((len(step_records) / total) * 100) if total else 100
            await self._run_repo.update_progress(run_id, {
                "percent": pct,
                "completed": len(step_records),
                "total": total,
                "passed": passed,
                "failed": failed,
            })

        # 6. Save step records
        for rec in step_records:
            try:
                await self._run_repo.save_step(rec)
            except Exception as e:
                logger.warning("Failed to save step %s: %s", rec.id, e)

        # 7. Finalize
        final_status = "completed" if failed == 0 else "completed_with_defects"
        await self._run_repo.update_status(run_id, final_status)

        return {
            "run_id": run_id,
            "status": final_status,
            "target_url": url,
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "defects": len(defects),
                "pass_rate": round(passed / total, 4) if total else 0,
            },
            "defects": [
                {"id": d.id, "severity": d.severity, "title": d.title, "type": d.type}
                for d in defects
            ],
            "steps": [
                {"step_index": r.step_index, "action": r.action,
                 "status": r.status, "duration_ms": r.duration_ms,
                 "console_errors": len(r.console_snapshot.errors) if r.console_snapshot else 0}
                for r in step_records
            ],
        }
