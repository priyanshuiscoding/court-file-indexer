from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models.document import Document
from app.models.document_page import DocumentPage
from app.models.index_row import IndexRow
from app.services.content_index_fallback_service import ContentIndexFallbackService
from app.services.index_detection_service import IndexDetectionService
from app.services.index_mapping_service import IndexMappingService
from app.services.index_parsing_service import IndexParsingService
from app.services.log_service import LogService
from app.services.row_validation_service import RowValidationService
from app.services.status_service import StatusService

settings = get_settings()


class IndexPipeline:
    def __init__(self) -> None:
        self.log_service = LogService()
        self.status_service = StatusService()
        self.detector = IndexDetectionService()
        self.parser = IndexParsingService()
        self.mapper = IndexMappingService()
        self.content_fallback = ContentIndexFallbackService()
        self.validator = RowValidationService()

    def run(self, db: Session, document: Document, ocr_pages: list[dict]) -> list[IndexRow]:
        self.status_service.update_document_status(db, document, "INDEX_SEARCH_RUNNING", "Detecting index pages")
        log = self.log_service.create_log(db, document_id=document.id, step_name="INDEX", status="RUNNING")

        candidates = self.detector.detect_index_pages(ocr_pages)
        selected_pages = self.detector.choose_primary_and_continuations(candidates)

        if selected_pages:
            self._persist_candidate_scores(db, document.id, candidates, selected_pages)
            parsed_rows = self.parser.parse_index_rows(selected_pages, page_count=document.page_count)

            if self.validator.suspicious_row_count(len(parsed_rows)):
                document.status = "REVIEW_REQUIRED"
                document.current_step = "Suspicious row extraction; needs review"
                db.add(document)
                db.commit()
                self.log_service.finish_log(
                    db,
                    log,
                    "FAILED",
                    f"Suspicious row count detected: {len(parsed_rows)}. Parser output rejected.",
                )
                return []
        else:
            self._persist_candidate_scores(db, document.id, candidates, [])
            if settings.ENABLE_CONTENT_GENERATED_INDEX_FALLBACK:
                parsed_rows = self.content_fallback.build_proposed_index(ocr_pages)
            else:
                self.status_service.update_document_status(db, document, "REVIEW_REQUIRED", "Index not confidently found")
                self.log_service.finish_log(db, log, "FAILED", "No confident index page found")
                return []

        saved_rows: list[IndexRow] = []
        used_fallback = not bool(selected_pages)

        for row in parsed_rows:
            doc_type, sub_type, map_conf = self.mapper.map_description(row["description_normalized"])
            extraction_conf = row.get("extraction_confidence", 0.0)
            final_conf = min(0.95, extraction_conf * 0.75 + map_conf * 0.25)

            db_row = IndexRow(
                document_id=document.id,
                row_no=row.get("row_no"),
                source_page_no=row.get("source_page_no"),
                description_raw=row["description_raw"],
                description_normalized=row.get("description_normalized"),
                annexure_no=row.get("annexure_no"),
                page_from=row.get("page_from"),
                page_to=row.get("page_to"),
                total_pages=row.get("total_pages"),
                mapped_document_type=doc_type,
                mapped_sub_document_type=sub_type,
                extraction_confidence=final_conf,
                status="PENDING",
                generated_from_content=row.get("generated_from_content", False),
            )
            db.add(db_row)
            saved_rows.append(db_row)

        db.commit()
        for row in saved_rows:
            db.refresh(row)

        if used_fallback:
            document.status = "REVIEW_REQUIRED"
            document.current_step = "Generated index needs review"
            db.add(document)
            db.commit()
        else:
            self.status_service.update_document_status(db, document, "INDEX_PARSED", "Index parsed")

        self.log_service.finish_log(
            db,
            log,
            "COMPLETED",
            f"Parsed {len(saved_rows)} rows; fallback={used_fallback}",
        )
        return saved_rows

    def _persist_candidate_scores(self, db: Session, document_id: int, candidates: list[dict], selected_pages: list[dict]) -> None:
        selected_numbers = {page["page_no"] for page in selected_pages}
        by_page = {page["page_no"]: page for page in candidates}

        pages = db.query(DocumentPage).filter(DocumentPage.document_id == document_id).all()
        for page in pages:
            meta = by_page.get(page.page_no)
            if not meta:
                continue
            page.candidate_score = meta["index_candidate_score"]
            page.is_candidate_index_page = page.page_no in selected_numbers
            db.add(page)
        db.commit()
