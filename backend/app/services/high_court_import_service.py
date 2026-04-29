from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document
from app.schemas.high_court_import_models import HighCourtImportItemResult, HighCourtImportResponse
from app.services.document_service import DocumentService
from app.services.high_court_import_job_service import HighCourtImportJobService
from app.services.high_court_mysql_service import HighCourtMySQLService
from app.services.high_court_pdf_resolver_service import HighCourtPDFResolverService
from app.tasks.document_tasks import enqueue_document_pipeline
from app.utils.pdf_utils import get_pdf_page_count

logger = logging.getLogger(__name__)
settings = get_settings()


class HighCourtImportService:
    def __init__(self) -> None:
        self.mysql_service = HighCourtMySQLService()
        self.pdf_resolver = HighCourtPDFResolverService()
        self.document_service = DocumentService()
        self.job_service = HighCourtImportJobService()

    def import_pending(self, db: Session, limit: int | None = None) -> HighCourtImportResponse:
        effective_limit = min(500, int(limit or settings.HC_IMPORT_LIMIT or 10))
        logger.info("High Court import_pending started limit=%s", effective_limit)
        rows = self.mysql_service.fetch_pending_rows(effective_limit)

        results: list[HighCourtImportItemResult] = []
        queued = 0
        skipped = 0
        failed = 0

        for row in rows:
            result = self._import_one(db, row)
            results.append(result)
            if result.status == "QUEUED":
                queued += 1
            elif result.status == "SKIPPED_DUPLICATE":
                skipped += 1
            else:
                failed += 1

        response = HighCourtImportResponse(
            ok=failed == 0,
            fetched=len(rows),
            queued=queued,
            skipped=skipped,
            failed=failed,
            results=results,
        )
        logger.info(
            "High Court import_pending completed fetched=%s queued=%s skipped=%s failed=%s",
            response.fetched,
            response.queued,
            response.skipped,
            response.failed,
        )
        return response

    def import_by_batch_no(self, db: Session, batch_no: str) -> HighCourtImportItemResult:
        row = {
            "id": None,
            "batch_no": batch_no,
            "fil_no": None,
        }
        return self._import_one(db, row, force_retry=True)

    def _import_one(
        self,
        db: Session,
        row: dict[str, Any],
        *,
        force_retry: bool = False,
    ) -> HighCourtImportItemResult:
        external_row_id = row.get("id")
        batch_no = row.get("batch_no")
        fil_no = row.get("fil_no")
        job = None

        try:
            if batch_no is None:
                return HighCourtImportItemResult(
                    external_row_id=external_row_id,
                    batch_no=None,
                    fil_no=str(fil_no) if fil_no is not None else None,
                    status="FAILED",
                    error="Missing batch_no",
                )

            batch_no_str = str(batch_no).strip()
            fil_no_str = str(fil_no).strip() if fil_no is not None else None
            job = self.job_service.upsert_discovered(
                db,
                external_row_id=external_row_id,
                batch_no=batch_no_str,
                fil_no=fil_no_str,
            )
            db.commit()

            if (
                not force_retry
                and job.status in {"QUEUED", "SKIPPED_DUPLICATE"}
            ):
                return HighCourtImportItemResult(
                    external_row_id=external_row_id if external_row_id is not None else job.external_row_id,
                    batch_no=batch_no_str,
                    fil_no=fil_no_str if fil_no_str is not None else job.fil_no,
                    pdf_path=job.source_pdf_path,
                    status="SKIPPED_DUPLICATE",
                    document_id=job.document_id,
                    error=None,
                )

            self.job_service.mark_attempt(db, job)
            db.commit()

            pdf_path = self.pdf_resolver.resolve_pdf(batch_no_str)
            self.job_service.mark_pdf_found(db, job, str(pdf_path))
            db.commit()

            stmt = (
                select(Document)
                .where(
                    or_(
                        Document.batch_no == batch_no_str,
                        Document.original_path == str(pdf_path),
                    )
                )
                .order_by(Document.created_at.desc())
                .limit(1)
            )
            existing = db.scalars(stmt).first()
            if existing:
                self.job_service.mark_skipped_duplicate(
                    db,
                    job,
                    document_id=existing.id,
                    pdf_path=str(pdf_path),
                )
                db.commit()
                return HighCourtImportItemResult(
                    external_row_id=external_row_id,
                    batch_no=batch_no_str,
                    fil_no=fil_no_str,
                    pdf_path=str(pdf_path),
                    status="SKIPPED_DUPLICATE",
                    document_id=existing.id,
                    error=None,
                )

            page_count = get_pdf_page_count(str(pdf_path))
            if page_count <= 0:
                raise ValueError(f"PDF has invalid page count: {page_count}")

            document = self.document_service.create_document(
                db,
                file_name=Path(pdf_path).name,
                original_path=str(pdf_path),
                page_count=page_count,
                cnr_number=fil_no_str,
                batch_no=batch_no_str,
                status="UPLOADED",
                current_step="Imported from High Court source",
            )

            enqueue_document_pipeline(db, document.id)
            self.job_service.mark_queued(
                db,
                job,
                document_id=document.id,
                pdf_path=str(pdf_path),
            )
            db.commit()
            logger.info(
                "Queued imported High Court PDF batch_no=%s document_id=%s path=%s",
                batch_no_str,
                document.id,
                pdf_path,
            )

            return HighCourtImportItemResult(
                external_row_id=external_row_id,
                batch_no=batch_no_str,
                fil_no=fil_no_str,
                pdf_path=str(pdf_path),
                status="QUEUED",
                document_id=document.id,
                error=None,
            )
        except FileNotFoundError as exc:
            logger.exception("PDF not found for High Court row id=%s batch_no=%s", external_row_id, batch_no)
            if job is not None:
                self.job_service.mark_failed(db, job, "PDF_NOT_FOUND", str(exc))
                db.commit()
            return HighCourtImportItemResult(
                external_row_id=external_row_id,
                batch_no=str(batch_no) if batch_no is not None else None,
                fil_no=str(fil_no) if fil_no is not None else None,
                pdf_path=None,
                status="PDF_NOT_FOUND",
                document_id=job.document_id if job is not None else None,
                error=str(exc),
            )
        except Exception as exc:
            logger.exception("Failed importing High Court row id=%s batch_no=%s reason=%s", external_row_id, batch_no, str(exc))
            if job is not None:
                self.job_service.mark_failed(db, job, "FAILED", str(exc))
                db.commit()
            return HighCourtImportItemResult(
                external_row_id=external_row_id,
                batch_no=str(batch_no) if batch_no is not None else None,
                fil_no=str(fil_no) if fil_no is not None else None,
                pdf_path=None,
                status="FAILED",
                document_id=None,
                error=str(exc),
            )
