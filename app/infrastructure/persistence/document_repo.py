from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.document import Document, DocumentRaw
from app.infrastructure.persistence.models import DocumentModel
from app.interfaces.repositories.document_repo import DocumentRepository


class SqlDocumentRepository(DocumentRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, document: Document) -> Document:
        model = DocumentModel(
            id=document.id,
            project_id=document.project_id,
            url=document.url,
            type=document.type,
            description=document.description,
            version=document.version,
            status=document.status,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(model)
        await self._session.commit()
        return document

    async def get_by_id(self, document_id: str) -> Document | None:
        result = await self._session.execute(
            select(DocumentModel).where(DocumentModel.id == document_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return Document(
            id=model.id, project_id=model.project_id, url=model.url,
            type=model.type, status=model.status, rule_count=model.rule_count,
            created_at=model.created_at, updated_at=model.updated_at,
        )

    async def get_by_project(self, project_id: str) -> list[Document]:
        result = await self._session.execute(
            select(DocumentModel).where(DocumentModel.project_id == project_id)
        )
        models = result.scalars().all()
        return [Document(id=m.id, project_id=m.project_id, url=m.url, type=m.type,
                         status=m.status) for m in models]

    async def update(self, document: Document) -> Document:
        model = await self._session.get(DocumentModel, document.id)
        if model:
            model.status = document.status
            model.rule_count = document.rule_count
            model.error_message = document.error_message
            await self._session.commit()
        return document

    async def delete(self, document_id: str) -> None:
        model = await self._session.get(DocumentModel, document_id)
        if model:
            await self._session.delete(model)
            await self._session.commit()

    async def save_raw(self, raw: DocumentRaw) -> DocumentRaw:
        return raw

    async def get_raw(self, document_id: str) -> DocumentRaw | None:
        return None
