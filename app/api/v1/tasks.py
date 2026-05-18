"""任务驱动 API — 自动测试任务的 CRUD、启动、取消、子资源获取。"""
from fastapi import APIRouter, Depends

from app.domain.models.task import (
    TestTask, TaskInput, TaskMode, TaskGoal, TaskDepth,
    TaskStatus, TaskStateMachine,
)
from app.interfaces.repositories.task_repo import TaskRepository
from app.dependencies import get_task_repo
from app.lib.id_generator import generate_id

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("")
async def create_task(
    name: str,
    target_url: str = "",
    code_dir: str = "",
    mode: str = "quick",
    goal: str = "smoke",
    depth: str = "standard",
    project_id: str = "",
    doc_ids: str = "",
    description: str = "",
    task_repo: TaskRepository = Depends(get_task_repo),
):
    task = TestTask(
        id=generate_id("task"),
        name=name,
        description=description,
        project_id=project_id,
        input=TaskInput(target_url=target_url, code_dir=code_dir,
                        documents=doc_ids.split(",") if doc_ids else []),
        mode=TaskMode(mode),
        goal=TaskGoal(goal),
        depth=TaskDepth(depth),
    )
    created = await task_repo.create(task)
    return {"code": 0, "data": {"task": created.model_dump(mode="json")}}


@router.get("")
async def list_tasks(
    project_id: str = "",
    status: str = "",
    page: int = 1,
    page_size: int = 20,
    task_repo: TaskRepository = Depends(get_task_repo),
):
    result = await task_repo.list_tasks(project_id, status, page, page_size)
    return {"code": 0, "data": result}


@router.get("/{task_id}")
async def get_task(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    if not task:
        return {"code": 40001, "message": "Task not found"}
    return {"code": 0, "data": {"task": task.model_dump(mode="json")}}


@router.post("/{task_id}/start")
async def start_task(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    if not task:
        return {"code": 40001, "message": "Task not found"}
    if not TaskStateMachine.can_transition(task.status, TaskStatus.PRECHECKING):
        return {"code": 40003, "message": f"Cannot start task in status {task.status}"}
    await task_repo.update_status(task_id, "prechecking", "prechecking")

    # Fire pipeline in background
    import asyncio
    from app.dependencies import init_services
    from app.engine.task_orchestrator import TaskOrchestrator
    from app.engine.execution_engine import ExecutionEngine
    from app.lib.logger import get_logger

    async def _run():
        try:
            # Don't call init_services() again - it would overwrite repos.
            # The repos are already initialized by the first API call.
            from app.dependencies import get_run_repo
            from app.engine.execution_engine import ExecutionEngine
            rr = get_run_repo()
            engine = ExecutionEngine(
                run_repo=rr, scenario_repo=None,
                defect_repo=None,
            )
            orch = TaskOrchestrator(task_repo, engine, run_repo=rr)
            await orch.run_pipeline(task_id)
        except Exception as e:
            get_logger(__name__).error("Background pipeline failed for %s: %s", task_id, e)

    asyncio.create_task(_run())
    return {"code": 0, "data": {"task_id": task_id, "status": "prechecking"}}


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    if not task:
        return {"code": 40001, "message": "Task not found"}
    await task_repo.update_status(task_id, "cancelled", "")
    return {"code": 0, "data": {"task_id": task_id, "status": "cancelled"}}


@router.get("/{task_id}/timeline")
async def get_task_timeline(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    if not task:
        return {"code": 40001, "message": "Task not found"}
    return {
        "code": 0,
        "data": {
            "task_id": task_id,
            "current_stage": task.current_stage,
            "progress": task.progress_percent,
            "status": task.status,
        },
    }


@router.get("/{task_id}/delivery")
async def get_task_delivery(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    if not task:
        return {"code": 40001, "message": "Task not found"}
    if not task.delivery:
        return {"code": 40003, "message": "Delivery not ready yet"}
    return {"code": 0, "data": task.delivery.model_dump(mode="json")}


@router.get("/{task_id}/defects")
async def get_task_defects(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    if not task:
        return {"code": 40001, "message": "Task not found"}
    # 优先从 delivery 获取缺陷数据 (更可靠)
    defects = []
    if task.delivery:
        defects = task.delivery.tester_view.defect_list
    elif task.run_id:
        from app.dependencies import get_analyzer
        analyzer = get_analyzer()
        if analyzer and analyzer._defect_repo:
            dl = await analyzer._defect_repo.get_by_run(task.run_id)
            defects = [d.model_dump(mode="json") for d in dl]
    return {
        "code": 0,
        "data": {
            "defect_count": len(defects),
            "high_risk_count": sum(1 for d in defects if d.get("severity") in ("high", "critical")),
            "defects": defects,
        },
    }


@router.get("/{task_id}/environment-check")
async def get_task_environment_check(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    if not task:
        return {"code": 40001, "message": "Task not found"}
    return {
        "code": 0,
        "data": task.environment_check.model_dump(mode="json") if task.environment_check else {},
    }


@router.get("/{task_id}/understanding")
async def get_task_understanding(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    if not task:
        return {"code": 40001, "message": "Task not found"}
    return {
        "code": 0,
        "data": task.understanding.model_dump(mode="json") if task.understanding else {},
    }


@router.get("/{task_id}/blueprint")
async def get_task_blueprint(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    if not task:
        return {"code": 40001, "message": "Task not found"}
    return {
        "code": 0,
        "data": task.blueprint.model_dump(mode="json") if task.blueprint else {},
    }


@router.get("/{task_id}/repair-context")
async def get_task_repair_context(task_id: str, task_repo: TaskRepository = Depends(get_task_repo)):
    task = await task_repo.get_by_id(task_id)
    if not task:
        return {"code": 40001, "message": "Task not found"}
    if not task.delivery:
        return {"code": 40003, "message": "Repair context not available yet"}
    return {
        "code": 0,
        "data": task.delivery.ai_assistant_view.model_dump(mode="json"),
    }
