from app.domain.models.document import Document
from app.domain.exceptions import DocumentNotFoundError, InvalidParameterError
from app.interfaces.repositories.document_repo import DocumentRepository
from app.interfaces.ai_service import AIService
from app.lib.id_generator import generate_id
from app.lib.logger import get_logger

logger = get_logger(__name__)


class DocumentService:
    def __init__(self, doc_repo: DocumentRepository, ai_service: AIService | None = None):
        self._repo = doc_repo
        self._ai = ai_service

    async def add_document(self, project_id: str, url: str, doc_type: str = "prd",
                           description: str = "") -> Document:
        if not url:
            raise InvalidParameterError("Document URL cannot be empty")
        doc = Document(
            id=generate_id("document"),
            project_id=project_id,
            url=url,
            type=doc_type,
            description=description,
        )
        created = await self._repo.create(doc)
        logger.info(f"Document added: {created.id}")
        return created

    async def get_document(self, document_id: str) -> Document:
        doc = await self._repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(document_id)
        return doc

    async def get_project_documents(self, project_id: str) -> list[Document]:
        return await self._repo.get_by_project(project_id)

    async def parse_document(self, document_id: str) -> Document:
        doc = await self.get_document(document_id)
        doc.status = "parsing"
        await self._repo.update(doc)
        logger.info(f"Document parse triggered: {document_id}")
        return doc
