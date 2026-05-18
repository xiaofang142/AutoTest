from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.run import RunRecord, RunSummary, StepExecutionRecord
from app.infrastructure.persistence.models import RunModel, StepRecordModel
from app.interfaces.repositories.run_repo import RunRepository


class SqlRunRepository(RunRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, run: RunRecord) -> RunRecord:
        model = RunModel(
            id=run.id, project_id=run.project_id, name=run.name,
            status=run.status, platforms=run.platforms,
            total_cases=run.total_cases,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(model)
        await self._session.commit()
        return run

    async def get_by_id(self, run_id: str) -> RunRecord | None:
        model = await self._session.get(RunModel, run_id)
        if not model:
            return None
        return RunRecord(
            id=model.id, project_id=model.project_id, name=model.name or "",
            status=model.status, platforms=model.platforms or ["web"],
            total_cases=model.total_cases,
            passed_count=model.passed_count, failed_count=model.failed_count,
            uncertain_count=model.uncertain_count,
            summary=RunSummary(
                total_cases=model.total_cases, passed=model.passed_count,
                failed=model.failed_count, uncertain=model.uncertain_count,
                pass_rate=(model.passed_count / model.total_cases) if model.total_cases else 0,
            ),
            started_at=model.started_at, completed_at=model.completed_at,
            created_at=model.created_at, progress=model.progress or {},
        )

    async def get_by_project(self, project_id: str) -> list[RunRecord]:
        result = await self._session.execute(
            select(RunModel).where(RunModel.project_id == project_id)
            .order_by(RunModel.created_at.desc())
        )
        models = result.scalars().all()
        return [RunRecord(id=m.id, project_id=m.project_id, name=m.name or "",
                          status=m.status, total_cases=m.total_cases)
                for m in models]

    async def update_status(self, run_id: str, status: str) -> None:
        await self._session.execute(
            update(RunModel).where(RunModel.id == run_id).values(
                status=status,
                completed_at=datetime.now(timezone.utc) if status in ("completed", "cancelled", "failed") else None,
            )
        )
        await self._session.commit()

    async def update_progress(self, run_id: str, progress: dict) -> None:
        await self._session.execute(
            update(RunModel).where(RunModel.id == run_id).values(progress=progress)
        )
        await self._session.commit()

    async def save_step(self, step: StepExecutionRecord) -> StepExecutionRecord:
        model = StepRecordModel(
            id=step.id or "", run_id=step.run_id, case_id=step.case_id,
            step_index=step.step_index, action=step.action,
            platform=step.platform, status=step.status,
            duration_ms=step.duration_ms,
            screenshots=step.screenshots or {},
            console_snapshot=step.console_snapshot.model_dump() if hasattr(step.console_snapshot, "model_dump") else {},
            network_snapshot=step.network_snapshot.model_dump() if hasattr(step.network_snapshot, "model_dump") else {},
            page_state=step.page_state.model_dump() if hasattr(step.page_state, "model_dump") else {},
            verifications=step.verifications.model_dump() if hasattr(step.verifications, "model_dump") else {},
            error=step.error,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(model)
        await self._session.commit()
        return step

    async def get_steps(self, run_id: str) -> list[StepExecutionRecord]:
        result = await self._session.execute(
            select(StepRecordModel).where(StepRecordModel.run_id == run_id)
            .order_by(StepRecordModel.step_index)
        )
        models = result.scalars().all()
        return [StepExecutionRecord(
            id=m.id, run_id=m.run_id, case_id=m.case_id,
            step_index=m.step_index, action=m.action, platform=m.platform,
            status=m.status, duration_ms=m.duration_ms,
        ) for m in models]
