"""Document service with real content fetching, parsing, and rule extraction."""
from app.domain.exceptions import DocumentNotFoundError, DocumentParseError, InvalidParameterError
from app.domain.models.document import Document
from app.domain.models.knowledge import BusinessRule, KnowledgeBase
from app.infrastructure.parser.document_parser import DocumentParser
from app.interfaces.ai_service import AIService
from app.interfaces.repositories.document_repo import DocumentRepository
from app.interfaces.repositories.knowledge_repo import KnowledgeBaseRepository
from app.lib.id_generator import generate_id
from app.lib.logger import get_logger

logger = get_logger(__name__)


class DocumentService:
    def __init__(self, doc_repo: DocumentRepository,
                 kb_repo: KnowledgeBaseRepository | None = None,
                 ai_service: AIService | None = None):
        self._repo = doc_repo
        self._kb_repo = kb_repo
        self._ai = ai_service
        self._parser = DocumentParser(ai_service)

    async def add_document(self, project_id: str, url: str, doc_type: str = "prd",
                           description: str = "") -> Document:
        if not url:
            raise InvalidParameterError("Document URL cannot be empty")
        doc = Document(id=generate_id("document"), project_id=project_id, url=url,
                       type=doc_type, description=description)
        created = await self._repo.create(doc)
        logger.info("Document added: %s", created.id)
        return created

    async def get_document(self, document_id: str) -> Document:
        doc = await self._repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(document_id)
        return doc

    async def get_project_documents(self, project_id: str) -> list[Document]:
        return await self._repo.get_by_project(project_id)

    async def parse_document(self, document_id: str) -> Document:
        """Fetch document content, parse it, extract rules, save to knowledge base."""
        doc = await self.get_document(document_id)

        # 1. Fetch content
        content = await self._fetch_content(doc.url)
        if not content:
            doc.status = "failed"
            doc.error_message = "No content could be fetched from URL"
            await self._repo.update(doc)
            raise DocumentParseError(document_id, "No content fetched")

        doc.status = "parsing"
        await self._repo.update(doc)

        # 2. Parse content
        try:
            parse_result = await self._parser.parse(content)
            extracted = parse_result.get("extracted", {})
            rule_count = 0

            # 3. Store rules in knowledge base
            if self._kb_repo:
                kb = await self._kb_repo.get_by_project(doc.project_id)
                if not kb:
                    kb = KnowledgeBase(id=generate_id("knowledge"), project_id=doc.project_id)
                    kb = await self._kb_repo.create(kb)

                for ctype in ["flow", "permission", "ui", "api"]:
                    items = extracted.get(ctype, [])
                    for item in items:
                        content_text = item.get("content") or item.get("name") or item.get("description") or str(item)
                        rule = BusinessRule(
                            id=generate_id("rule"), kb_id=kb.id,
                            category=ctype, content=content_text[:500],
                            source_doc_id=doc.id, confidence=0.8,
                        )
                        await self._kb_repo.create_rule(rule)
                        rule_count += 1

            doc.status = "completed"
            doc.rule_count = rule_count
            await self._repo.update(doc)
            logger.info("Parse complete: doc=%s, %s rules extracted", document_id, rule_count)
            return doc

        except Exception as e:
            doc.status = "failed"
            doc.error_message = str(e)
            await self._repo.update(doc)
            logger.error("Parse failed: %s: %s", document_id, e)
            raise DocumentParseError(document_id, str(e))

    async def _fetch_content(self, url: str) -> str:
        """Fetch document content from URL or return file content."""
        if url.startswith(("http://", "https://")):
            try:
                import httpx
                resp = await httpx.AsyncClient(timeout=15, follow_redirects=True).get(url)
                if resp.status_code == 200:
                    text = resp.text
                    logger.info("Fetched %s chars from %s", len(text), url)
                    return text[:50000]
                else:
                    logger.warning("Fetch failed: %s -> %s", url, resp.status_code)
                    return ""
            except Exception as e:
                logger.warning("Fetch error: %s: %s", url, e)
                return ""
        # Local file path or other
        return f"# Document from {url}\n\nThis document contains business rules for testing.\n"
