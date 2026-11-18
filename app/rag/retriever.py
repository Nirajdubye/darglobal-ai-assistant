"""Semantic retrieval over the Chroma index."""
from __future__ import annotations

import re

from app.config import Settings
from app.ingestion.indexing import VectorIndex

FOLLOW_UP_RE = re.compile(
    r"\b(it|its|it's|they|them|their|that|this|those|these|there|same|which one|the project|the property|"
    r"the villa|the apartment|more|else|another|also)\b", re.I)


def detect_source_filter(question: str) -> dict | None:
    q = question.lower()
    dg = "darglobal" in q or "dar global" in q
    wa = "wasalt" in q
    if dg and not wa:
        return {"source": "DarGlobal"}
    if wa and not dg:
        return {"source": "Wasalt"}
    return None


def build_search_query(question: str, history: list[dict] | None) -> str:
    """Make follow-up questions searchable by adding the previous user question.

    "What is its payment plan?" alone retrieves nothing useful; combined with
    "Tell me about Les Vagues" it retrieves the Les Vagues chunks.
    """
    if not history:
        return question
    prev_user = [m["content"] for m in history if m.get("role") == "user"]
    if not prev_user:
        return question
    if len(question.split()) <= 8 or FOLLOW_UP_RE.search(question):
        return f"{prev_user[-1]} {question}"
    return question


class Retriever:
    def __init__(self, index: VectorIndex, settings: Settings):
        self.index = index
        self.settings = settings

    def retrieve(self, question: str, history: list[dict] | None = None, top_k: int | None = None) -> list[dict]:
        k = top_k or self.settings.top_k
        query = build_search_query(question, history)
        emb = self.index.embedder.embed_query(query)
        where = detect_source_filter(query)
        hits = self.index.query(emb, top_k=k, where=where)
        if where and not hits:      # filter too strict -> fall back to unfiltered search
            hits = self.index.query(emb, top_k=k)
        return [h for h in hits if h["score"] >= self.settings.min_similarity]
