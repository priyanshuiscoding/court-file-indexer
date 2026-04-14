from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.models.document import Document
from app.services.document_chat_service import DocumentChatService
from app.services.document_service import DocumentService
from app.services.llm_service import LLMService
from app.services.rag_chat_service import RAGChatService
from app.services.vector_service import VectorService

router = APIRouter(prefix="/chat", tags=["chat"])

settings = get_settings()

document_service = DocumentService()
chat_store = DocumentChatService()


class ChatRequest(BaseModel):
    question: str


@router.get("/{document_id}/status")
def chat_status(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document_id": document_id, "ready": document.chat_ready}


@router.get("/{document_id}/history")
def get_chat_history(document_id: int, db: Session = Depends(get_db)):
    document = document_service.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    rows = chat_store.list_messages(db, document_id)
    return [
        {
            "id": row.id,
            "role": row.role,
            "message": row.message,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.post("/{document_id}/ask")
def ask_chat(document_id: int, payload: ChatRequest, db: Session = Depends(get_db)):
    document = document_service.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    question = (payload.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    if not document.chat_ready:
        raise HTTPException(status_code=409, detail="Document is not chat-ready yet. Complete indexing first.")

    try:
        chat_store.add_message(db, document_id, "user", question)

        rag = RAGChatService(
            vector_service=VectorService(),
            llm_service=LLMService(),
        )

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(rag.answer_question, document_id, question)
            try:
                result = future.result(timeout=settings.CHAT_REQUEST_TIMEOUT_SECONDS)
            except FuturesTimeoutError:
                result = {
                    "answer": "The chat model took too long to respond. Please retry once. If this keeps happening, the local model service may be slow or unavailable.",
                    "sources": [],
                }

        answer_text = (result.get("answer") or "").strip() or "Answer not found clearly in the indexed case file."
        sources = result.get("sources") or []

        chat_store.add_message(db, document_id, "assistant", answer_text)

        return {
            "answer": answer_text,
            "sources": sources,
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(exc)}") from exc


@router.post("/documents/{document_id}")
def chat_with_document(document_id: int, payload: ChatRequest, db: Session = Depends(get_db)):
    return ask_chat(document_id, payload, db)
