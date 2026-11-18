"""Chunk + embed data/processed/documents.jsonl into the persistent Chroma index.

    python -m scripts.ingest           # incremental (unchanged chunks are skipped)
    python -m scripts.ingest --reset   # drop the collection and rebuild
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.ingestion.indexing import VectorIndex  # noqa: E402
from app.ingestion.pipeline import build_index  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()
    s = get_settings()
    if not s.documents_path.exists():
        sys.exit(f"{s.documents_path} not found - run `python -m scripts.scrape` first")
    index = VectorIndex(s.chroma_dir, s.collection_name, embedding_model=s.embedding_model)
    if args.reset:
        index.client.delete_collection(s.collection_name)
        index = VectorIndex(s.chroma_dir, s.collection_name, embedding_model=s.embedding_model)
    result = build_index(s, index)
    print(json.dumps({**result, "stats": index.stats()}, indent=2))


if __name__ == "__main__":
    main()
