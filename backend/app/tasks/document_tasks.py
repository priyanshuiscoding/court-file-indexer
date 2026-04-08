from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.document import Document
from app.pipelines.fast_index_pipeline import FastIndexPipeline
from app.pipelines.ocr_pipeline import OCRPipeline
from app.pipelines.vector_pipeline import VectorPipeline
from app.pipelines.verification_pipeline import VerificationPipeline
from app.services.document_service import DocumentService
from app.services.queue_service import QueueService
from app.tasks.celery_app import celery_app

queue_service = QueueService()

# INDEX_READY is an intermediate fast-stage status, not terminal.
TERMINAL_DOC_STATUSES = {"CHAT_READY", "COMPLETED", "APPROVED", "REVIEW_REQUIRED"}


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
    # Prefer same batch to keep uploads moving predictably.
    if preferred_batch:
        stmt = (
            select(Document)
            .where(Document.batch_no == preferred_batch, Document.status == "UPLOADED")
            .order_by(Document.created_at.asc())
        )
        for doc in db.scalars(stmt).all():
            if not _has_active_for_document(db, doc.id):
                return doc

    # Fallback: any queued document.
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
    # Delay FULL_PROCESS until FAST queue is drained.
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

    # Auto-recover stale jobs for this document so Start can resume safely.
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

    # Reset state for clean retry from UI Start button.
    doc.status = "UPLOADED"
    doc.current_step = "Queued for indexing"
    db.add(doc)
    db.commit()

    # Only one active FAST_INDEX at a time across the system.
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

        result = FastIndexPipeline().run(db, doc)

        if result.get("rows", 0) <= 0:
            queue_service.mark_terminal(db, self.request.id, "FAILED")
            _start_next_fast_if_possible(db, preferred_batch=doc.batch_no)
            if doc.batch_no:
                _enqueue_batch_full_process_when_ready(db, doc.batch_no)
            return {"ok": False, "error": "No index rows extracted"}

        # For non-batch docs, keep immediate full processing.
        if not doc.batch_no:
            has_active_full = any(item.queue_name == "FULL_PROCESS" for item in queue_service.active_for_document(db, document_id))
            if not has_active_full and doc.status not in {"STOPPED", "CANCELLED"}:
                _enqueue_full_task(db, document_id)

        queue_service.mark_terminal(db, self.request.id, "COMPLETED")

        # Start next queued FAST doc now that current fast has completed.
        _start_next_fast_if_possible(db, preferred_batch=doc.batch_no)

        # Batch mode: enqueue FULL_PROCESS only when batch FAST candidates are drained.
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

        pages = OCRPipeline().run_full(db, doc)
        queue_service.touch(db, self.request.id)

        VectorPipeline().run(db, doc, pages)
        queue_service.touch(db, self.request.id)

        VerificationPipeline().run(db, doc, [], pages)
        queue_service.touch(db, self.request.id)

        doc.status = "CHAT_READY"
        db.commit()

        queue_service.mark_terminal(db, self.request.id, "COMPLETED")
        return {"ok": True}
    except Exception as exc:
        doc = DocumentService().get_document(db, document_id)
        if doc:
            doc.status = "FAILED"
            doc.current_step = str(exc)[:120]
            db.add(doc)
            db.commit()
        queue_service.mark_terminal(db, self.request.id, "FAILED")
        raise
    finally:
        db.close()
