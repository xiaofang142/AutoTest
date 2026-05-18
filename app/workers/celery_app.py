from celery import Celery

from app.config import settings

celery_app = Celery(
    "autotest",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.parse_docs",
        "app.workers.gen_scenarios",
        "app.workers.execute_run",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3000,
    worker_max_tasks_per_child=50,
)
