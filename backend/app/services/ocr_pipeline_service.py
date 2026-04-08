from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.document import Document
from app.pipelines.ocr_pipeline import OCRPipeline


class OCRPipelineService:
    def process_document(self, db: Session, document: Document) -> list[dict]:
        return OCRPipeline().run_full(db, document)
