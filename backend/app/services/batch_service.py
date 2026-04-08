from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.document import Document
from app.models.enums import BatchStatus, DocumentStatus, JobType
from app.schemas.batch_models import BatchCreateResponse, BatchDetailResponse, DocumentQueueItem
from app.services.document_service import DocumentService
from app.services.job_service import JobService
from app.services.pdf_service import PdfService
from app.services.storage_service import StorageService


class BatchService:
    def __init__(self) -> None:
        self.storage_service = StorageService()
        self.pdf_service = PdfService()
        self.document_service = DocumentService()
        self.job_service = JobService()

    def _make_batch_no(self, name: str | None = None) -> str:
        base = (name or "BATCH").strip().replace(" ", "_")[:60] or "BATCH"
        return f"{base}_{uuid4().hex[:8]}"

    def create_batch(self, db: Session, name: str | None = None) -> Batch:
        batch = Batch(
            batch_no=self._make_batch_no(name),
            total_files=0,
            queued_files=0,
            processing_files=0,
            completed_files=0,
            failed_files=0,
        )
        db.add(batch)
        db.flush()
        return batch

    def upload_documents(self, db: Session, files: list[UploadFile], batch_name: str | None = None) -> BatchCreateResponse:
        batch = self.create_batch(db, batch_name)

        total = 0
        for file in files:
            stored_path = self.storage_service.save_upload(file)
            page_count = self.pdf_service.count_pages(stored_path)

            doc = self.document_service.create_document(
                db,
                file_name=file.filename or "document.pdf",
                original_path=stored_path,
                page_count=page_count,
                cnr_number=None,
                batch_no=batch.batch_no,
                status="QUEUED",
                current_step="Queued for OCR",
                commit=False,
            )
            self.job_service.enqueue_job(
                db,
                document_id=doc.id,
                batch_id=batch.id,
                job_type=JobType.OCR_DOCUMENT,
                payload={"document_id": doc.id},
                priority=100,
            )
            total += 1

        batch.total_files = total
        batch.queued_files = total
        db.commit()

        return BatchCreateResponse(
            batch_id=batch.id,
            name=batch.batch_no,
            total_documents=batch.total_files,
            status=BatchStatus.QUEUED,
        )

    def start_batch(self, db: Session, batch_id: int) -> BatchDetailResponse:
        batch = db.get(Batch, batch_id)
        if not batch:
            raise ValueError("Batch not found")

        self.refresh_batch_status(db, batch_id)
        db.commit()
        return self.get_batch_detail(db, batch_id)

    def get_batch_detail(self, db: Session, batch_id: int) -> BatchDetailResponse:
        batch = db.get(Batch, batch_id)
        if not batch:
            raise ValueError("Batch not found")

        docs = (
            db.query(Document)
            .filter(Document.batch_no == batch.batch_no)
            .order_by(Document.id.asc())
            .all()
        )
        status = self._derive_batch_status(docs)

        items = [
            DocumentQueueItem(
                id=d.id,
                filename=d.file_name,
                page_count=d.page_count,
                status=d.status,
                progress_percent=self._status_to_progress(d.status),
                error_message=(d.current_step if d.status == "FAILED" else None),
            )
            for d in docs
        ]

        return BatchDetailResponse(
            id=batch.id,
            name=batch.batch_no,
            status=status,
            total_documents=batch.total_files,
            completed_documents=batch.completed_files,
            failed_documents=batch.failed_files,
            created_at=batch.created_at,
            updated_at=getattr(batch, "updated_at", batch.created_at) or datetime.utcnow(),
            documents=items,
        )

    def refresh_batch_status(self, db: Session, batch_id: int) -> None:
        batch = db.get(Batch, batch_id)
        if not batch:
            return

        docs = (
            db.query(Document)
            .filter(Document.batch_no == batch.batch_no)
            .all()
        )

        total = len(docs)
        completed = sum(1 for d in docs if d.status in {"CHAT_READY", "COMPLETED", "APPROVED", "REVIEW_REQUIRED"})
        failed = sum(1 for d in docs if d.status in {"FAILED", "PARTIAL_FAILED"})
        processing = sum(1 for d in docs if d.status in {"QUEUED", "OCR_PROCESSING", "OCR_DONE", "INDEX_PROCESSING", "INDEX_DONE", "VECTORIZING", "FAST_INDEX_RUNNING"})

        batch.total_files = total
        batch.completed_files = completed
        batch.failed_files = failed
        batch.processing_files = processing
        batch.queued_files = max(total - completed - failed - processing, 0)
        db.flush()

    def _status_to_progress(self, status: str) -> int:
        s = (status or "").upper()
        if s in {"QUEUED", "UPLOADED"}:
            return 5
        if s == "OCR_PROCESSING":
            return 20
        if s in {"OCR_DONE", "FAST_INDEX_RUNNING"}:
            return 45
        if s == "INDEX_PROCESSING":
            return 60
        if s == "INDEX_DONE":
            return 75
        if s == "VECTORIZING":
            return 90
        if s in {"CHAT_READY", "COMPLETED", "APPROVED", "REVIEW_REQUIRED"}:
            return 100
        if s in {"FAILED", "PARTIAL_FAILED"}:
            return 100
        return 0

    def _derive_batch_status(self, docs: list[Document]) -> BatchStatus:
        total = len(docs)
        if total == 0:
            return BatchStatus.DRAFT

        completed = sum(1 for d in docs if d.status in {"CHAT_READY", "COMPLETED", "APPROVED", "REVIEW_REQUIRED"})
        failed = sum(1 for d in docs if d.status in {"FAILED", "PARTIAL_FAILED"})

        if completed == total:
            return BatchStatus.COMPLETED
        if completed + failed == total and failed > 0 and completed > 0:
            return BatchStatus.COMPLETED_WITH_ERRORS
        if failed == total:
            return BatchStatus.FAILED
        if any(d.status in {"OCR_PROCESSING", "INDEX_PROCESSING", "VECTORIZING", "FAST_INDEX_RUNNING"} for d in docs):
            return BatchStatus.PROCESSING
        return BatchStatus.QUEUED
