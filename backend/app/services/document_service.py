from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document


class DocumentService:
    def create_document(
        self,
        db: Session,
        *,
        file_name: str,
        original_path: str,
        page_count: int,
        cnr_number: str | None = None,
        batch_no: str | None = None,
        status: str = "UPLOADED",
        current_step: str = "Uploaded",
        commit: bool = True,
    ) -> Document:
        doc = Document(
            file_name=file_name,
            original_path=original_path,
            page_count=page_count,
            cnr_number=cnr_number,
            batch_no=batch_no,
            status=status,
            current_step=current_step,
        )
        db.add(doc)
        db.flush()

        if commit:
            db.commit()
            db.refresh(doc)
        return doc

    def update_status(
        self,
        db: Session,
        document: Document,
        *,
        status: str,
        current_step: str | None = None,
    ) -> None:
        document.status = status
        if current_step is not None:
            document.current_step = current_step
        db.add(document)
        db.flush()

    def get_document(self, db: Session, document_id: int) -> Document | None:
        return db.get(Document, document_id)

    def list_documents(self, db: Session, cnr: str | None = None, batch_no: str | None = None) -> list[Document]:
        stmt = select(Document).order_by(Document.created_at.desc())
        if cnr:
            stmt = stmt.where(Document.cnr_number.ilike(f"%{cnr}%"))
        if batch_no:
            stmt = stmt.where(Document.batch_no.ilike(f"%{batch_no}%"))
        return list(db.scalars(stmt).all())
