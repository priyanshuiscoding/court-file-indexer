from __future__ import annotations

import logging

from app.db.session import SessionLocal
from app.services.external_fetch_service import ExternalFetchService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="integration.fetch_external_batch", bind=True)
def fetch_external_batch(self, overwrite: bool = False, limit: int | None = None):
    db = SessionLocal()
    try:
        service = ExternalFetchService()
        return service.fetch_and_ingest(db, overwrite=overwrite, limit=limit)
    except Exception as exc:
        logger.exception("External fetch task failed")
        return {
            "ok": False,
            "message": f"external fetch failed: {str(exc)}",
            "summary": {
                "total_received": 0,
                "total_processed": 0,
                "total_queued": 0,
                "total_skipped": 0,
                "total_failed": 1,
            },
            "items": [],
        }
    finally:
        db.close()
