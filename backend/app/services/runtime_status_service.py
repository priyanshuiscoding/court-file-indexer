from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.document import Document
from app.schemas.ops_models import BatchRuntimeStatus, DocumentRuntimeStatus, StageCounts


class RuntimeStatusService:
    def _progress_from_status(self, status: str) -> int:
        s = (status or '').upper()
        if s in {'QUEUED', 'UPLOADED'}:
            return 5
        if s == 'OCR_PROCESSING':
            return 20
        if s in {'OCR_DONE', 'FAST_INDEX_RUNNING'}:
            return 45
        if s == 'INDEX_PROCESSING':
            return 60
        if s in {'INDEX_DONE', 'INDEX_READY', 'INDEX_PARSED'}:
            return 75
        if s == 'VECTORIZING':
            return 90
        if s in {'CHAT_READY', 'COMPLETED', 'APPROVED', 'REVIEW_REQUIRED'}:
            return 100
        if s in {'FAILED', 'PARTIAL_FAILED', 'CANCELLED'}:
            return 100
        return 0

    def get_batch_runtime_status(self, db: Session, batch_id: int) -> BatchRuntimeStatus:
        batch = db.get(Batch, batch_id)
        if not batch:
            raise ValueError('Batch not found')

        docs = (
            db.query(Document)
            .filter(Document.batch_no == batch.batch_no)
            .order_by(Document.id.asc())
            .all()
        )

        counts = StageCounts()
        items: list[DocumentRuntimeStatus] = []

        for doc in docs:
            status = (doc.status or '').upper()
            if status in {'QUEUED', 'UPLOADED'}:
                counts.queued += 1
            elif status in {'OCR_PROCESSING', 'FAST_INDEX_RUNNING', 'OCR_DONE'}:
                counts.ocr_processing += 1
            elif status in {'INDEX_PROCESSING', 'INDEX_DONE', 'INDEX_READY', 'INDEX_PARSED'}:
                counts.index_processing += 1
            elif status in {'VECTORIZING'}:
                counts.vectorizing += 1
            elif status in {'CHAT_READY', 'COMPLETED', 'APPROVED', 'REVIEW_REQUIRED'}:
                counts.completed += 1
            elif status in {'FAILED', 'PARTIAL_FAILED', 'CANCELLED'}:
                counts.failed += 1

            items.append(
                DocumentRuntimeStatus(
                    document_id=doc.id,
                    status=doc.status,
                    current_stage=getattr(doc, 'current_step', None),
                    progress_percent=self._progress_from_status(doc.status),
                    error_message=(doc.current_step if doc.status in {'FAILED', 'PARTIAL_FAILED', 'CANCELLED'} else None),
                )
            )

        return BatchRuntimeStatus(
            batch_id=batch.id,
            status='processing' if counts.ocr_processing + counts.index_processing + counts.vectorizing > 0 else 'queued',
            counts=counts,
            documents=items,
        )