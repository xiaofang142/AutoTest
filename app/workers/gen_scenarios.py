from app.workers.celery_app import celery_app
from app.lib.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def generate_scenarios_task(self, project_id: str, platforms: list[str] | None = None):
    logger.info(f"Scenario generation task started: project={project_id}")
    return {"status": "completed", "project_id": project_id, "scenarios_count": 0}
