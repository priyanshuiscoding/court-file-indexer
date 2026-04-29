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

    def import_pending(self, db: Session, limit: int | None = None) -> HighCourtImportResponse:
        effective_limit = int(limit or settings.HC_IMPORT_LIMIT or 10)
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

        return HighCourtImportResponse(
            ok=failed == 0,
            fetched=len(rows),
            queued=queued,
            skipped=skipped,
            failed=failed,
            results=results,
        )

    def _import_one(self, db: Session, row: dict[str, Any]) -> HighCourtImportItemResult:
        external_row_id = row.get("id")
        batch_no = row.get("batch_no")
        fil_no = row.get("fil_no")

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
            pdf_path = self.pdf_resolver.resolve_pdf(batch_no_str)

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
        except Exception as exc:
            logger.exception("Failed importing High Court row id=%s batch_no=%s", external_row_id, batch_no)
            return HighCourtImportItemResult(
                external_row_id=external_row_id,
                batch_no=str(batch_no) if batch_no is not None else None,
                fil_no=str(fil_no) if fil_no is not None else None,
                pdf_path=None,
                status="FAILED",
                document_id=None,
                error=str(exc),
            )
