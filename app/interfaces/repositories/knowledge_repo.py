from abc import ABC, abstractmethod

from app.domain.models.knowledge import BusinessRule, Conflict, KnowledgeBase


class KnowledgeBaseRepository(ABC):
    @abstractmethod
    async def create(self, kb: KnowledgeBase) -> KnowledgeBase:
        ...

    @abstractmethod
    async def get_by_project(self, project_id: str) -> KnowledgeBase | None:
        ...

    @abstractmethod
    async def get_by_id(self, kb_id: str) -> KnowledgeBase | None:
        ...

    @abstractmethod
    async def update(self, kb: KnowledgeBase) -> KnowledgeBase:
        ...

    @abstractmethod
    async def get_rules(self, kb_id: str, category: str | None = None) -> list[BusinessRule]:
        ...

    @abstractmethod
    async def create_rule(self, rule: BusinessRule) -> BusinessRule:
        ...

    @abstractmethod
    async def update_rule(self, rule: BusinessRule) -> BusinessRule:
        ...

    @abstractmethod
    async def get_conflicts(self, kb_id: str) -> list[Conflict]:
        ...

    @abstractmethod
    async def resolve_conflict(self, conflict: Conflict) -> Conflict:
        ...
