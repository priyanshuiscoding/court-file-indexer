from __future__ import annotations

from typing import Any


class RAGChatService:
    def __init__(self, vector_service, llm_service) -> None:
        self.vector_service = vector_service
        self.llm_service = llm_service

    def _build_prompt(self, question: str, chunks: list[dict]) -> str:
        context_parts = []
        for i, chunk in enumerate(chunks, start=1):
            page_no = chunk.get("page_no")
            text = (chunk.get("text") or "").strip()
            context_parts.append(f"[Chunk {i} | Page {page_no}]\n{text}")

        context = "\n\n".join(context_parts)

        return f"""
You are a legal case-file assistant.

Rules:
- Answer only from the retrieved case-file context.
- Do not invent facts.
- If the answer is not clearly present, say:
  "Answer not found clearly in the indexed case file."
- Keep the answer precise and helpful.

User question:
{question}

Retrieved context:
{context}

Return:
1. Direct answer
2. Short reasoning
3. Pages used
""".strip()

    def _fallback_answer(self, question: str, chunks: list[dict]) -> str:
        page_list = [str(c.get("page_no")) for c in chunks if c.get("page_no") is not None]
        pages = ", ".join(page_list[:5]) if page_list else "unknown"
        top_text = (chunks[0].get("text") or "").strip() if chunks else ""
        top_text = top_text[:500] if top_text else ""

        if not top_text:
            return "I found relevant pages but could not extract a reliable answer right now. Please try again in a moment."

        return (
            "I could not complete model generation in time, so here is the most relevant extracted evidence. "
            f"Relevant pages: {pages}.\n\n"
            f"Top excerpt:\n{top_text}"
        )

    def answer_question(self, document_id: int, question: str) -> dict[str, Any]:
        chunks = self.vector_service.search_document_chunks(
            document_id=document_id,
            query=question,
            top_k=6,
        )

        if not chunks:
            return {
                "answer": "No relevant indexed content found for this question.",
                "sources": [],
            }

        prompt = self._build_prompt(question, chunks)

        try:
            answer = self.llm_service.generate(prompt)
            if not answer:
                answer = "Answer not found clearly in the indexed case file."
        except Exception:
            answer = self._fallback_answer(question, chunks)

        return {
            "answer": answer,
            "sources": [
                {
                    "page_no": c.get("page_no"),
                    "text": (c.get("text") or "")[:500],
                    "score": c.get("score"),
                }
                for c in chunks
            ],
        }
