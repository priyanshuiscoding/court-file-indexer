from __future__ import annotations

import torch
from sentence_transformers import SentenceTransformer
from app.core.config import get_settings

settings = get_settings()


class EmbeddingService:
    _model: SentenceTransformer | None = None

    def _get_model(self) -> SentenceTransformer:
        if EmbeddingService._model is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            EmbeddingService._model = SentenceTransformer(settings.LOCAL_EMBEDDING_MODEL, device=device)
        return EmbeddingService._model

    def encode(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        vectors = model.encode(texts, normalize_embeddings=True)
        return [vec.tolist() for vec in vectors]
