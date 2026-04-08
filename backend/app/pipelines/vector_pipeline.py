from sqlalchemy.orm import Session
from app.models.document import Document
from app.services.log_service import LogService
from app.services.qdrant_service import QdrantService
from app.services.status_service import StatusService
from app.services.vector_service import VectorService


class VectorPipeline:
    def __init__(self) -> None:
        self.log_service = LogService()
        self.status_service = StatusService()
        self.vector_service = VectorService()
        self.qdrant_service = QdrantService()

    def run(self, db: Session, document: Document, ocr_pages: list[dict]) -> list[dict]:
        self.status_service.update_document_status(db, document, "VECTORIZING", "Vectorizing document")
        log = self.log_service.create_log(db, document_id=document.id, step_name="VECTORIZE", status="RUNNING")

        self.qdrant_service.ensure_collection()
        chunk_payloads = self.vector_service.build_chunk_payloads(document.id, ocr_pages)
        points = self.vector_service.vectorize_chunks(chunk_payloads)
        self.qdrant_service.upsert_chunks(points)

        document.is_vectorized = True
        document.chat_ready = len(points) > 0
        document.status = "VECTORIZED"
        document.current_step = "Vectorized"
        db.add(document)
        db.commit()
        db.refresh(document)

        self.log_service.finish_log(db, log, "COMPLETED", f"Vectorized {len(points)} chunks")
        return chunk_payloads
