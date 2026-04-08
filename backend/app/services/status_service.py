from sqlalchemy.orm import Session
from app.models.document import Document


class StatusService:
    def update_document_status(self, db: Session, document: Document, status: str, step: str) -> Document:
        document.status = status
        document.current_step = step
        db.add(document)
        db.commit()
        db.refresh(document)
        return document
