from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.high_court_import_job import HighCourtImportJob

logger = logging.getLogger(__name__)


PROCESSING_STATUSES = {
    "UPLOADED",
    "FAST_INDEX_RUNNING",
    "VECTORIZING",
    "VECTORING",
    "FULL_PROCESS_RUNNING",
    "PROCESSING",
    "FAST_INDEX",
    "FULL_PROCESS",
    "OCR_PROCESSING",
    "INDEX_PROCESSING",
    "OCR_DONE",
    "INDEX_DONE",
    "INDEX_PARSED",
}

FINAL_STATUSES = {
    "INDEX_READY",
    "CHAT_READY",
    "REVIEW_REQUIRED",
    "FAILED",
}


class HighCourtImportStatusSyncService:
    def get_job_by_document_id(self, db: Session, document_id: int) -> HighCourtImportJob | None:
        stmt = select(HighCourtImportJob).where(HighCourtImportJob.document_id == document_id)
        return db.scalars(stmt).first()

    def derive_status(self, document: Document) -> str | None:
        doc_status = (document.status or "").upper()

        if doc_status == "FAILED":
            return "DOCUMENT_FAILED"
        if doc_status == "REVIEW_REQUIRED":
            return "REVIEW_REQUIRED"
        if bool(document.chat_ready):
            return "CHAT_READY"
        if doc_status == "INDEX_READY":
            return "INDEX_READY"
        if doc_status in PROCESSING_STATUSES:
            return "PROCESSING"
        return None

    def sync_document(
        self,
        db: Session,
        document: Document,
        *,
        commit: bool = False,
        error_message: str | None = None,
    ) -> HighCourtImportJob | None:
        if not document or not document.id:
            return None

        job = self.get_job_by_document_id(db, document.id)
        if not job:
            return None
        if job.status in {"EXTERNAL_COMPLETED"}:
            return job

        new_status = self.derive_status(document)
        if not new_status:
            return job

        if job.status != new_status:
            logger.info(
                "Syncing High Court import job status batch_no=%s document_id=%s %s -> %s",
                job.batch_no,
                document.id,
                job.status,
                new_status,
            )

        job.status = new_status
        job.updated_at = datetime.utcnow()

        if error_message:
            job.error_message = error_message
        elif new_status in {"PROCESSING", "INDEX_READY", "CHAT_READY"}:
            job.error_message = None

        db.add(job)
        if commit:
            db.commit()
            db.refresh(job)
        else:
            db.flush()
        return job

    def sync_all_linked_jobs(self, db: Session, *, limit: int = 500) -> dict:
        stmt = (
            select(HighCourtImportJob, Document)
            .join(Document, HighCourtImportJob.document_id == Document.id)
            .limit(limit)
        )
        rows = db.execute(stmt).all()

        updated = 0
        checked = 0
        for job, document in rows:
            checked += 1
            if job.status in {"EXTERNAL_COMPLETED"}:
                continue
            old_status = job.status
            new_status = self.derive_status(document)
            if not new_status:
                continue
            if old_status != new_status:
                job.status = new_status
                job.updated_at = datetime.utcnow()
                if new_status in {"PROCESSING", "INDEX_READY", "CHAT_READY"}:
                    job.error_message = None
                db.add(job)
                updated += 1

        db.commit()
        return {"ok": True, "checked": checked, "updated": updated}
