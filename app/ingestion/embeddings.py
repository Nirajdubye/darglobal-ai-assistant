"""Sentence-Transformers embedding wrapper (lazy, process-wide singleton)."""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)


class Embedder:
    _instances: dict[str, "Embedder"] = {}
    _lock = threading.Lock()

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # heavy import, keep lazy

        logger.info("Loading embedding model %s", model_name)
        self.model_name = model_name
        self.model = SentenceTransformer(model_name, device="cpu")
        self.dimension = self.model.get_sentence_embedding_dimension()

    @classmethod
    def get(cls, model_name: str) -> "Embedder":
        with cls._lock:
            if model_name not in cls._instances:
                cls._instances[model_name] = cls(model_name)
            return cls._instances[model_name]

    def embed(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        if not texts:
            return []
        # normalize_embeddings=True -> dot product == cosine similarity
        vecs = self.model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                                 show_progress_bar=len(texts) > 500, convert_to_numpy=True)
        return vecs.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]
