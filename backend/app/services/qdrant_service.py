from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams
from app.core.config import get_settings

settings = get_settings()


class QdrantService:
    def __init__(self) -> None:
        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection = settings.QDRANT_COLLECTION

    def ensure_collection(self, vector_size: int | None = None) -> None:
        size = vector_size or settings.EMBEDDING_VECTOR_SIZE
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection not in collections:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=size, distance=Distance.COSINE),
            )

    def upsert_chunks(self, points: list[PointStruct]) -> None:
        if not points:
            return
        self.client.upsert(collection_name=self.collection, points=points)

    def search_document(self, vector: list[float], document_id: int, limit: int | None = None):
        top_k = limit or settings.QDRANT_TOP_K
        return self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            query_filter=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            ),
            limit=top_k,
        )
