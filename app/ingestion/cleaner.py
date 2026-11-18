"""Turn scraped records into clean, de-duplicated text documents."""
from __future__ import annotations

import hashlib
import re
import unicodedata

BOILERPLATE_PATTERNS = [
    r"^(accept|reject|manage) (all )?cookies?",
    r"we use cookies",
    r"^(enquire|register|subscribe|download brochure|book (a|your) (call|viewing|unit)|contact us|call us)\b.{0,40}$",
    r"^(read more|learn more|view more|explore|see all|back|next|previous|close|menu)$",
    r"^©|all rights reserved",
    r"^(privacy policy|terms (and|&) conditions|terms of use)$",
    r"^(share|follow us)( on)?\b.{0,30}$",
]
_BOILER = [re.compile(p, re.I) for p in BOILERPLATE_PATTERNS]

FIELD_LABELS = [
    ("source", "Source"), ("page_type", "Page type"), ("country", "Country"), ("city", "City"),
    ("location", "Location"), ("property_type", "Property type"), ("listing_type", "Listing purpose"),
    ("price", "Price"), ("payment_plan", "Payment plan"), ("bedrooms", "Bedrooms"),
    ("bathrooms", "Bathrooms"), ("area_sqm", "Area (sqm)"),
]


def normalize_text(text: str | None) -> str:
    """Unicode NFKC, unify quotes/dashes, collapse spaces, keep line breaks."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-").replace("​", "")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def remove_boilerplate(text: str) -> str:
    kept, seen = [], set()
    for ln in text.splitlines():
        low = ln.lower()
        if any(p.search(ln) for p in _BOILER):
            continue
        if low in seen:          # repeated nav/footer lines
            continue
        seen.add(low)
        kept.append(ln)
    return "\n".join(kept)


def content_hash(text: str) -> str:
    return hashlib.sha1(re.sub(r"\s+", " ", text.lower()).encode()).hexdigest()


def record_to_document(rec: dict) -> dict | None:
    """Flatten a PropertyRecord dict into {text, metadata}. Only present fields are written."""
    title = normalize_text(rec.get("title")) or "Untitled"
    header = [f"Title: {title}"]
    for key, label in FIELD_LABELS:
        val = rec.get(key)
        if val not in (None, "", []):
            header.append(f"{label}: {normalize_text(str(val))}")
    if rec.get("amenities"):
        header.append("Amenities: " + "; ".join(normalize_text(a) for a in rec["amenities"]))
    if rec.get("features"):
        header.append("Features: " + "; ".join(normalize_text(f) for f in rec["features"]))
    if rec.get("specifications"):
        header.append("Specifications: " + "; ".join(f"{k}: {v}" for k, v in rec["specifications"].items()))

    body_parts = [normalize_text(rec.get("description")), remove_boilerplate(normalize_text(rec.get("body_text")))]
    body = "\n".join(p for p in body_parts if p)
    text = "\n".join(header) + ("\n\n" + body if body else "")
    if len(text) < 40:
        return None

    metadata = {
        "url": rec["url"],
        "source": rec["source"],
        "title": title[:200],
        "page_type": rec.get("page_type") or "",
        "country": rec.get("country") or "",
        "city": rec.get("city") or "",
        "property_type": rec.get("property_type") or "",
        "listing_type": rec.get("listing_type") or "",
        "price": rec.get("price") or "",
        "extraction_method": rec.get("extraction_method") or "",
        "extracted_at": rec.get("extracted_at") or "",
    }
    return {"doc_id": hashlib.sha1(rec["url"].encode()).hexdigest()[:16] + "-" + content_hash(title)[:6],
            "text": text, "metadata": metadata, "content_hash": content_hash(text)}


def clean_records(records: list[dict]) -> tuple[list[dict], dict]:
    """Records -> documents, dropping exact duplicates (same text) and duplicate (url, title)."""
    docs, seen_hash, seen_key = [], set(), set()
    stats = {"input": len(records), "empty": 0, "duplicate": 0}
    for rec in records:
        doc = record_to_document(rec)
        if doc is None:
            stats["empty"] += 1
            continue
        key = (doc["metadata"]["url"], doc["metadata"]["title"])
        if doc["content_hash"] in seen_hash or key in seen_key:
            stats["duplicate"] += 1
            continue
        seen_hash.add(doc["content_hash"])
        seen_key.add(key)
        docs.append(doc)
    stats["output"] = len(docs)
    return docs, stats
