from app.lib.logger import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, acks_late=True)
def execute_run_task(self, run_id: str, platform: str = "web"):
    logger.info("Run execution started: run_id=%s platform=%s", run_id, platform)
    try:
        from app.dependencies import get_run_service
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            get_run_service().execute_run(run_id, platform)
        )
        loop.close()
        return {"status": "completed", "run_id": run_id, "result": result}
    except Exception as e:
        logger.error("Run execution failed: %s", e)
        raise self.retry(exc=e, countdown=10 * (self.request.retries + 1))
