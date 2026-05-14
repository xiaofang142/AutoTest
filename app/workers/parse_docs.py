from app.workers.celery_app import celery_app
from app.lib.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def parse_documents_task(self, project_id: str, document_ids: list[str] | None = None):
    logger.info(f"Document parse task started: project={project_id}")
    return {"status": "completed", "project_id": project_id, "rules_count": 0}
