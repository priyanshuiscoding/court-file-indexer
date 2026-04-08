from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.index_page_detector import score_index_page
from app.models.document import Document
from app.models.document_page import DocumentPage
from app.services.hindi_ocr_fallback_service import HindiOCRFallbackService
from app.services.log_service import LogService
from app.services.ocr_merge_service import OCRMergeService
from app.services.ocr_service import OCRService
from app.services.page_service import PageService
from app.services.pdf_render_service import PDFRenderService
from app.services.status_service import StatusService

settings = get_settings()


class OCRPipeline:
    def __init__(self) -> None:
        self.log_service = LogService()
        self.status_service = StatusService()
        self.render_service = PDFRenderService()
        self.ocr_service = OCRService()
        self.hindi_fallback_service = HindiOCRFallbackService()
        self.merge_service = OCRMergeService()
        self.page_service = PageService()

    def _ocr(self, document_id: int, rendered: list[dict]) -> list[dict]:
        primary = self.ocr_service.run_ocr_on_rendered_pages(document_id, rendered)

        primary_conf = 0.0
        if primary:
            primary_conf = sum(float(p.get("confidence", 0.0)) for p in primary) / len(primary)

        if settings.ENABLE_HINDI_FALLBACK and primary_conf < 0.5:
            fallback = self.hindi_fallback_service.run_tesseract_hin_eng(document_id, rendered)
            return self.merge_service.merge_primary_and_fallback(primary, fallback)

        return primary

    def run_single_page(self, db: Session, document: Document, page_no: int) -> dict:
        existing = self._get_existing_page(db, document.id, page_no)
        if existing is not None:
            return existing

        rendered = self.render_service.render_pages(document.id, document.original_path, page_no, page_no)
        pages = self._ocr(document.id, rendered)

        page = pages[0]
        self.page_service.upsert_page(db, document.id, page)
        return page

    def run_fast_until_index(
        self,
        db: Session,
        document: Document,
        max_probe_pages: int = 10,
        max_extended_pages: int = 20,
    ):
        self.status_service.update_document_status(db, document, "FAST_INDEX_RUNNING", "Fast indexing")

        collected = []

        # First pass: pages 1..10
        for page_no in range(1, min(document.page_count, max_probe_pages) + 1):
            page = self.run_single_page(db, document, page_no)
            collected.append(page)

        scores = [score_index_page(p.get("text", "")) for p in collected]
        if scores and max(scores) >= 4:
            return collected

        # Second pass: extend up to page 20
        for page_no in range(max_probe_pages + 1, min(document.page_count, max_extended_pages) + 1):
            page = self.run_single_page(db, document, page_no)
            collected.append(page)

        return collected

    def run_full(self, db: Session, document: Document):
        existing = self.page_service.get_pages(db, document.id)
        if existing and len(existing) >= document.page_count:
            return [self._to_payload(page) for page in existing]

        rendered = self.render_service.render_pages(document.id, document.original_path, 1, document.page_count)
        pages = self._ocr(document.id, rendered)

        self.page_service.replace_pages(db, document.id, pages)
        return pages

    def _get_existing_page(self, db: Session, document_id: int, page_no: int) -> dict | None:
        stmt = select(DocumentPage).where(
            DocumentPage.document_id == document_id,
            DocumentPage.page_no == page_no,
        )
        row = db.scalars(stmt).first()
        if not row:
            return None
        return self._to_payload(row)

    def _to_payload(self, page: DocumentPage) -> dict:
        return {
            "page_no": page.page_no,
            "image_path": page.image_path,
            "width": page.width,
            "height": page.height,
            "text": page.ocr_text or "",
            "confidence": float(page.ocr_confidence or 0.0),
            "lines": [],
            "ocr_json_path": page.ocr_json_path,
        }
