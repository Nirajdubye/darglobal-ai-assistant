"""Split documents into overlapping chunks that each carry their source metadata.

Strategy: recursive splitting. Try paragraph breaks first, then line breaks, then
sentence ends, then spaces, so chunks break at natural boundaries. Every chunk is
prefixed with a short header (title + source) so it stays understandable on its own
when retrieved without its neighbours.
"""
from __future__ import annotations

import hashlib
import re

SEPARATORS = ["\n\n", "\n", ". ", " "]


def _split(text: str, size: int, seps: list[str]) -> list[str]:
    if len(text) <= size:
        return [text]
    if not seps:
        return [text[i:i + size] for i in range(0, len(text), size)]
    sep, rest = seps[0], seps[1:]
    parts = text.split(sep)
    pieces: list[str] = []
    buf = ""
    for part in parts:
        candidate = f"{buf}{sep}{part}" if buf else part
        if len(candidate) <= size:
            buf = candidate
            continue
        if buf:
            pieces.append(buf)
        if len(part) > size:
            pieces.extend(_split(part, size, rest))
            buf = ""
        else:
            buf = part
    if buf:
        pieces.append(buf)
    return pieces


def split_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")
    text = text.strip()
    if not text:
        return []
    pieces = _split(text, chunk_size - overlap if overlap else chunk_size, SEPARATORS)
    if not overlap or len(pieces) == 1:
        return [p.strip() for p in pieces if p.strip()]
    chunks = [pieces[0].strip()]
    for prev, cur in zip(pieces, pieces[1:]):
        tail = prev[-overlap:]
        cut = re.search(r"\s", tail)              # start overlap on a word boundary
        tail = tail[cut.end():] if cut else tail
        chunks.append(f"{tail} {cur}".strip())
    return [c for c in chunks if c]


def chunk_document(doc: dict, chunk_size: int = 900, overlap: int = 150) -> list[dict]:
    meta = doc["metadata"]
    header = f"[{meta['source']}] {meta['title']}"
    out = []
    for i, piece in enumerate(split_text(doc["text"], chunk_size, overlap)):
        text = piece if i == 0 else f"{header}\n{piece}"   # first chunk already starts with Title:
        chunk_id = hashlib.sha1(f"{meta['url']}|{doc['doc_id']}|{i}|{text}".encode()).hexdigest()
        out.append({"id": chunk_id, "text": text,
                    "metadata": {**meta, "doc_id": doc["doc_id"], "chunk_index": i}})
    return out


def chunk_documents(docs: list[dict], chunk_size: int = 900, overlap: int = 150) -> list[dict]:
    chunks = []
    for d in docs:
        chunks.extend(chunk_document(d, chunk_size, overlap))
    return chunks
