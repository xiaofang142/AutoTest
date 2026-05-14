from app.workers.celery_app import celery_app
from app.lib.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, track_started=True)
def execute_run_task(self, run_id: str, platform: str = "web"):
    logger.info(f"Run execution task started: run_id={run_id}, platform={platform}")
    return {"status": "completed", "run_id": run_id}
