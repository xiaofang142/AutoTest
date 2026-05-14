from app.domain.models.knowledge import KnowledgeBase, BusinessRule, Conflict, QualityScore
from app.domain.exceptions import KnowledgeBaseNotFoundError
from app.interfaces.repositories.knowledge_repo import KnowledgeBaseRepository
from app.lib.id_generator import generate_id
from app.lib.logger import get_logger

logger = get_logger(__name__)


class KnowledgeService:
    def __init__(self, kb_repo: KnowledgeBaseRepository):
        self._repo = kb_repo

    async def get_knowledge_base(self, project_id: str) -> KnowledgeBase:
        kb = await self._repo.get_by_project(project_id)
        if not kb:
            raise KnowledgeBaseNotFoundError(f"project={project_id}")
        return kb

    async def create_knowledge_base(self, project_id: str) -> KnowledgeBase:
        kb = KnowledgeBase(
            id=generate_id("knowledge"),
            project_id=project_id,
        )
        created = await self._repo.create(kb)
        logger.info(f"Knowledge base created: {created.id}")
        return created

    async def update_rule(self, rule_id: str, content: str, status: str = "confirmed") -> BusinessRule:
        rule = BusinessRule(id=rule_id, kb_id="", content=content, status=status)
        return await self._repo.update_rule(rule)

    async def get_rules(self, kb_id: str, category: str | None = None) -> list[BusinessRule]:
        return await self._repo.get_rules(kb_id, category)

    async def get_conflicts(self, kb_id: str) -> list[Conflict]:
        return await self._repo.get_conflicts(kb_id)

    async def resolve_conflict(self, conflict_id: str, resolution: str) -> Conflict:
        conflict = Conflict(id=conflict_id, kb_id="", status="resolved", resolution=resolution)
        return await self._repo.resolve_conflict(conflict)
