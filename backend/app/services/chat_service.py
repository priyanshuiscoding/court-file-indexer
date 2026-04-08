from __future__ import annotations

import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from transformers import pipeline
from app.core.config import get_settings
from app.models.chat import ChatMessage
from app.services.qdrant_service import QdrantService
from app.services.vector_service import VectorService

settings = get_settings()


class ChatService:
    _generator = None

    def __init__(self) -> None:
        self.vector_service = VectorService()
        self.qdrant_service = QdrantService()

    def _get_generator(self):
        if ChatService._generator is None:
            ChatService._generator = pipeline(
                "text-generation",
                model=settings.LOCAL_CHAT_MODEL,
                max_new_tokens=300,
            )
        return ChatService._generator

    def ask(self, db: Session, document_id: int, question: str) -> dict:
        query_vector = self.vector_service.embed_query(question)
        hits = self.qdrant_service.search_document(query_vector, document_id, limit=settings.CHAT_CONTEXT_TOP_K)
        contexts = []
        citations = []
        for hit in hits:
            payload = hit.payload or {}
            page_no = payload.get("page_no")
            text = payload.get("text", "")
            contexts.append(f"[Page {page_no}] {text}")
            citations.append(
                {
                    "page_no": page_no,
                    "score": float(hit.score),
                    "snippet": text[:280],
                }
            )

        prompt = self._build_prompt(question, contexts)
        generator = self._get_generator()
        output = generator(prompt)[0]["generated_text"]
        answer = output[len(prompt):].strip() if output.startswith(prompt) else output.strip()
        if not answer:
            answer = "I could not find enough grounded evidence in this document to answer reliably."

        user_message = ChatMessage(document_id=document_id, role="user", content=question)
        assistant_message = ChatMessage(
            document_id=document_id,
            role="assistant",
            content=answer,
            citations_json=json.dumps(citations, ensure_ascii=False),
        )
        db.add(user_message)
        db.add(assistant_message)
        db.commit()

        return {"answer": answer, "citations": citations}

    def get_history(self, db: Session, document_id: int) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.document_id == document_id)
            .order_by(ChatMessage.created_at.asc())
        )
        return list(db.scalars(stmt).all())

    def _build_prompt(self, question: str, contexts: list[str]) -> str:
        joined_context = "\n\n".join(contexts[: settings.CHAT_CONTEXT_TOP_K])
        return (
            "You are a court document assistant. Answer only from the provided context. "
            "If evidence is weak, say so. Mention page numbers when possible.\n\n"
            f"Context:\n{joined_context}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )
