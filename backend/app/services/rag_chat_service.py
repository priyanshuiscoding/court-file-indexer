from __future__ import annotations

import re
from typing import Any

from app.core.config import get_settings

settings = get_settings()


class RAGChatService:
    def __init__(self, vector_service, llm_service) -> None:
        self.vector_service = vector_service
        self.llm_service = llm_service

    def _is_summary_question(self, question: str) -> bool:
        q = (question or "").lower()
        summary_keywords = [
            "summary",
            "summarize",
            "brief",
            "gist",
            "overview",
            "case summary",
            "structured summary",
            "what is this case about",
            "short note",
            "saransh",
            "saar",
        ]
        return any(k in q for k in summary_keywords)

    def _query_variants(self, question: str) -> list[str]:
        if not self._is_summary_question(question):
            return [question]

        return [
            question,
            "case number petitioner respondent applicant advocate judge order date",
            "sections act offence charges relief compensation amount fine sentence imprisonment",
            "court bench location police station district crime number fir",
            "final order decision direction dismissed allowed bail",
        ]

    def _dedupe_chunks(self, chunks: list[dict]) -> list[dict]:
        seen: set[tuple[Any, str]] = set()
        unique: list[dict] = []
        for c in chunks:
            page_no = c.get("page_no")
            text = (c.get("text") or "").strip()
            if not text:
                continue
            key = (page_no, text[:180])
            if key in seen:
                continue
            seen.add(key)
            unique.append(c)
        return unique

    def _noise_score(self, text: str) -> float:
        if not text:
            return 1.0
        clean = re.sub(r"\s+", "", text)
        if not clean:
            return 1.0

        alpha_num = sum(ch.isalnum() for ch in clean)
        weird = sum((not ch.isalnum()) for ch in clean)
        if alpha_num == 0:
            return 1.0

        ratio_weird = weird / max(len(clean), 1)
        repeated = len(re.findall(r"(.)\1{4,}", text))
        return min(1.0, ratio_weird + (0.15 * repeated))

    def _chunk_rank_score(self, chunk: dict, is_summary: bool) -> float:
        text = (chunk.get("text") or "").lower()
        base = float(chunk.get("score") or 0.0)
        bonus = 0.0

        if any(k in text for k in ["petitioner", "respondent", "applicant", "advocate", "judge", "versus", "v/s"]):
            bonus += 0.08
        if any(k in text for k in ["section", "act", "ipc", "bns", "sentence", "compensation", "fine"]):
            bonus += 0.07
        if any(k in text for k in ["order", "judgment", "dated", "court", "bench"]):
            bonus += 0.05

        noise_penalty = 0.35 * self._noise_score(text)
        if is_summary:
            return base + bonus - noise_penalty
        return base - noise_penalty

    def _collect_chunks(self, document_id: int, question: str) -> list[dict]:
        is_summary = self._is_summary_question(question)
        top_k = settings.CHAT_SUMMARY_CONTEXT_TOP_K if is_summary else settings.CHAT_CONTEXT_TOP_K

        collected: list[dict] = []
        for q in self._query_variants(question):
            found = self.vector_service.search_document_chunks(
                document_id=document_id,
                query=q,
                top_k=min(top_k, 8) if is_summary else top_k,
            )
            collected.extend(found)

        chunks = self._dedupe_chunks(collected)
        chunks.sort(key=lambda c: self._chunk_rank_score(c, is_summary), reverse=True)
        return chunks[:top_k]

    def _build_context(self, chunks: list[dict]) -> str:
        context_parts = []
        for i, chunk in enumerate(chunks, start=1):
            page_no = chunk.get("page_no")
            text = (chunk.get("text") or "").strip()
            context_parts.append(f"[Chunk {i} | Page {page_no}]\n{text}")
        return "\n\n".join(context_parts)

    def _build_summary_prompt(self, question: str, context: str) -> str:
        return f"""
You are a legal case-file assistant.

STRICT RULES:
- Use only the retrieved context below.
- Never invent names, dates, sections, or amounts.
- If a field is missing, write exactly: Not found in indexed pages.
- Keep output compact and factual.
- Mention page numbers for each important factual block.
- Do not use outside knowledge.
- Do not guess.

User request:
{question}

Retrieved context:
{context}

Return exactly in this structure:

Case Summary
1. Case Type/Number:
2. Court/Bench:
3. Location/Police Station/District:
4. Petitioner/Applicant:
5. Respondent/Opposite Party:
6. Advocate(s):
7. Judge/Authority:
8. Key Dates (filing/order/judgment):
9. Sections/Acts Involved:
10. Compensation/Fine/Amount:
11. Sentence/Jail Term (if any):
12. Relief Sought:
13. Final Direction/Current Status:
14. Short Narrative (5-7 lines):
15. Source Pages:
""".strip()

    def _build_qa_prompt(self, question: str, context: str) -> str:
        return f"""
You are a legal case-file assistant.

Rules:
- Answer only from retrieved context.
- Do not hallucinate.
- If answer is not present, return exactly: Answer not found clearly in the indexed case file.
- Keep response concise and direct.
- Always include source page numbers.
- Do not use outside knowledge.
- Do not guess.

User question:
{question}

Retrieved context:
{context}

Return format:
Answer: <direct answer>
Why: <one short evidence line>
Pages: <comma-separated page numbers>
""".strip()

    def _fallback_answer(self, question: str, chunks: list[dict]) -> str:
        page_list = [str(c.get("page_no")) for c in chunks if c.get("page_no") is not None]
        pages = ", ".join(page_list[:6]) if page_list else "unknown"
        top_text = (chunks[0].get("text") or "").strip() if chunks else ""
        top_text = top_text[:450] if top_text else ""

        if self._is_summary_question(question):
            return (
                "Case Summary\n"
                "1. Case Type/Number: Not found in indexed pages.\n"
                "2. Court/Bench: Not found in indexed pages.\n"
                "3. Location/Police Station/District: Not found in indexed pages.\n"
                "4. Petitioner/Applicant: Not found in indexed pages.\n"
                "5. Respondent/Opposite Party: Not found in indexed pages.\n"
                "6. Advocate(s): Not found in indexed pages.\n"
                "7. Judge/Authority: Not found in indexed pages.\n"
                "8. Key Dates (filing/order/judgment): Not found in indexed pages.\n"
                "9. Sections/Acts Involved: Not found in indexed pages.\n"
                "10. Compensation/Fine/Amount: Not found in indexed pages.\n"
                "11. Sentence/Jail Term (if any): Not found in indexed pages.\n"
                "12. Relief Sought: Not found in indexed pages.\n"
                "13. Final Direction/Current Status: Not found in indexed pages.\n"
                "14. Short Narrative (5-7 lines): Could not generate a reliable summary from the current model response.\n"
                f"15. Source Pages: {pages}"
            )

        if not top_text:
            return "Answer not found clearly in the indexed case file."

        return (
            "Answer not found clearly in the indexed case file.\n"
            "Why: The model could not return a reliable grounded answer in time.\n"
            f"Pages: {pages}\n"
            f"Evidence: {top_text}"
        )

    def answer_question(self, document_id: int, question: str) -> dict[str, Any]:
        chunks = self._collect_chunks(document_id=document_id, question=question)

        if not chunks:
            return {
                "answer": "No relevant indexed content found for this question.",
                "sources": [],
            }

        context = self._build_context(chunks)
        is_summary = self._is_summary_question(question)
        prompt = self._build_summary_prompt(question, context) if is_summary else self._build_qa_prompt(question, context)

        try:
            max_tokens = 420 if is_summary else 180
            timeout = settings.CHAT_GENERATION_TIMEOUT_SECONDS + (20 if is_summary else 0)
            answer = self.llm_service.generate(
                prompt,
                timeout_seconds=timeout,
                max_new_tokens=max_tokens,
            )
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
