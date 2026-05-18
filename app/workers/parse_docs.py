from app.lib.logger import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, acks_late=True)
def parse_documents_task(self, project_id: str, document_ids: list[str] | None = None):
    logger.info("Document parse task started: project=%s docs=%s", project_id, document_ids)
    try:
        from app.dependencies import get_document_service
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            get_document_service().parse_documents(project_id, document_ids or [])
        )
        loop.close()
        return {"status": "completed", "project_id": project_id, "rules_count": result}
    except Exception as e:
        logger.error("Document parse failed: %s", e)
        raise self.retry(exc=e, countdown=10 * (self.request.retries + 1))
