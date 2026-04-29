from __future__ import annotations

import threading
import time

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.queue_item import QueueItem
from app.pipelines.fast_index_pipeline import FastIndexPipeline
from app.pipelines.ocr_pipeline import OCRPipeline
from app.pipelines.vector_pipeline import VectorPipeline
from app.pipelines.verification_pipeline import VerificationPipeline
from app.services.document_service import DocumentService
from app.services.high_court_import_status_sync_service import HighCourtImportStatusSyncService
from app.services.queue_service import QueueService
from app.tasks.celery_app import celery_app

settings = get_settings()
queue_service = QueueService()
high_court_sync_service = HighCourtImportStatusSyncService()

# INDEX_READY is an intermediate fast-stage status, not terminal.
TERMINAL_DOC_STATUSES = {"CHAT_READY", "COMPLETED", "APPROVED", "REVIEW_REQUIRED"}

HEARTBEAT_TOUCH_SECONDS = max(15, min(30, int(settings.TASK_HEARTBEAT_SECONDS or 30)))
QUEUE_STALE_SECONDS = {
    "FAST_INDEX": 300,   # 5 min without heartbeat
    "FULL_PROCESS": 900, # 15 min without heartbeat
}
QUEUE_MAX_ATTEMPTS = {
    "FAST_INDEX": 2,
    "FULL_PROCESS": 2,
}


def _sync_high_court_import_job(db, doc: Document | None, error_message: str | None = None) -> None:
    if not doc:
        return
    try:
        high_court_sync_service.sync_document(db, doc, commit=False, error_message=error_message)
        db.commit()
    except Exception:
        pass


class _QueueHeartbeat:
    def __init__(self, task_id: str, interval_seconds: int = HEARTBEAT_TOUCH_SECONDS) -> None:
        self.task_id = task_id
        self.interval_seconds = max(10, interval_seconds)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self):
        def _runner():
            while not self._stop.wait(self.interval_seconds):
                db = SessionLocal()
                try:
                    queue_service.touch(db, self.task_id)
                except Exception:
                    pass
                finally:
                    db.close()

        self._thread = threading.Thread(target=_runner, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)


def _has_active_fast_index(db) -> bool:
    active = queue_service.list_active(db)
    return any(item.queue_name == "FAST_INDEX" for item in active)


def _has_active_for_document(db, document_id: int) -> bool:
    return queue_service.has_active_for_document(db, document_id)


def _enqueue_fast_task(db, document_id: int):
    task = fast_index.delay(document_id)
    queue_service.enqueue_task(
        db,
        queue_name="FAST_INDEX",
        document_id=document_id,
        task_id=task.id,
        priority=10,
    )
    return task


def _enqueue_full_task(db, document_id: int):
    task = full_process.delay(document_id)
    queue_service.enqueue_task(
        db,
        queue_name="FULL_PROCESS",
        document_id=document_id,
        task_id=task.id,
        priority=50,
    )
    return task


def _pick_next_fast_candidate(db, preferred_batch: str | None = None) -> Document | None:
    if preferred_batch:
        stmt = (
            select(Document)
            .where(Document.batch_no == preferred_batch, Document.status == "UPLOADED")
            .order_by(Document.created_at.asc())
        )
        for doc in db.scalars(stmt).all():
            if not _has_active_for_document(db, doc.id):
                return doc

    stmt = select(Document).where(Document.status == "UPLOADED").order_by(Document.created_at.asc())
    for doc in db.scalars(stmt).all():
        if not _has_active_for_document(db, doc.id):
            return doc

    return None


def _start_next_fast_if_possible(db, preferred_batch: str | None = None) -> dict | None:
    if _has_active_fast_index(db):
        return None

    next_doc = _pick_next_fast_candidate(db, preferred_batch=preferred_batch)
    if not next_doc:
        return None

    task = _enqueue_fast_task(db, next_doc.id)
    return {"document_id": next_doc.id, "task_id": task.id}


def _batch_has_pending_fast_candidates(db, batch_no: str) -> bool:
    stmt = select(Document).where(Document.batch_no == batch_no, Document.status == "UPLOADED")
    for doc in db.scalars(stmt).all():
        if not _has_active_for_document(db, doc.id):
            return True
    return False


def _enqueue_batch_full_process_when_ready(db, batch_no: str) -> int:
    if _has_active_fast_index(db):
        return 0

    if _batch_has_pending_fast_candidates(db, batch_no):
        return 0

    queued = 0
    stmt = (
        select(Document)
        .where(Document.batch_no == batch_no, Document.status == "INDEX_READY")
        .order_by(Document.created_at.asc())
    )
    for doc in db.scalars(stmt).all():
        if _has_active_for_document(db, doc.id):
            continue
        _enqueue_full_task(db, doc.id)
        queued += 1
    return queued


def _revoke_worker_task(task_id: str | None, terminate: bool = True) -> None:
    if not task_id:
        return
    try:
        celery_app.control.revoke(task_id, terminate=terminate)
    except Exception:
        pass


def _recover_stale_row(db, row: QueueItem) -> dict:
    doc = DocumentService().get_document(db, row.document_id)
    queue_name = row.queue_name
    attempt_count = queue_service.count_attempts_for_document_queue(db, row.document_id, queue_name)
    max_attempts = QUEUE_MAX_ATTEMPTS.get(queue_name, 1)

    _revoke_worker_task(row.worker_id, terminate=True)
    queue_service.mark_terminal(db, row.worker_id, "FAILED")

    if not doc:
        return {
            "document_id": row.document_id,
            "queue_name": queue_name,
            "action": "marked_failed_missing_document",
        }

    if doc.status in {"STOPPED", "CANCELLED"}:
        return {
            "document_id": row.document_id,
            "queue_name": queue_name,
            "action": "ignored_stopped_document",
        }

    if queue_name == "FAST_INDEX":
        if attempt_count < max_attempts:
            doc.status = "UPLOADED"
            doc.current_step = f"Auto-retrying FAST_INDEX ({attempt_count}/{max_attempts})"
            db.add(doc)
            db.commit()
            _sync_high_court_import_job(db, doc)

            _start_next_fast_if_possible(db, preferred_batch=doc.batch_no)
            return {
                "document_id": doc.id,
                "queue_name": queue_name,
                "action": "retried_fast_index",
                "attempt_count": attempt_count,
            }

        doc.status = "REVIEW_REQUIRED"
        doc.current_step = "Auto-stopped after repeated stale FAST_INDEX"
        db.add(doc)
        db.commit()
        _sync_high_court_import_job(db, doc)

        _start_next_fast_if_possible(db, preferred_batch=doc.batch_no)
        if doc.batch_no:
            _enqueue_batch_full_process_when_ready(db, doc.batch_no)

        return {
            "document_id": doc.id,
            "queue_name": queue_name,
            "action": "moved_to_review_required",
            "attempt_count": attempt_count,
        }

    if queue_name == "FULL_PROCESS":
        if attempt_count < max_attempts:
            doc.status = "INDEX_READY"
            doc.current_step = f"Auto-retrying FULL_PROCESS ({attempt_count}/{max_attempts})"
            db.add(doc)
            db.commit()
            _sync_high_court_import_job(db, doc)

            if doc.batch_no:
                _enqueue_batch_full_process_when_ready(db, doc.batch_no)
            else:
                if not _has_active_for_document(db, doc.id):
                    _enqueue_full_task(db, doc.id)

            return {
                "document_id": doc.id,
                "queue_name": queue_name,
                "action": "retried_full_process",
                "attempt_count": attempt_count,
            }

        doc.status = "FAILED"
        doc.current_step = "Auto-stopped after repeated stale FULL_PROCESS"
        db.add(doc)
        db.commit()
        _sync_high_court_import_job(db, doc, error_message=doc.current_step)

        return {
            "document_id": doc.id,
            "queue_name": queue_name,
            "action": "marked_failed_after_retries",
            "attempt_count": attempt_count,
        }

    return {
        "document_id": doc.id,
        "queue_name": queue_name,
        "action": "marked_failed_unknown_queue",
        "attempt_count": attempt_count,
    }


def enqueue_document_pipeline(db, document_id: int) -> dict:
    doc = DocumentService().get_document(db, document_id)
    if not doc:
        return {"ok": False, "reason": "not_found"}

    if doc.status in TERMINAL_DOC_STATUSES:
        return {
            "ok": False,
            "reason": "already_completed",
            "message": "Indexing is already completed for this PDF.",
        }

    queue_service.cancel_stale_for_document(db, document_id, stale_seconds=600)

    active = queue_service.active_for_document(db, document_id)
    if active:
        return {
            "ok": False,
            "reason": "already_running",
            "message": "Indexing is already running for this PDF.",
            "active_jobs": [
                {
                    "id": row.id,
                    "queue_name": row.queue_name,
                    "status": row.status,
                    "task_id": row.worker_id,
                }
                for row in active
            ],
        }

    doc.status = "UPLOADED"
    doc.current_step = "Queued for indexing"
    db.add(doc)
    db.commit()
    _sync_high_court_import_job(db, doc)

    if _has_active_fast_index(db):
        return {
            "ok": True,
            "queued": True,
            "message": "Queued for FAST_INDEX; will start after current FAST task finishes.",
        }

    task = _enqueue_fast_task(db, document_id)
    return {"ok": True, "fast_task_id": task.id}


@celery_app.task(name="document.fast_index", bind=True)
def fast_index(self, document_id: int):
    db = SessionLocal()
    try:
        queue_service.mark_started(db, self.request.id)

        doc = DocumentService().get_document(db, document_id)
        if not doc:
            queue_service.mark_terminal(db, self.request.id, "FAILED")
            return {"ok": False, "error": "Document not found"}

        if doc.status in {"STOPPED", "CANCELLED"}:
            queue_service.mark_terminal(db, self.request.id, "CANCELLED")
            _start_next_fast_if_possible(db, preferred_batch=doc.batch_no)
            return {"ok": False, "cancelled": True}

        with _QueueHeartbeat(self.request.id):
            result = FastIndexPipeline().run(db, doc)

        if result.get("rows", 0) <= 0:
            _sync_high_court_import_job(db, doc)
            queue_service.mark_terminal(db, self.request.id, "FAILED")
            _start_next_fast_if_possible(db, preferred_batch=doc.batch_no)
            if doc.batch_no:
                _enqueue_batch_full_process_when_ready(db, doc.batch_no)
            return {"ok": False, "error": "No index rows extracted"}

        if not doc.batch_no:
            has_active_full = any(
                item.queue_name == "FULL_PROCESS"
                for item in queue_service.active_for_document(db, document_id)
            )
            if not has_active_full and doc.status not in {"STOPPED", "CANCELLED"}:
                _enqueue_full_task(db, document_id)

        queue_service.mark_terminal(db, self.request.id, "COMPLETED")

        _start_next_fast_if_possible(db, preferred_batch=doc.batch_no)

        if doc.batch_no:
            _enqueue_batch_full_process_when_ready(db, doc.batch_no)

        return result
    except Exception as exc:
        doc = DocumentService().get_document(db, document_id)
        if doc:
            doc.status = "FAILED"
            doc.current_step = str(exc)[:120]
            db.add(doc)
            db.commit()
            _sync_high_court_import_job(db, doc, error_message=doc.current_step)
        queue_service.mark_terminal(db, self.request.id, "FAILED")
        if doc and doc.batch_no:
            _start_next_fast_if_possible(db, preferred_batch=doc.batch_no)
        else:
            _start_next_fast_if_possible(db)
        raise
    finally:
        db.close()


@celery_app.task(name="document.full_process", bind=True)
def full_process(self, document_id: int):
    db = SessionLocal()
    try:
        queue_service.mark_started(db, self.request.id)

        doc = DocumentService().get_document(db, document_id)
        if not doc:
            queue_service.mark_terminal(db, self.request.id, "FAILED")
            return {"ok": False, "error": "Document not found"}

        if doc.status in {"STOPPED", "CANCELLED"}:
            queue_service.mark_terminal(db, self.request.id, "CANCELLED")
            return {"ok": False, "cancelled": True}

        with _QueueHeartbeat(self.request.id):
            pages = OCRPipeline().run_full(db, doc)
            queue_service.touch(db, self.request.id)

            VectorPipeline().run(db, doc, pages)
            queue_service.touch(db, self.request.id)

            VerificationPipeline().run(db, doc, [], pages)
            queue_service.touch(db, self.request.id)

        doc.status = "CHAT_READY"
        doc.current_step = "Auto-approved"
        db.add(doc)
        db.commit()
        _sync_high_court_import_job(db, doc)

        queue_service.mark_terminal(db, self.request.id, "COMPLETED")
        return {"ok": True}
    except Exception as exc:
        doc = DocumentService().get_document(db, document_id)
        if doc:
            doc.status = "FAILED"
            doc.current_step = str(exc)[:120]
            db.add(doc)
            db.commit()
            _sync_high_court_import_job(db, doc, error_message=doc.current_step)
        queue_service.mark_terminal(db, self.request.id, "FAILED")
        raise
    finally:
        db.close()


@celery_app.task(name="queue.monitor_and_recover", bind=True)
def monitor_and_recover(self):
    db = SessionLocal()
    try:
        recovered: list[dict] = []
        active_rows = queue_service.list_active(db)

        for row in active_rows:
            stale_seconds = QUEUE_STALE_SECONDS.get(row.queue_name, int(settings.STUCK_TASK_SECONDS or 900))
            if row.heartbeat_at is None:
                is_stale = True
            else:
                age = (time.time() - row.heartbeat_at.timestamp())
                is_stale = age >= stale_seconds

            if not is_stale:
                continue

            recovered.append(_recover_stale_row(db, row))

        # After cleanup, keep FAST queue moving.
        _start_next_fast_if_possible(db)

        return {
            "ok": True,
            "recovered_count": len(recovered),
            "items": recovered,
        }
    finally:
        db.close()
