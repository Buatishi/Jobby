from celery import Celery
from kombu import Queue

from app.config import settings

celery_app = Celery(
    "jobmatch",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.parsing"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_default_queue="analysis",
    task_queues=(
        Queue("parsing"),
        Queue("analysis"),
        Queue("scraping"),
    ),
    task_routes={
        "app.tasks.parsing.parse_cv_task": {"queue": "parsing"},
    },
    broker_transport_options={"visibility_timeout": 3600},
    result_backend_transport_options={"visibility_timeout": 3600},
)

__all__ = ["celery_app"]
