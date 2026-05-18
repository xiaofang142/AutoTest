from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.defect import Defect
from app.infrastructure.persistence.models import DefectModel
from app.interfaces.repositories.defect_repo import DefectRepository


class SqlDefectRepository(DefectRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, defect: Defect) -> Defect:
        model = DefectModel(
            id=defect.id, run_id=defect.run_id, step_record_id=defect.step_record_id,
            type=defect.type, severity=defect.severity, title=defect.title,
            step_context=defect.step_context, screenshots=defect.screenshots,
            console_logs=defect.console_logs, api_calls={"calls": defect.api_calls},
            page_state=defect.page_state, ai_analysis=defect.ai_analysis,
            fix_suggestion=defect.fix_suggestion.model_dump() if defect.fix_suggestion else None,
            cross_dimension_analysis=defect.cross_dimension_analysis,
            is_false_positive=defect.is_false_positive,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(model)
        await self._session.commit()
        return defect

    async def get_by_id(self, defect_id: str) -> Defect | None:
        model = await self._session.get(DefectModel, defect_id)
        if not model:
            return None
        return self._model_to_domain(model)

    async def get_by_run(self, run_id: str, severity: str | None = None) -> list[Defect]:
        query = select(DefectModel).where(DefectModel.run_id == run_id)
        if severity:
            query = query.where(DefectModel.severity == severity)
        result = await self._session.execute(query)
        models = result.scalars().all()
        return [self._model_to_domain(m) for m in models]

    async def update(self, defect: Defect) -> Defect:
        model = await self._session.get(DefectModel, defect.id)
        if model:
            model.is_false_positive = defect.is_false_positive
            await self._session.commit()
        return defect

    def _model_to_domain(self, model: DefectModel) -> Defect:
        api_calls = model.api_calls.get("calls", []) if model.api_calls else []
        return Defect(
            id=model.id, run_id=model.run_id, step_record_id=model.step_record_id or "",
            type=model.type, severity=model.severity, title=model.title,
            step_context=model.step_context or {},
            screenshots=model.screenshots or {},
            console_logs=model.console_logs or {},
            api_calls=api_calls,
            page_state=model.page_state or {},
            ai_analysis=model.ai_analysis or {},
            is_false_positive=model.is_false_positive,
            created_at=model.created_at,
        )
