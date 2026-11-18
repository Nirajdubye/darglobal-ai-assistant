"""Collect data from DarGlobal and Wasalt and write raw + processed datasets.

    python -m scripts.scrape            # live sitemaps + parse browser snapshots
    python -m scripts.scrape --offline  # reuse cached sitemap data, only re-parse snapshots

Outputs
    data/raw/darglobal_urls.json        sitemap URLs in scope (to capture)
    data/raw/wasalt_listings.csv        all listing facts parsed from the product sitemap
    data/raw/wasalt_static_urls.json    info pages (static sitemap)
    data/raw/wasalt_category_urls.json  city/area landing pages (category sitemap)
    data/raw/darglobal_records.json     parsed records (raw)
    data/raw/wasalt_records.json        parsed records (raw)
    data/processed/documents.jsonl      cleaned, de-duplicated documents for indexing
    data/processed/scraping_summary.json
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.ingestion.cleaner import clean_records  # noqa: E402
from app.scraper.base_scraper import utc_now  # noqa: E402
from app.scraper.darglobal_scraper import DarGlobalScraper  # noqa: E402
from app.scraper.wasalt_scraper import WasaltScraper  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("scrape")


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="reuse cached sitemap data")
    ap.add_argument("--sample-per-group", type=int, default=20, help="Wasalt sitemap listings per (purpose, type)")
    ap.add_argument("--dg-articles", type=int, default=0, help="include N DarGlobal blog/press URLs in capture list")
    args = ap.parse_args()
    s = get_settings()
    raw = s.raw_dir
    summary: dict = {"run_at": utc_now(), "sources": {}}

    # ---------------- DarGlobal ----------------
    dg = DarGlobalScraper()
    urls_path = raw / "darglobal_urls.json"
    if args.offline and urls_path.exists():
        dg_urls = json.loads(urls_path.read_text())
    else:
        dg_urls = dg.discover_urls(include_articles=args.dg_articles)
        write_json(urls_path, dg_urls)
    dg_records = [r.to_dict() for r in dg.scrape_snapshots()]
    write_json(raw / "darglobal_records.json", dg_records)
    captured = {r["url"] for r in dg_records}
    summary["sources"]["DarGlobal"] = {
        "sitemap_urls_in_scope": len(dg_urls),
        "snapshot_stats": dg.stats,
        "records": len(dg_records),
        "coverage_of_sitemap_scope": f"{len(captured & {u['loc'] for u in dg_urls})}/{len(dg_urls)}",
        "by_page_type": pd.Series([r["page_type"] for r in dg_records]).value_counts().to_dict() if dg_records else {},
        "fields_present": _field_coverage(dg_records),
    }
    log.info("DarGlobal: %d records from snapshots (%s)", len(dg_records), dg.stats)

    # ---------------- Wasalt ----------------
    wa = WasaltScraper()
    csv_path, static_path = raw / "wasalt_listings.csv", raw / "wasalt_static_urls.json"
    if args.offline and csv_path.exists():
        cached = pd.read_csv(csv_path, dtype={"listing_id": str})
        df = wa.listings_frame(cached.rename(columns={"url": "loc"})[["loc", "lastmod"]].to_dict("records"))
        static = json.loads(static_path.read_text()) if static_path.exists() else []
        cat_path = raw / "wasalt_category_urls.json"
        static += json.loads(cat_path.read_text()) if cat_path.exists() else []
    else:
        maps = wa.fetch_sitemaps()
        df = wa.listings_frame(maps["product"])
        df.to_csv(csv_path, index=False)
        write_json(static_path, maps["static"])
        write_json(raw / "wasalt_category_urls.json", maps["category"])   # city/area landing pages
        static = maps["static"] + maps["category"]
    snap = [r.to_dict() for r in wa.scrape_snapshots()]
    snap_urls = {r["url"] for r in snap}
    sitemap_recs = [r.to_dict() for r in wa.sitemap_listing_records(df, args.sample_per_group)
                    if r.url not in snap_urls]     # snapshot (richer) wins over sitemap facts
    summary_recs = [r.to_dict() for r in wa.market_summary_records(df, static)]
    wa_records = snap + summary_recs + sitemap_recs
    write_json(raw / "wasalt_records.json", wa_records)
    summary["sources"]["Wasalt"] = {
        "sitemap_listings_total": int(len(df)),
        "sitemap_listings_sampled": len(sitemap_recs),
        "aggregate_documents": len(summary_recs),
        "snapshot_stats": wa.stats,
        "snapshot_records": len(snap),
        "records": len(wa_records),
        "fields_present": _field_coverage(wa_records),
    }
    log.info("Wasalt: %d listings in sitemap, %d records total", len(df), len(wa_records))

    # ---------------- Clean + save processed ----------------
    docs, clean_stats = clean_records(dg_records + wa_records)
    s.processed_dir.mkdir(parents=True, exist_ok=True)
    with s.documents_path.open("w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    summary["cleaning"] = clean_stats
    summary["documents"] = len(docs)
    write_json(s.processed_dir / "scraping_summary.json", summary)
    log.info("Wrote %d documents to %s", len(docs), s.documents_path)
    print(json.dumps(summary, indent=2))


def _field_coverage(records: list[dict]) -> dict:
    fields = ["description", "location", "country", "property_type", "price", "payment_plan",
              "bedrooms", "area_sqm", "amenities", "features"]
    return {f: sum(1 for r in records if r.get(f)) for f in fields}


if __name__ == "__main__":
    main()
