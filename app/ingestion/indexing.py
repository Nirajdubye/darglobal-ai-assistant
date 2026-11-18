"""Persistent ChromaDB index with incremental, duplicate-free updates.

Chunk ids are content hashes, so:
* re-indexing unchanged content is a no-op (ids already exist, skipped);
* changed pages get new ids; their old chunks are deleted by URL first;
* the same chunk can never be stored twice.
"""
from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.ingestion.embeddings import Embedder

logger = logging.getLogger(__name__)
# chromadb 0.6 ships a posthog client with a broken signature; telemetry is disabled anyway.
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)


class VectorIndex:
    def __init__(self, persist_dir: Path, collection_name: str, embedder: Embedder | None = None,
                 embedding_model: str | None = None):
        persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(persist_dir),
                                                settings=ChromaSettings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection(name=collection_name,
                                                               metadata={"hnsw:space": "cosine"})
        self._embedder = embedder
        self._embedding_model = embedding_model

    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = Embedder.get(self._embedding_model)
        return self._embedder

    def count(self) -> int:
        return self.collection.count()

    def upsert_chunks(self, chunks: list[dict], batch_size: int = 256) -> dict:
        """Add new chunks; drop stale chunks of URLs being re-indexed. Returns stats."""
        stats = {"received": len(chunks), "added": 0, "unchanged": 0, "stale_deleted": 0}
        if not chunks:
            return stats
        # de-duplicate within this batch
        unique = {c["id"]: c for c in chunks}
        chunks = list(unique.values())

        # remove chunks belonging to these URLs that are no longer produced
        new_ids = set(unique)
        for url in {c["metadata"]["url"] for c in chunks}:
            existing = self.collection.get(where={"url": url}, include=[])["ids"]
            stale = [i for i in existing if i not in new_ids]
            if stale:
                self.collection.delete(ids=stale)
                stats["stale_deleted"] += len(stale)

        existing_ids: set[str] = set()
        ids = list(new_ids)
        for i in range(0, len(ids), 500):
            existing_ids.update(self.collection.get(ids=ids[i:i + 500], include=[])["ids"])
        todo = [c for c in chunks if c["id"] not in existing_ids]
        stats["unchanged"] = len(chunks) - len(todo)

        for i in range(0, len(todo), batch_size):
            batch = todo[i:i + batch_size]
            self.collection.add(
                ids=[c["id"] for c in batch],
                documents=[c["text"] for c in batch],
                metadatas=[c["metadata"] for c in batch],
                embeddings=self.embedder.embed([c["text"] for c in batch]),
            )
            stats["added"] += len(batch)
        logger.info("Index upsert: %s", stats)
        return stats

    def remove_missing_urls(self, keep_urls: set[str]) -> int:
        """Delete chunks whose URL is no longer in the dataset (full-sync mode)."""
        data = self.collection.get(include=["metadatas"])
        gone = [i for i, m in zip(data["ids"], data["metadatas"]) if m.get("url") not in keep_urls]
        if gone:
            self.collection.delete(ids=gone)
        return len(gone)

    def query(self, embedding: list[float], top_k: int = 6, where: dict | None = None) -> list[dict]:
        if self.count() == 0:
            return []
        res = self.collection.query(query_embeddings=[embedding], n_results=min(top_k, self.count()),
                                    where=where or None, include=["documents", "metadatas", "distances"])
        out = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            out.append({"text": doc, "metadata": meta, "score": round(1.0 - float(dist), 4)})
        return out

    def stats(self) -> dict:
        data = self.collection.get(include=["metadatas"])
        metas = data["metadatas"]
        return {
            "chunks": len(metas),
            "documents": len({m.get("doc_id") for m in metas}),
            "by_source": dict(Counter(m.get("source") for m in metas)),
            "by_page_type": dict(Counter(m.get("page_type") for m in metas)),
            "countries": sorted({m.get("country") for m in metas if m.get("country")}),
        }
