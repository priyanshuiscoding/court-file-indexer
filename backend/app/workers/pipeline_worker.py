from __future__ import annotations

import logging
import os
import time

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.batch import Batch
from app.models.document import Document
from app.models.enums import JobType
from app.services.batch_service import BatchService
from app.services.document_service import DocumentService
from app.services.index_pipeline_service import IndexPipelineService
from app.services.job_service import JobService
from app.services.ocr_pipeline_service import OCRPipelineService
from app.services.vector_pipeline_service import VectorPipelineService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

POLL_SECONDS = float(os.getenv("PIPELINE_POLL_SECONDS", "1.0"))
WORKER_STAGE = os.getenv("WORKER_STAGE", JobType.OCR_DOCUMENT.value)


class PipelineWorker:
    def __init__(self) -> None:
        self.job_service = JobService()
        self.document_service = DocumentService()
        self.batch_service = BatchService()
        self.ocr_pipeline_service = OCRPipelineService()
        self.index_pipeline_service = IndexPipelineService()
        self.vector_pipeline_service = VectorPipelineService()
        self.stage = JobType(WORKER_STAGE)

    def run_forever(self) -> None:
        logger.info("starting worker stage=%s", self.stage.value)
        while True:
            processed = self.run_once()
            if not processed:
                time.sleep(POLL_SECONDS)

    def run_once(self) -> bool:
        with SessionLocal() as db:
            job = self.job_service.claim_next_job(db, self.stage)
            if not job:
                db.commit()
                return False

            try:
                document = db.get(Document, job.document_id)
                if document is None:
                    raise RuntimeError(f"document {job.document_id} not found")

                if self.stage == JobType.OCR_DOCUMENT:
                    self._handle_ocr(db, document)
                elif self.stage == JobType.EXTRACT_INDEX:
                    self._handle_index(db, document)
                elif self.stage == JobType.VECTORIZE_DOCUMENT:
                    self._handle_vector(db, document)
                else:
                    raise RuntimeError(f"unsupported stage {self.stage.value}")

                self.job_service.mark_success(db, job)
                if job.batch_id:
                    self.batch_service.refresh_batch_status(db, job.batch_id)
                db.commit()
                return True
            except Exception as exc:
                logger.exception("job failed: %s", exc)
                document = db.get(Document, job.document_id)
                if document:
                    document.status = "FAILED"
                    document.current_step = str(exc)[:120]
                    db.add(document)
                self.job_service.mark_failed(db, job, str(exc))
                if job.batch_id:
                    self.batch_service.refresh_batch_status(db, job.batch_id)
                db.commit()
                return True

    def _handle_ocr(self, db: Session, document: Document) -> None:
        self.document_service.update_status(db, document, status="OCR_PROCESSING", current_step="OCR in progress")
        self.ocr_pipeline_service.process_document(db, document)
        self.document_service.update_status(db, document, status="OCR_DONE", current_step="OCR complete")
        self.job_service.enqueue_job(
            db,
            document_id=document.id,
            batch_id=self._batch_id_from_document(db, document),
            job_type=JobType.EXTRACT_INDEX,
            payload={"document_id": document.id},
            priority=200,
        )

    def _handle_index(self, db: Session, document: Document) -> None:
        self.document_service.update_status(db, document, status="INDEX_PROCESSING", current_step="Index extraction in progress")
        self.index_pipeline_service.process_document(db, document)
        self.document_service.update_status(db, document, status="INDEX_DONE", current_step="Index extraction complete")
        self.job_service.enqueue_job(
            db,
            document_id=document.id,
            batch_id=self._batch_id_from_document(db, document),
            job_type=JobType.VECTORIZE_DOCUMENT,
            payload={"document_id": document.id},
            priority=300,
        )

    def _handle_vector(self, db: Session, document: Document) -> None:
        self.document_service.update_status(db, document, status="VECTORIZING", current_step="Vectorization in progress")
        self.vector_pipeline_service.process_document(db, document)
        self.document_service.update_status(db, document, status="COMPLETED", current_step="Completed")

    def _batch_id_from_document(self, db: Session, document: Document) -> int | None:
        if not document.batch_no:
            return None
        batch = db.query(Batch).filter(Batch.batch_no == document.batch_no).first()
        return batch.id if batch else None
