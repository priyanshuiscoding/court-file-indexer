import logging

from sqlalchemy.orm import Session

from app.models.document import Document
from app.services.high_court_import_status_sync_service import HighCourtImportStatusSyncService

logger = logging.getLogger(__name__)


class StatusService:
    def __init__(self) -> None:
        self.high_court_sync = HighCourtImportStatusSyncService()

    def update_document_status(self, db: Session, document: Document, status: str, step: str) -> Document:
        document.status = status
        document.current_step = step
        db.add(document)
        try:
            self.high_court_sync.sync_document(db, document, commit=False)
        except Exception:
            logger.exception("Failed to sync High Court import status for document_id=%s", document.id)
        db.commit()
        db.refresh(document)
        return document
