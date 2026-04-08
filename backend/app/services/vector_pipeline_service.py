from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.index_row import IndexRow
from app.pipelines.vector_pipeline import VectorPipeline
from app.pipelines.verification_pipeline import VerificationPipeline
from app.services.page_service import PageService


class VectorPipelineService:
    def __init__(self) -> None:
        self.page_service = PageService()

    def process_document(self, db: Session, document: Document) -> None:
        pages = self.page_service.get_pages(db, document.id)
        ocr_pages = [
            {
                "page_no": p.page_no,
                "text": p.ocr_text or "",
                "width": p.width,
                "height": p.height,
            }
            for p in pages
        ]

        VectorPipeline().run(db, document, ocr_pages)

        rows = (
            db.query(IndexRow)
            .filter(IndexRow.document_id == document.id)
            .order_by(IndexRow.row_no.asc())
            .all()
        )
        VerificationPipeline().run(db, document, rows, ocr_pages)
