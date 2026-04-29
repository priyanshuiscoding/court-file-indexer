from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.high_court_import_job import HighCourtImportJob

settings = get_settings()


class HighCourtImportJobService:
    def get_by_batch_no(self, db: Session, batch_no: str) -> HighCourtImportJob | None:
        stmt = select(HighCourtImportJob).where(HighCourtImportJob.batch_no == str(batch_no))
        return db.scalars(stmt).first()

    def upsert_discovered(
        self,
        db: Session,
        *,
        external_row_id: int | str | None,
        batch_no: int | str,
        fil_no: int | str | None = None,
    ) -> HighCourtImportJob:
        batch_no_str = str(batch_no).strip()
        job = self.get_by_batch_no(db, batch_no_str)

        if not job:
            job = HighCourtImportJob(
                source_system=settings.HC_SOURCE_SYSTEM or "high_court_mysql",
                external_row_id=str(external_row_id) if external_row_id is not None else None,
                batch_no=batch_no_str,
                fil_no=str(fil_no).strip() if fil_no is not None else None,
                status="DISCOVERED",
            )
            db.add(job)
            db.flush()
            return job

        if external_row_id is not None and not job.external_row_id:
            job.external_row_id = str(external_row_id)
        if fil_no is not None and not job.fil_no:
            job.fil_no = str(fil_no).strip()

        job.updated_at = datetime.utcnow()
        db.add(job)
        db.flush()
        return job

    def mark_attempt(self, db: Session, job: HighCourtImportJob) -> HighCourtImportJob:
        job.import_attempts = int(job.import_attempts or 0) + 1
        job.last_attempt_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        db.add(job)
        db.flush()
        return job

    def mark_pdf_found(self, db: Session, job: HighCourtImportJob, pdf_path: str) -> HighCourtImportJob:
        job.status = "PDF_FOUND"
        job.source_pdf_path = pdf_path
        job.error_message = None
        job.updated_at = datetime.utcnow()
        db.add(job)
        db.flush()
        return job

    def mark_queued(
        self,
        db: Session,
        job: HighCourtImportJob,
        *,
        document_id: int,
        pdf_path: str | None = None,
    ) -> HighCourtImportJob:
        job.status = "QUEUED"
        job.document_id = document_id
        if pdf_path:
            job.source_pdf_path = pdf_path
        job.error_message = None
        job.imported_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        db.add(job)
        db.flush()
        return job

    def mark_skipped_duplicate(
        self,
        db: Session,
        job: HighCourtImportJob,
        *,
        document_id: int,
        pdf_path: str | None = None,
    ) -> HighCourtImportJob:
        job.status = "SKIPPED_DUPLICATE"
        job.document_id = document_id
        if pdf_path:
            job.source_pdf_path = pdf_path
        job.error_message = None
        job.imported_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        db.add(job)
        db.flush()
        return job

    def mark_failed(self, db: Session, job: HighCourtImportJob, status: str, error: str) -> HighCourtImportJob:
        job.status = status
        job.error_message = error
        job.updated_at = datetime.utcnow()
        db.add(job)
        db.flush()
        return job

    def list_jobs(
        self,
        db: Session,
        *,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[HighCourtImportJob]:
        stmt = select(HighCourtImportJob).order_by(HighCourtImportJob.created_at.desc())
        if status:
            stmt = stmt.where(HighCourtImportJob.status == status)
        stmt = stmt.offset(offset).limit(limit)
        return list(db.scalars(stmt).all())

    def count_by_status(self, db: Session) -> dict[str, int]:
        stmt = (
            select(HighCourtImportJob.status, func.count(HighCourtImportJob.id))
            .group_by(HighCourtImportJob.status)
        )
        rows = db.execute(stmt).all()
        return {str(status): int(count) for status, count in rows if status is not None}
