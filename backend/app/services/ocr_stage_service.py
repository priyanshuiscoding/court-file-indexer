from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.document import Document
from app.services.ocr_pipeline_service import OCRPipelineService


class OCRStageService:
    def __init__(self) -> None:
        self.pipeline = OCRPipelineService()

    def process_document(self, db: Session, document: Document) -> list[dict]:
        return self.pipeline.process_document(db, document)
