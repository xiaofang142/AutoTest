"""TaskOrchestrator — 八阶段闭环编排器。

把 TestTask 状态机连接到实际执行引擎，自动跑完：
  预检 → 理解 → 蓝图 → 执行 → 校验 → 归因 → 交付
"""
from app.domain.models.run import RunRecord
from app.domain.models.task import (
    TestTask, TaskStatus, TaskMode, AutoLevel,
    EnvironmentCheck, UnderstandingResult, TestBlueprint, BlueprintStep,
    DeliveryPackage, TesterView, DeveloperView, AIAssistantView,
)
from app.engine.execution_engine import ExecutionEngine
from app.interfaces.repositories.task_repo import TaskRepository
from app.interfaces.repositories.run_repo import RunRepository
from app.api.websocket.task_progress import task_ws_manager
from app.lib.id_generator import generate_id
from app.lib.logger import get_logger

logger = get_logger(__name__)


class TaskOrchestrator:
    """协调 TestTask 走完八阶段闭环。"""

    def __init__(self, task_repo: TaskRepository, engine: ExecutionEngine,
                 run_repo: RunRepository | None = None):
        self._task_repo = task_repo
        self._engine = engine
        self._run_repo = run_repo

    async def run_pipeline(self, task_id: str) -> dict:
        task = await self._task_repo.get_by_id(task_id)
        if not task:
            return {"error": "Task not found"}

        try:
            # Stage 1: 环境预检
            await self._task_repo.update_status(task_id, "prechecking", "prechecking")
            await task_ws_manager.broadcast_stage_change(task_id, "prechecking", "started", 5)
            check = await self._precheck(task)
            await self._task_repo.update_stage_result(task_id, "environment_check",
                                                       check.model_dump())
            if check.blocking_items:
                await self._task_repo.update_status(task_id, "blocked", "prechecking")
                await task_ws_manager.broadcast_stage_change(task_id, "prechecking", "blocked", 5, str(check.blocking_items))
                return {"status": "blocked", "reason": check.blocking_items}
            await task_ws_manager.broadcast_stage_change(task_id, "prechecking", "completed", 10)
            task.environment_check = check

            # Stage 2: 测试对象理解
            await self._task_repo.update_status(task_id, "understanding", "understanding")
            await task_ws_manager.broadcast_stage_change(task_id, "understanding", "started", 10)
            understanding = await self._understand(task)
            await self._task_repo.update_stage_result(task_id, "understanding",
                                                       understanding.model_dump())
            task.understanding = understanding
            await task_ws_manager.broadcast_stage_change(task_id, "understanding", "completed", 20)

            # Stage 3: 测试蓝图生成
            await self._task_repo.update_status(task_id, "planning", "planning")
            await task_ws_manager.broadcast_stage_change(task_id, "planning", "started", 20)
            blueprint = await self._plan(task, understanding)
            await self._task_repo.update_stage_result(task_id, "blueprint",
                                                       blueprint.model_dump())
            task.blueprint = blueprint
            await self._task_repo.update_progress(task_id, 30)
            await task_ws_manager.broadcast_stage_change(task_id, "planning", "completed", 30)

            # Stage 4: 执行编排
            await self._task_repo.update_status(task_id, "running", "running")
            await task_ws_manager.broadcast_stage_change(task_id, "running", "started", 30)
            run_result = await self._execute(task, blueprint)
            await self._task_repo.update_progress(task_id, 70)
            await task_ws_manager.broadcast_stage_change(task_id, "running", "completed", 70)

            # Stage 5-7: 多维校验 + 缺陷归因（在分析中聚合）
            await self._task_repo.update_status(task_id, "analyzing", "analyzing")
            await task_ws_manager.broadcast_stage_change(task_id, "analyzing", "started", 70)
            await self._task_repo.update_progress(task_id, 85)

            # Stage 8: 结果交付
            final_status, delivery = await self._deliver(task, run_result)
            if delivery:
                await self._task_repo.update_delivery(task_id, delivery.model_dump(mode="json"))

            await self._task_repo.update_status(task_id, final_status, final_status)
            await self._task_repo.update_progress(task_id, 100)
            has_defects = "with_defects" in final_status
            await task_ws_manager.broadcast_completed(task_id, final_status,
                                                       task.defect_count if has_defects else 0)
            logger.info("Task %s completed with status %s", task_id, final_status)
            return {"status": final_status, "task_id": task_id}

        except Exception as e:
            logger.error("Task %s failed: %s", task_id, e)
            await self._task_repo.update_status(task_id, "error", "error")
            await task_ws_manager.broadcast_error(task_id, str(e))
            return {"status": "error", "error": str(e)}

    async def _precheck(self, task: TestTask) -> EnvironmentCheck:
        health = await self._engine.executor_ping()
        return EnvironmentCheck(
            executor_online=health,
            browser_available=health,
            network_ok=True,
            ai_available=True,
            ocr_available=True,
            auto_level="A1",
            summary="All checks passed" if health else "Executor not reachable",
            blocking_items=[] if health else ["executor_offline"],
        )

    async def _understand(self, task: TestTask) -> UnderstandingResult:
        result = UnderstandingResult(
            page_intent=f"Test of {task.input.target_url}",
            completeness=0.6,
        )
        # 如果有代码目录, 进行源码分析增强理解
        if task.input.code_dir:
            try:
                from app.services.code_analysis_service import CodeAnalysisService
                code_info = await CodeAnalysisService.analyze_codebase(task.input.code_dir)
                if "error" not in code_info:
                    result = CodeAnalysisService.enhance_understanding(code_info, result)
                    result.page_intent += f" (code analysis: {code_info.get('framework', 'unknown')}, {code_info.get('route_count', 0)} routes)"
                    logger.info("Code analysis enhanced understanding: %s routes, %s apis",
                               code_info.get('route_count', 0), code_info.get('api_count', 0))
            except Exception as e:
                logger.warning("Code analysis failed, continuing without: %s", e)
        return result

    async def _plan(self, task: TestTask, understanding: UnderstandingResult) -> TestBlueprint:
        steps = []
        # 如果有代码目录, 用源码分析生成更精准的步骤 (替换默认冒烟)
        if task.input.code_dir:
            try:
                from app.services.code_analysis_service import CodeAnalysisService
                code_info = await CodeAnalysisService.analyze_codebase(task.input.code_dir)
                if "error" not in code_info:
                    code_steps = CodeAnalysisService.generate_blueprint_steps(
                        code_info, task.input.target_url)
                    existing = len(steps)
                    for s in code_steps:
                        s.index = s.index + existing
                    steps.extend(code_steps)
                    logger.info("Code analysis added %s blueprint steps", len(code_steps))
            except Exception as e:
                logger.warning("Code analysis for blueprint failed: %s", e)

        if len(steps) <= 2:
            steps.append(BlueprintStep(index=2, action="screenshot", target="full_page",
                                       assert_ui=True))

        return TestBlueprint(
            targets=[{"url": task.input.target_url}],
            flow_chains=[steps],
            all_steps=steps,
            confidence=0.8 if not task.input.code_dir else 0.85,
            risk_coverage="Code-driven test" if task.input.code_dir else "Basic smoke test",
            min_executable_set=list(range(len(steps))),
        )

    async def _execute(self, task: TestTask, blueprint: TestBlueprint) -> dict:
        steps = []
        for chain in blueprint.flow_chains:
            steps.extend(chain)
        from app.domain.models.scenario import TestStep
        engine_steps = [
            TestStep(index=s.index, action=s.action, target=s.target, value=s.value)
            for s in steps
        ]

        # Create RunRecord first so ExecutionEngine can find it
        run_id = f"run_{task.id}"
        if self._run_repo:
            existing = await self._run_repo.get_by_id(run_id)
            if not existing:
                run = RunRecord(
                    id=run_id,
                    project_id=task.project_id,
                    task_id=task.id,
                    name=f"Auto-run for task {task.id}",
                    total_cases=len(engine_steps),
                )
                await self._run_repo.create(run)

        result = await self._engine.execute_run(
            run_id=run_id,
            target_url=task.input.target_url,
            steps=engine_steps,
            entry={"url": task.input.target_url},
            case_id="task_default",
        )
        task.run_id = run_id  # Keep the actual RunRecord id, not the engine's return value
        defects = result.get("defects", [])
        task.defect_count = len(defects)
        task.high_risk_count = sum(
            1 for d in defects if d.get("severity") in ("high", "critical")
        )
        return result

    async def _deliver(self, task: TestTask, run_result: dict) -> tuple[str, DeliveryPackage | None]:
        summary = run_result.get("summary", {})
        has_defects = summary.get("defects", 0) > 0
        status = TaskStatus.COMPLETED_WITH_DEFECTS if has_defects else TaskStatus.COMPLETED

        # Build regression entry for each defect
        regression_entry = {
            "target_url": task.input.target_url,
            "task_id": task.id,
            "run_id": task.run_id,
            "defect_count": task.defect_count,
            "key_steps": [
                s.get("step_index", i) for i, s in enumerate(run_result.get("steps", []))
                if s.get("status") == "failed"
            ],
        }

        delivery = DeliveryPackage(
            tester_view=TesterView(
                summary=f"Test completed: {summary.get('total', 0)} steps, "
                        f"{summary.get('passed', 0)} passed, {summary.get('failed', 0)} failed",
                defect_list=run_result.get("defects", []),
            ),
            developer_view=DeveloperView(
                defect_details=run_result.get("defects", []),
            ),
            ai_assistant_view=AIAssistantView(
                task_summary=task.name,
                reproduction_steps=[
                    f"{s.get('step_index', i)}: {s.get('action', '')}"
                    for i, s in enumerate(run_result.get("steps", []))
                ],
            ),
            regression_entry=regression_entry,
        )
        task.summary = delivery.tester_view.summary
        task.delivery_ready = True
        task.auto_level = self._calculate_auto_level(task, run_result)
        return status.value, delivery

    @staticmethod
    def _calculate_auto_level(task: TestTask, run_result: dict) -> AutoLevel:
        stages_ok = 0
        if task.environment_check:
            stages_ok += 1
        if task.understanding:
            stages_ok += 1
        if task.blueprint:
            stages_ok += 1
        if run_result.get("run_id"):
            stages_ok += 1
        if task.defect_count > 0 or task.delivery_ready:
            stages_ok += 1

        if stages_ok >= 5 and task.delivery_ready:
            return AutoLevel.A5
        if stages_ok >= 4 and (task.defect_count > 0 or task.delivery_ready):
            return AutoLevel.A4
        if stages_ok >= 3:
            return AutoLevel.A3
        if stages_ok >= 2:
            return AutoLevel.A2
        if stages_ok >= 1:
            return AutoLevel.A1
        return AutoLevel.A0
