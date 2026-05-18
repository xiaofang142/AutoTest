import pytest
from unittest.mock import AsyncMock
from app.domain.models.task import TestTask, TaskInput
from app.engine.task_orchestrator import TaskOrchestrator
from app.engine.execution_engine import ExecutionEngine
from app.infrastructure.persistence.task_repo import InMemoryTaskRepository


@pytest.fixture
def repo():
    return InMemoryTaskRepository()


@pytest.fixture
def engine():
    eng = AsyncMock(spec=ExecutionEngine)
    eng.executor_ping.return_value = True
    eng.execute_run.return_value = {
        "run_id": "run_test",
        "status": "completed",
        "summary": {"total": 5, "passed": 5, "failed": 0, "defects": 0},
        "defects": [],
        "steps": [
            {"step_index": i, "action": f"step_{i}", "status": "passed", "duration_ms": 100}
            for i in range(5)
        ],
    }
    return eng


@pytest.mark.asyncio
async def test_orchestrator_completed(repo, engine):
    task = await repo.create(TestTask(name="test", input=TaskInput(target_url="https://x.com")))
    orch = TaskOrchestrator(repo, engine)
    result = await orch.run_pipeline(task.id)

    assert result["status"] == "completed"
    updated = await repo.get_by_id(task.id)
    assert updated.status == "completed"
    assert updated.environment_check is not None
    assert updated.understanding is not None
    assert updated.blueprint is not None
    assert updated.delivery is not None
    assert updated.delivery_ready is True
    assert updated.progress_percent == 100


@pytest.mark.asyncio
async def test_orchestrator_executor_offline(repo):
    eng = AsyncMock(spec=ExecutionEngine)
    eng.executor_ping.return_value = False
    task = await repo.create(TestTask(name="test", input=TaskInput(target_url="https://x.com")))
    orch = TaskOrchestrator(repo, eng)
    result = await orch.run_pipeline(task.id)

    assert result["status"] == "blocked"
    updated = await repo.get_by_id(task.id)
    assert updated.status == "blocked"
    assert updated.current_stage == "prechecking"


@pytest.mark.asyncio
async def test_orchestrator_error_handling(repo):
    eng = AsyncMock(spec=ExecutionEngine)
    eng.executor_ping.side_effect = Exception("Unexpected crash")
    task = await repo.create(TestTask(name="test", input=TaskInput(target_url="https://x.com")))
    orch = TaskOrchestrator(repo, eng)
    result = await orch.run_pipeline(task.id)

    assert result["status"] == "error"
    updated = await repo.get_by_id(task.id)
    assert updated.status == "error"
