from app.lib.logger import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, acks_late=True)
def generate_scenarios_task(self, project_id: str, platforms: list[str] | None = None):
    logger.info("Scenario generation started: project=%s platforms=%s", project_id, platforms)
    try:
        from app.dependencies import get_scenario_service
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        scenarios = loop.run_until_complete(
            get_scenario_service().generate_scenarios(project_id, platforms or ["web"])
        )
        loop.close()
        return {"status": "completed", "project_id": project_id, "scenarios_count": len(scenarios)}
    except Exception as e:
        logger.error("Scenario generation failed: %s", e)
        raise self.retry(exc=e, countdown=10 * (self.request.retries + 1))
