from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.knowledge import KnowledgeBase, BusinessRule, Conflict
from app.infrastructure.persistence.models import KnowledgeBaseModel, BusinessRuleModel
from app.interfaces.repositories.knowledge_repo import KnowledgeBaseRepository


class PostgresKnowledgeBaseRepository(KnowledgeBaseRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, kb: KnowledgeBase) -> KnowledgeBase:
        model = KnowledgeBaseModel(
            id=kb.id, project_id=kb.project_id, version=kb.version,
            quality_grade=kb.quality_grade,
            quality_score=kb.quality_score.model_dump() if hasattr(kb.quality_score, "model_dump") else {},
            total_rules=kb.total_rules, confirmed_rules=kb.confirmed_rules,
            conflicts_count=kb.conflicts_count,
            created_at=datetime.now(), updated_at=datetime.now(),
        )
        self._session.add(model)
        await self._session.commit()
        return kb

    async def get_by_project(self, project_id: str) -> KnowledgeBase | None:
        result = await self._session.execute(
            select(KnowledgeBaseModel).where(KnowledgeBaseModel.project_id == project_id)
            .order_by(KnowledgeBaseModel.version.desc())
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return KnowledgeBase(id=model.id, project_id=model.project_id, version=model.version)

    async def get_by_id(self, kb_id: str) -> KnowledgeBase | None:
        model = await self._session.get(KnowledgeBaseModel, kb_id)
        if not model:
            return None
        return KnowledgeBase(id=model.id, project_id=model.project_id, version=model.version)

    async def update(self, kb: KnowledgeBase) -> KnowledgeBase:
        model = await self._session.get(KnowledgeBaseModel, kb.id)
        if model:
            model.version = kb.version
            model.total_rules = kb.total_rules
            model.updated_at = datetime.now()
            await self._session.commit()
        return kb

    async def get_rules(self, kb_id: str, category: str | None = None) -> list[BusinessRule]:
        query = select(BusinessRuleModel).where(BusinessRuleModel.kb_id == kb_id)
        if category:
            query = query.where(BusinessRuleModel.category == category)
        result = await self._session.execute(query)
        models = result.scalars().all()
        return [BusinessRule(id=m.id, kb_id=m.kb_id, category=m.category,
                             content=m.content, confidence=m.confidence, status=m.status)
                for m in models]

    async def create_rule(self, rule: BusinessRule) -> BusinessRule:
        model = BusinessRuleModel(
            id=rule.id, kb_id=rule.kb_id, category=rule.category, content=rule.content,
            confidence=rule.confidence, status=rule.status,
        )
        self._session.add(model)
        await self._session.commit()
        return rule

    async def update_rule(self, rule: BusinessRule) -> BusinessRule:
        model = await self._session.get(BusinessRuleModel, rule.id)
        if model:
            model.content = rule.content
            model.status = rule.status
            await self._session.commit()
        return rule

    async def get_conflicts(self, kb_id: str) -> list[Conflict]:
        return []

    async def resolve_conflict(self, conflict: Conflict) -> Conflict:
        return conflict
