from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.high_court_import_job import HighCourtImportJob
from app.services.high_court_mysql_service import HighCourtMySQLService
from app.services.high_court_result_service import HighCourtResultService

READY_STATUSES = {"INDEX_READY", "CHAT_READY", "REVIEW_REQUIRED"}
logger = logging.getLogger(__name__)


class HighCourtCompletionService:
    def __init__(self) -> None:
        self.mysql_service = HighCourtMySQLService()
        self.result_service = HighCourtResultService()

    def mark_completed_by_batch_no(self, db: Session, batch_no: str) -> dict:
        stmt = select(HighCourtImportJob).where(HighCourtImportJob.batch_no == str(batch_no))
        job = db.scalars(stmt).first()
        if not job:
            return {
                "ok": False,
                "batch_no": str(batch_no),
                "status": "NOT_FOUND",
                "message": "Import job not found",
            }

        if job.status not in READY_STATUSES:
            return {
                "ok": False,
                "batch_no": job.batch_no,
                "status": job.status,
                "message": "Job is not ready for external completion update",
            }

        result = self.result_service.get_result(db, job.batch_no)
        if not result.get("ok"):
            return {
                "ok": False,
                "batch_no": job.batch_no,
                "status": job.status,
                "message": "Index JSON is not available; external DB not updated",
                "result_error": result.get("error") or result.get("message"),
            }

        mysql_result = self.mysql_service.mark_completed(
            external_row_id=job.external_row_id,
            batch_no=job.batch_no,
        )
        logger.info(
            "High Court external mark-complete attempted batch_no=%s external_row_id=%s ok=%s rows_affected=%s",
            job.batch_no,
            job.external_row_id,
            mysql_result.get("ok"),
            mysql_result.get("rows_affected"),
        )

        job.updated_at = datetime.utcnow()
        if mysql_result.get("ok"):
            job.status = "EXTERNAL_COMPLETED"
            job.error_message = None
        else:
            if mysql_result.get("disabled"):
                job.error_message = mysql_result.get("message")
            else:
                job.status = "EXTERNAL_UPDATE_FAILED"
                job.error_message = mysql_result.get("message")

        db.add(job)
        db.commit()
        db.refresh(job)

        return {
            "ok": bool(mysql_result.get("ok")),
            "batch_no": job.batch_no,
            "document_id": job.document_id,
            "local_status": job.status,
            "mysql": mysql_result,
        }

    def mark_completed_ready_jobs(self, db: Session, *, limit: int = 100) -> dict:
        stmt = (
            select(HighCourtImportJob)
            .where(HighCourtImportJob.status.in_(READY_STATUSES))
            .order_by(HighCourtImportJob.updated_at.asc())
            .limit(limit)
        )
        jobs = list(db.scalars(stmt).all())

        results = []
        success = 0
        failed = 0
        skipped = 0

        for job in jobs:
            result = self.mark_completed_by_batch_no(db, job.batch_no)
            results.append(result)
            if result.get("ok"):
                success += 1
            else:
                failed += 1

        return {
            "ok": failed == 0,
            "checked": len(jobs),
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "results": results,
        }
