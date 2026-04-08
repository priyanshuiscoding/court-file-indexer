from datetime import datetime, timezone
import os

from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.document import Document
from app.models.index_row import IndexRow
from app.schemas.ops import OpsQueueItemOut, OpsStatusOut, QueueActionResponse
from app.services.queue_service import QueueService
from app.tasks.celery_app import celery_app
from app.tasks.document_tasks import enqueue_document_pipeline

router = APIRouter(prefix="/ops", tags=["ops"])
queue_service = QueueService()
STUCK_SECONDS = int(os.getenv("QUEUE_STUCK_SECONDS", "600"))


@router.get("/status", response_model=OpsStatusOut)
def ops_status(db: Session = Depends(get_db)):
    indexed_count = db.query(func.count(Document.id)).filter(Document.status.in_(["INDEX_PARSED", "APPROVED", "REVIEW_REQUIRED", "INDEX_READY", "CHAT_READY"])) .scalar() or 0
    vectorized_count = db.query(func.count(Document.id)).filter(Document.is_vectorized.is_(True)).scalar() or 0
    pending_queue_count = db.query(func.count(Document.id)).filter(Document.status.in_(["UPLOADED", "OCR_RUNNING", "INDEX_SEARCH_RUNNING", "VECTORIZING", "VERIFYING", "FAST_INDEX_RUNNING"])) .scalar() or 0
    review_queue_count = db.query(func.count(IndexRow.id)).filter(IndexRow.status == "REVIEW").scalar() or 0
    failed_count = db.query(func.count(Document.id)).filter(Document.status == "FAILED").scalar() or 0
    return OpsStatusOut(
        indexed_count=indexed_count,
        vectorized_count=vectorized_count,
        pending_queue_count=pending_queue_count,
        review_queue_count=review_queue_count,
        failed_count=failed_count,
    )


@router.get("/queue/active", response_model=list[OpsQueueItemOut])
def active_queue(db: Session = Depends(get_db)):
    rows = queue_service.list_active(db)
    doc_ids = list({row.document_id for row in rows})
    docs = db.query(Document).filter(Document.id.in_(doc_ids)).all() if doc_ids else []
    doc_map = {d.id: d for d in docs}

    now = datetime.now(timezone.utc)
    items: list[OpsQueueItemOut] = []

    for row in rows:
        heartbeat = row.heartbeat_at
        stale_seconds = None
        is_stuck = False
        if heartbeat:
            hb = heartbeat.replace(tzinfo=timezone.utc) if heartbeat.tzinfo is None else heartbeat.astimezone(timezone.utc)
            stale_seconds = int((now - hb).total_seconds())
            is_stuck = stale_seconds >= STUCK_SECONDS
        else:
            is_stuck = True

        doc = doc_map.get(row.document_id)
        items.append(
            OpsQueueItemOut(
                id=row.id,
                queue_name=row.queue_name,
                document_id=row.document_id,
                document_name=(doc.file_name if doc else None),
                document_status=(doc.status if doc else None),
                status=row.status,
                priority=row.priority,
                attempts=row.attempts,
                task_id=row.worker_id,
                heartbeat_at=row.heartbeat_at,
                stale_seconds=stale_seconds,
                is_stuck=is_stuck,
                created_at=row.created_at,
            )
        )

    return items


@router.post("/documents/{document_id}/stop", response_model=QueueActionResponse)
def stop_document_processing(document_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    rows = queue_service.mark_cancelled_for_document(db, document_id)
    for row in rows:
        if row.worker_id:
            celery_app.control.revoke(row.worker_id, terminate=True)

    doc.status = "STOPPED"
    doc.current_step = "Stopped by operator"
    db.add(doc)
    db.commit()

    return QueueActionResponse(message="Stopped document processing", affected=len(rows))


@router.post("/documents/{document_id}/restart", response_model=QueueActionResponse)
def restart_document_processing(document_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    old_rows = queue_service.mark_cancelled_for_document(db, document_id)
    for row in old_rows:
        if row.worker_id:
            celery_app.control.revoke(row.worker_id, terminate=True)

    doc.status = "UPLOADED"
    doc.current_step = "Restart requested"
    db.add(doc)
    db.commit()

    enqueue_result = enqueue_document_pipeline(db, document_id)
    if not enqueue_result.get("ok"):
        return QueueActionResponse(ok=False, message=enqueue_result.get("message", "Could not restart"), affected=0)
    return QueueActionResponse(message="Restarted document processing", affected=1)


@router.post("/queue/clear-pending", response_model=QueueActionResponse)
def clear_pending_queue(db: Session = Depends(get_db)):
    active_rows = queue_service.list_active(db)
    for row in active_rows:
        if row.status == "PENDING" and row.worker_id:
            celery_app.control.revoke(row.worker_id, terminate=False)

    cleared = queue_service.clear_pending(db)
    return QueueActionResponse(message="Pending queue cleared", affected=cleared)
