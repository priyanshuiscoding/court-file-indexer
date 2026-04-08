from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import JobStatus, JobType
from app.models.processing_job import ProcessingJob


class JobService:
    def enqueue_job(
        self,
        db: Session,
        *,
        document_id: int,
        batch_id: Optional[int],
        job_type: JobType,
        payload: Optional[dict] = None,
        priority: int = 100,
        max_retries: int = 3,
    ) -> ProcessingJob:
        job = ProcessingJob(
            document_id=document_id,
            batch_id=batch_id,
            job_type=job_type,
            status=JobStatus.QUEUED,
            priority=priority,
            payload=payload or {},
            max_retries=max_retries,
        )
        db.add(job)
        db.flush()
        return job

    def claim_next_job(self, db: Session, job_type: JobType) -> Optional[ProcessingJob]:
        stmt = (
            select(ProcessingJob)
            .where(ProcessingJob.job_type == job_type, ProcessingJob.status == JobStatus.QUEUED)
            .order_by(ProcessingJob.priority.asc(), ProcessingJob.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        job = db.execute(stmt).scalar_one_or_none()
        if not job:
            return None

        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        db.flush()
        return job

    def mark_success(self, db: Session, job: ProcessingJob) -> None:
        job.status = JobStatus.SUCCESS
        job.finished_at = datetime.now(timezone.utc)
        job.error_message = None
        db.flush()

    def mark_failed(self, db: Session, job: ProcessingJob, error_message: str) -> None:
        job.retry_count += 1
        if job.retry_count <= job.max_retries:
            job.status = JobStatus.QUEUED
            job.error_message = error_message[:2000]
            job.started_at = None
            job.finished_at = None
        else:
            job.status = JobStatus.FAILED
            job.finished_at = datetime.now(timezone.utc)
            job.error_message = error_message[:2000]
        db.flush()
