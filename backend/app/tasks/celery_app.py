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
    ],
)

celery_app.conf.task_track_started = True
celery_app.conf.result_expires = 3600
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.task_default_queue = FULL_PROCESS_QUEUE
celery_app.conf.task_routes = {
    "document.fast_index": {"queue": FAST_INDEX_QUEUE},
    "document.full_process": {"queue": FULL_PROCESS_QUEUE},
    "ops.ping": {"queue": FAST_INDEX_QUEUE},
}
