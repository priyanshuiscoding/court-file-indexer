from celery import Celery

from app.core.config import get_settings

settings = get_settings()

FAST_INDEX_QUEUE = "fast_index_q"
FULL_PROCESS_QUEUE = "full_process_q"

celery_app = Celery(
    "court_indexer",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.document_tasks",
        "app.tasks.ops_tasks",
        "app.tasks.external_fetch_tasks",
    ],
)

celery_app.conf.task_track_started = True
celery_app.conf.result_expires = 3600
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.task_default_queue = FULL_PROCESS_QUEUE
celery_app.conf.task_routes = {
    "document.fast_index": {"queue": FAST_INDEX_QUEUE},
    "document.full_process": {"queue": FULL_PROCESS_QUEUE},
    "queue.monitor_and_recover": {"queue": FAST_INDEX_QUEUE},
    "ops.ping": {"queue": FAST_INDEX_QUEUE},
    "integration.fetch_external_batch": {"queue": FAST_INDEX_QUEUE},
}

celery_app.conf.beat_schedule = {
    "queue-monitor-and-recover-every-minute": {
        "task": "queue.monitor_and_recover",
        "schedule": 60.0,
    },
    # Optional periodic external pull; disabled by default via EXTERNAL_FETCH_ENABLED.
    # Keep manual trigger as primary mode unless explicitly enabled in deployment.
    # "integration-fetch-external-every-5-minutes": {
    #     "task": "integration.fetch_external_batch",
    #     "schedule": 300.0,
    # },
}
