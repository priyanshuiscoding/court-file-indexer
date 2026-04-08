from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.document_page import DocumentPage


class PageService:
    def replace_pages(self, db: Session, document_id: int, page_payloads: list[dict]) -> list[DocumentPage]:
        db.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))
        db.commit()

        rows: list[DocumentPage] = []
        for item in page_payloads:
            row = DocumentPage(
                document_id=document_id,
                page_no=item["page_no"],
                image_path=item.get("image_path"),
                width=item.get("width"),
                height=item.get("height"),
                ocr_text=item.get("text"),
                ocr_json_path=item.get("ocr_json_path"),
                ocr_confidence=item.get("confidence", 0.0),
                is_candidate_index_page=item.get("is_candidate_index_page", False),
                candidate_score=item.get("candidate_score", 0.0),
            )
            if hasattr(row, "status") and item.get("status") is not None:
                setattr(row, "status", item.get("status"))
            if hasattr(row, "error_message") and item.get("error_message") is not None:
                setattr(row, "error_message", item.get("error_message"))
            db.add(row)
            rows.append(row)

        db.commit()
        for row in rows:
            db.refresh(row)
        return rows

    def upsert_page(self, db: Session, document_id: int, page_payload: dict) -> DocumentPage:
        page_no = int(page_payload["page_no"])

        stmt = (
            select(DocumentPage)
            .where(
                DocumentPage.document_id == document_id,
                DocumentPage.page_no == page_no,
            )
        )
        row = db.scalars(stmt).first()

        if not row:
            row = DocumentPage(
                document_id=document_id,
                page_no=page_no,
            )
            db.add(row)

        row.image_path = page_payload.get("image_path")
        row.width = page_payload.get("width")
        row.height = page_payload.get("height")
        row.ocr_text = page_payload.get("text")
        row.ocr_json_path = page_payload.get("ocr_json_path")
        row.ocr_confidence = page_payload.get("confidence", 0.0)
        row.is_candidate_index_page = page_payload.get("is_candidate_index_page", False)
        row.candidate_score = page_payload.get("candidate_score", 0.0)

        db.commit()
        db.refresh(row)
        return row

    def update_page_status(self, db: Session, document_id: int, page_no: int, status: str, error_message: str | None = None) -> None:
        stmt = select(DocumentPage).where(DocumentPage.document_id == document_id, DocumentPage.page_no == page_no)
        page = db.execute(stmt).scalar_one_or_none()
        if not page:
            return
        if hasattr(page, "status"):
            setattr(page, "status", status)
        if hasattr(page, "error_message"):
            setattr(page, "error_message", error_message)
        db.flush()

    def get_pages(self, db: Session, document_id: int) -> list[DocumentPage]:
        stmt = (
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_no.asc())
        )
        return list(db.scalars(stmt).all())
