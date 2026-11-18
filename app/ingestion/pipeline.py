"""documents.jsonl -> chunks -> Chroma. Shared by scripts/ingest.py, the API and app startup."""
from __future__ import annotations

import json
import logging

from app.config import Settings
from app.ingestion.chunker import chunk_documents
from app.ingestion.indexing import VectorIndex

logger = logging.getLogger(__name__)


def load_documents(settings: Settings) -> list[dict]:
    path = settings.documents_path
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def build_index(settings: Settings, index: VectorIndex, full_sync: bool = True) -> dict:
    docs = load_documents(settings)
    chunks = chunk_documents(docs, settings.chunk_size, settings.chunk_overlap)
    stats = index.upsert_chunks(chunks)
    if full_sync and docs:
        stats["removed_urls_chunks"] = index.remove_missing_urls({d["metadata"]["url"] for d in docs})
    stats["total_in_index"] = index.count()
    logger.info("Indexed %d documents / %d chunks: %s", len(docs), len(chunks), stats)
    return {"documents": len(docs), "chunks": len(chunks), "index": stats}
