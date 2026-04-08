from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.document import Document
from app.services.queue_service import QueueService
from app.tasks.celery_app import celery_app
from app.tasks.document_tasks import enqueue_document_pipeline, full_process

router = APIRouter(prefix='/retries', tags=['retries'])
queue_service = QueueService()


@router.post('/documents/{document_id}')
def retry_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail='Document not found')

    active = queue_service.mark_cancelled_for_document(db, document_id)
    for row in active:
        if row.worker_id:
            celery_app.control.revoke(row.worker_id, terminate=True)

    doc.status = 'UPLOADED'
    doc.current_step = 'Retry requested'
    db.add(doc)
    db.commit()

    result = enqueue_document_pipeline(db, document_id)
    if not result.get('ok'):
        return {
            'ok': False,
            'message': result.get('message', 'Could not requeue document'),
            'document_id': document_id,
        }

    return {
        'ok': True,
        'message': 'Document requeued from fast stage',
        'document_id': document_id,
        **result,
    }


@router.post('/documents/{document_id}/stage/{stage_name}')
def retry_stage(document_id: int, stage_name: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail='Document not found')

    stage = stage_name.strip().lower()
    if stage not in {'ocr', 'index', 'vector'}:
        raise HTTPException(status_code=400, detail='Invalid stage')

    active = queue_service.mark_cancelled_for_document(db, document_id)
    for row in active:
        if row.worker_id:
            celery_app.control.revoke(row.worker_id, terminate=True)

    if stage == 'ocr':
        doc.status = 'UPLOADED'
        doc.current_step = 'OCR stage retry requested'
        db.add(doc)
        db.commit()
        result = enqueue_document_pipeline(db, document_id)
        if not result.get('ok'):
            return {
                'ok': False,
                'message': result.get('message', 'Could not requeue stage'),
                'document_id': document_id,
                'stage': stage,
            }
        return {'ok': True, 'message': 'Stage requeued: ocr', 'document_id': document_id, 'stage': stage, **result}

    # For index/vector retries in current Celery flow, FULL_PROCESS is the safe resume path.
    doc.current_step = f'{stage.upper()} stage retry requested'
    if doc.status in {'FAILED', 'STOPPED', 'CANCELLED'}:
        doc.status = 'INDEX_READY'
    db.add(doc)
    db.commit()

    task = full_process.delay(document_id)
    queue_service.enqueue_task(
        db,
        queue_name='FULL_PROCESS',
        document_id=document_id,
        task_id=task.id,
        priority=50,
    )

    return {
        'ok': True,
        'message': f'Stage requeued: {stage}',
        'document_id': document_id,
        'stage': stage,
        'task_id': task.id,
    }