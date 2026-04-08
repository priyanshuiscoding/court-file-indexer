from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.document_chat_message import DocumentChatMessage


class DocumentChatService:
    def list_messages(self, db: Session, document_id: int):
        return (
            db.query(DocumentChatMessage)
            .filter(DocumentChatMessage.document_id == document_id)
            .order_by(DocumentChatMessage.created_at.asc(), DocumentChatMessage.id.asc())
            .all()
        )

    def add_message(self, db: Session, document_id: int, role: str, message: str):
        row = DocumentChatMessage(
            document_id=document_id,
            role=role,
            message=message,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
