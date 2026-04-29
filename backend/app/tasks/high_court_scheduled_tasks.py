from __future__ import annotations

import logging

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.high_court_completion_service import HighCourtCompletionService
from app.services.high_court_import_service import HighCourtImportService
from app.services.high_court_import_status_sync_service import HighCourtImportStatusSyncService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(name="high_court.import_pending_scheduled")
def import_pending_scheduled(force: bool = False) -> dict:
    if not force and not settings.HC_SCHEDULER_ENABLED:
        return {"ok": False, "skipped": True, "reason": "HC scheduler disabled"}

    db = SessionLocal()
    try:
        service = HighCourtImportService()
        result = service.import_pending(db, limit=settings.HC_SCHEDULER_IMPORT_LIMIT)
        data = result.model_dump() if hasattr(result, "model_dump") else result
        logger.info("High Court import task completed: %s", data)
        return data
    except Exception as exc:
        logger.exception("High Court import task failed")
        return {"ok": False, "error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="high_court.sync_status_scheduled")
def sync_status_scheduled(force: bool = False) -> dict:
    if not force and not settings.HC_SCHEDULER_ENABLED:
        return {"ok": False, "skipped": True, "reason": "HC scheduler disabled"}

    db = SessionLocal()
    try:
        service = HighCourtImportStatusSyncService()
        result = service.sync_all_linked_jobs(db, limit=1000)
        logger.info("High Court sync task completed: %s", result)
        return result
    except Exception as exc:
        logger.exception("High Court sync task failed")
        return {"ok": False, "error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="high_court.mark_completed_scheduled")
def mark_completed_scheduled(force: bool = False) -> dict:
    if not force and not settings.HC_SCHEDULER_ENABLED:
        return {"ok": False, "skipped": True, "reason": "HC scheduler disabled"}
    if not settings.HC_SCHEDULER_MARK_COMPLETE_ENABLED:
        return {"ok": False, "skipped": True, "reason": "HC scheduler mark-complete disabled"}
    if not settings.HC_MYSQL_MARK_COMPLETE_ENABLED:
        return {"ok": False, "skipped": True, "reason": "External MySQL mark-complete disabled"}

    db = SessionLocal()
    try:
        service = HighCourtCompletionService()
        result = service.mark_completed_ready_jobs(
            db,
            limit=settings.HC_SCHEDULER_MARK_COMPLETE_LIMIT,
        )
        logger.info("High Court mark-completed task finished: %s", result)
        return result
    except Exception as exc:
        logger.exception("High Court mark-completed task failed")
        return {"ok": False, "error": str(exc)}
    finally:
        db.close()
