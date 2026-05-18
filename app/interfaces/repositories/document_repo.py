from abc import ABC, abstractmethod

from app.domain.models.document import Document, DocumentRaw


class DocumentRepository(ABC):
    @abstractmethod
    async def create(self, document: Document) -> Document:
        ...

    @abstractmethod
    async def get_by_id(self, document_id: str) -> Document | None:
        ...

    @abstractmethod
    async def get_by_project(self, project_id: str) -> list[Document]:
        ...

    @abstractmethod
    async def update(self, document: Document) -> Document:
        ...

    @abstractmethod
    async def delete(self, document_id: str) -> None:
        ...

    @abstractmethod
    async def save_raw(self, raw: DocumentRaw) -> DocumentRaw:
        ...

    @abstractmethod
    async def get_raw(self, document_id: str) -> DocumentRaw | None:
        ...
