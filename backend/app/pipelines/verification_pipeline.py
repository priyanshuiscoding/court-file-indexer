from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.index_row import IndexRow
from app.services.log_service import LogService
from app.services.status_service import StatusService
from app.services.verification_service import VerificationService


class VerificationPipeline:
    def __init__(self) -> None:
        self.log_service = LogService()
        self.status_service = StatusService()
        self.verifier = VerificationService()

    def run(self, db: Session, document: Document, rows: list[IndexRow], ocr_pages: list[dict]) -> None:
        self.status_service.update_document_status(db, document, "VERIFYING", "Verifying index rows")
        log = self.log_service.create_log(db, document_id=document.id, step_name="VERIFY", status="RUNNING")

        row_dicts = [
            {
                "id": row.id,
                "page_from": row.page_from,
                "page_to": row.page_to,
                "description_normalized": row.description_normalized,
                "mapped_document_type": row.mapped_document_type,
                "mapped_sub_document_type": row.mapped_sub_document_type,
            }
            for row in rows
        ]
        verified = self.verifier.verify_index_rows(row_dicts, ocr_pages, total_pdf_pages=document.page_count)

        review_required = False
        for item in verified:
            row = db.get(IndexRow, item["id"])
            if row:
                row.verification_confidence = item["verification_confidence"]
                row.status = "REVIEW" if item["verification_confidence"] < 0.62 else "AUTO_OK"
                if row.status == "REVIEW":
                    review_required = True
                db.add(row)

        if review_required:
            document.status = "REVIEW_REQUIRED"
            document.current_step = "Needs review"
        else:
            document.status = "APPROVED"
            document.current_step = "Auto-approved"

        db.add(document)
        db.commit()
        self.log_service.finish_log(db, log, "COMPLETED", "Verification complete")
