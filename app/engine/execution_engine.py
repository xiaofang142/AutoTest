"""Execution engine: runs test cases through executor, collects data, verifies, reports."""
import asyncio, json, time
from typing import Optional
from app.domain.models.run import StepExecutionRecord, RunRecord, RunSummary
from app.domain.models.scenario import TestCase, TestStep
from app.domain.models.defect import Defect
from app.interfaces.repositories.run_repo import RunRepository
from app.interfaces.repositories.scenario_repo import ScenarioRepository
from app.interfaces.repositories.defect_repo import DefectRepository
from app.interfaces.executor_client import ExecutorClient
from app.services.analysis_service import CrossDimensionAnalyzer
from app.infrastructure.executor import create_executor_client
from app.lib.id_generator import generate_id
from app.lib.logger import get_logger

logger = get_logger(__name__)


class ExecutionEngine:
    """Executes test runs: processes cases through executor, collects 4D data, reports."""

    def __init__(self, run_repo: RunRepository, scenario_repo: ScenarioRepository,
                 defect_repo: DefectRepository,
                 executor: Optional[ExecutorClient] = None,
                 analyzer: Optional[CrossDimensionAnalyzer] = None):
        self._run_repo = run_repo
        self._scenario_repo = scenario_repo
        self._defect_repo = defect_repo
        self._executor = executor or create_executor_client()
        self._analyzer = analyzer or CrossDimensionAnalyzer(defect_repo)

    async def execute_run(self, run_id: str) -> dict:
        """Execute a complete run: all cases → all steps → collect → verify → report."""
        run = await self._run_repo.get_by_id(run_id)
        if not run:
            return {"error": f"Run {run_id} not found"}

        logger.info(f"Executing run: {run_id}")
        await self._run_repo.update_status(run_id, "running")

        results = []
        all_defects = []
        case_results = []

        # For each case in the run
        run_cases = await self._run_repo.get_steps(run_id)
        if not run_cases:
            # No steps yet - need to get from scenarios
            logger.info("No steps in run, checking for scenarios")
            # For now, create a basic step list
            pass

        # Get the test cases from the run's project
        # In a real system, run_cases links to test_cases
        # For this engine, we iterate over steps stored in run

        # Simple execution: run with progress updates
        total_steps = max(run.total_cases, 1)
        completed = 0

        for case_idx in range(run.total_cases or 1):
            # Create a mock step for demonstration
            step = TestStep(index=1, action="执行测试用例", target=f"用例 {case_idx + 1}",
                          verifications=["ui", "console", "api"])

            context = {"run_id": run_id, "case_id": f"case_{case_idx}", "platform": "web"}
            step_result = await self._executor.execute_step(step, context)

            # Run 4D analysis
            defect = await self._analyzer.analyze(step_result)
            if defect:
                all_defects.append(defect)

            # Save step
            step_result.id = generate_id("step")
            step_result.run_id = run_id
            await self._run_repo.save_step(step_result)

            completed += 1
            progress = {"total": total_steps, "completed": completed, "percent": int(completed / total_steps * 100)}
            await self._run_repo.update_progress(run_id, progress)

            results.append({
                "step_index": step.index,
                "status": step_result.status,
                "action": step_result.action,
                "has_screenshot": bool(step_result.screenshots.get("after")),
                "console_errors": len(step_result.console_snapshot.errors) if step_result.console_snapshot else 0,
                "api_calls": len(step_result.network_snapshot.requests) if step_result.network_snapshot else 0,
                "defect": defect.id if defect else None,
            })

        # Finalize run
        passed = sum(1 for r in results if r["status"] == "passed")
        failed = sum(1 for r in results if r["status"] == "failed")
        uncertain = sum(1 for r in results if r["status"] == "uncertain")

        await self._run_repo.update_status(run_id, "completed")
        final_progress = {"total": total_steps, "completed": completed, "percent": 100}
        await self._run_repo.update_progress(run_id, final_progress)

        report = {
            "run_id": run_id,
            "status": "completed",
            "summary": {
                "total": total_steps, "passed": passed, "failed": failed, "uncertain": uncertain,
                "pass_rate": passed / total_steps if total_steps else 0,
            },
            "defect_count": len(all_defects),
            "defects": [{"id": d.id, "severity": d.severity, "title": d.title} for d in all_defects],
            "steps": results,
            "duration_seconds": 0,
        }
        logger.info(f"Run {run_id} completed: {passed}/{total_steps} passed, {len(all_defects)} defects")
        return report
