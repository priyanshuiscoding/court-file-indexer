from __future__ import annotations

from qdrant_client.models import PointStruct
from app.services.embedding_service import EmbeddingService
from app.services.qdrant_service import QdrantService
from app.utils.text_normalizer import normalize_text


class VectorService:
    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()
        self.qdrant_service = QdrantService()

    def build_chunk_payloads(self, document_id: int, ocr_pages: list[dict]) -> list[dict]:
        payloads: list[dict] = []
        point_id = 1
        for page in ocr_pages:
            page_no = page["page_no"]
            page_text = normalize_text(page.get("text", ""))
            if not page_text:
                continue
            chunks = self._chunk_text(page_text, chunk_size=900, overlap=120)
            for chunk in chunks:
                payloads.append(
                    {
                        "point_id": int(f"{document_id}{page_no:04d}{point_id:04d}"),
                        "document_id": document_id,
                        "page_no": page_no,
                        "text": chunk,
                    }
                )
                point_id += 1
        return payloads

    def vectorize_chunks(self, chunk_payloads: list[dict]) -> list[PointStruct]:
        texts = [item["text"] for item in chunk_payloads]
        vectors = self.embedding_service.encode(texts) if texts else []
        points: list[PointStruct] = []
        for item, vector in zip(chunk_payloads, vectors):
            points.append(
                PointStruct(
                    id=item["point_id"],
                    vector=vector,
                    payload={
                        "document_id": item["document_id"],
                        "page_no": item["page_no"],
                        "text": item["text"],
                    },
                )
            )
        return points

    def embed_query(self, question: str) -> list[float]:
        return self.embedding_service.encode([question])[0]

    def search_document_chunks(self, document_id: int, query: str, top_k: int = 6) -> list[dict]:
        query_vector = self.embed_query(query)
        hits = self.qdrant_service.search_document(query_vector, document_id=document_id, limit=top_k)
        chunks: list[dict] = []
        for hit in hits:
            payload = hit.payload or {}
            chunks.append(
                {
                    "page_no": payload.get("page_no"),
                    "text": payload.get("text", ""),
                    "score": float(hit.score),
                }
            )
        return chunks

    def _chunk_text(self, text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
        if len(text) <= chunk_size:
            return [text]
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)
        return chunks
