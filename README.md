---
title: Real Estate RAG Assistant
emoji: 🏛️
colorFrom: yellow
colorTo: gray
sdk: gradio
app_file: app.py
pinned: false
short_description: RAG chatbot over public DarGlobal and Wasalt data
---

# DarGlobal & Wasalt AI Real Estate Assistant

A retrieval-augmented chatbot that answers questions about **DarGlobal** luxury projects and **Wasalt** property listings using information collected from their public websites, with a source link for every answer.

> **Disclaimer:** independent technical demonstration built for the DarGlobal *Junior AI Engineer – Applied AI* assignment. It is not affiliated with, endorsed by, or operated by DarGlobal or Wasalt. Data may be outdated, so always check the official websites.

## Business problem

Buyers and brokers ask the same questions again and again: *Where is this project? What amenities does it have? Is there a payment plan? What is available in Riyadh?* The answers are spread across many web pages. A chatbot can answer instantly, **but only if it never makes up prices or details**. This project shows how to build one that:

- answers only from collected website content,
- says clearly when the information is not available,
- links every answer to the original page.

## Features

- Scrapers for both sites that respect robots.txt, with rate limiting, retries, timeouts, de-duplication and bot-challenge detection
- Cleaning, chunking, MiniLM embeddings and a persistent ChromaDB index with incremental, duplicate-free updates
- Custom RAG pipeline with a similarity threshold (off-topic questions never reach the LLM), source filtering and follow-up question handling
- OpenRouter free model (`openrouter/free`). Paid models are rejected by config validation.
- FastAPI backend (`/health`, `/stats`, `/chat`, `/admin/ingest`) with OpenAPI docs at `/docs`
- Streamlit chat UI: welcome message, suggested questions, history, sources with relevance scores, clear chat, status sidebar
- 51 automated tests plus a 15+ question end-to-end evaluation
- Docker image with the model and index built in; docker-compose with a persistent volume and healthchecks

## Architecture

```
 OFFLINE (dev machine)                                   ONLINE (container)
 robots.txt + sitemaps ──► URL lists                     Streamlit UI (:7860 / :8501)
 browser snapshots     ──► data/raw/html/                     │ HTTP
 BS4 parsers           ──► data/raw/*.json                FastAPI (:8000)
 cleaner               ──► data/processed/documents.jsonl     │
 chunker + MiniLM      ──► ChromaDB (data/chroma_db) ◄── Retriever ──► Prompt ──► OpenRouter (free)
                                                              └──► answer + source URLs (from metadata)
```

| Layer | Module |
|---|---|
| Scraping | `app/scraper/base_scraper.py`, `darglobal_scraper.py`, `wasalt_scraper.py` |
| Ingestion | `app/ingestion/cleaner.py`, `chunker.py`, `embeddings.py`, `indexing.py`, `pipeline.py` |
| RAG | `app/rag/retriever.py`, `prompt.py`, `generator.py` |
| Service / API | `app/services/chat_service.py`, `app/api/routes.py`, `app/main.py` |
| UI | `app/frontend/streamlit_app.py` |
| Scripts | `scripts/scrape.py`, `ingest.py`, `evaluate.py`, `snapshot_receiver.py` |

More detail: [architecture.md](architecture.md) · research: [website_research.md](website_research.md).

## Technology stack

Python 3.11 · FastAPI · Streamlit · Requests + BeautifulSoup (lxml) · Pandas · Sentence-Transformers (`all-MiniLM-L6-v2`) · ChromaDB · OpenAI SDK pointed at OpenRouter · Pytest · Docker / Compose · Hugging Face Spaces

## Scraping methodology

| | DarGlobal | Wasalt |
|---|---|---|
| robots.txt | allows `/`, `/projects/`, `/blog/`, `/press/` | allows `/`; disallows `/search` (we never touch it) |
| Discovery | `sitemap.xml` (480 URLs → 93 in scope) | CDN sitemaps (59,998 listing URLs + 8.6k city pages) |
| Protection | Imperva/Incapsula JS challenge | Cloudflare managed challenge |
| Content source | browser snapshots | sitemap facts (+ optional browser snapshots) |

**Both sites block plain HTTP clients with bot-protection challenges. This project does not get around them:** no headless challenge solving, no stealth plugins, no cookie replay. Instead:

1. **Sitemaps** are fetched live by the polite fetcher. Sitemaps are published for crawlers and are not protected. Wasalt listing URLs encode real facts (`/property/sale/villa-333-sqm-facing-east-on-20m-width-street-5841671` → sale, villa, 333 sqm, east, 20 m street, id). Pandas computes aggregate statistics over all 59,998 listings, and a stratified sample of individual listings is indexed.
2. **Page content** is captured from a normal browser session at human pace (`scripts/snapshot_receiver.py`, or Chrome *Save page as*). The same BeautifulSoup parsers then process the saved HTML. Challenge pages are detected and skipped, and nothing is ever invented.

Data-quality handling (documented, never "fixed"): many Wasalt apartment and floor URLs state impossible areas (median ≈ 1,900 "sqm", max 14 million). Areas outside per-type plausibility bounds are dropped from the facts and statistics. Where more than 30% of a type's values are implausible, no size figure is reported for that type at all.

Outputs: `data/raw/*` (raw records, URL lists, listings CSV) · `data/processed/documents.jsonl` · `data/processed/scraping_summary.json`.

## RAG pipeline

1. **Validate**: reject empty, symbol-only or overlong questions (422). Greetings are answered without retrieval.
2. **Follow-ups**: short or pronoun-based questions ("what about its payment plan?") are searched together with the previous user question.
3. **Embed** the query with MiniLM (normalised, so cosine = dot product).
4. **Search** Chroma for the top-k chunks (k = 6). If the question names only one company, results are filtered by `source`.
5. **Threshold**: if no chunk scores at least 0.30, the bot returns a fixed "I don't have that information" answer **without calling the LLM**, so it can't hallucinate.
6. **Prompt**: strict grounding rules plus numbered context blocks `[n] title | source | url | collected date`, with the last 4 turns of history.
7. **Generate** with OpenRouter at temperature 0.1.
8. **Sources** are built from retrieval metadata, never from LLM text, so URLs can't be invented. Cited sources come first, and invented citation numbers are ignored.

## OpenRouter integration

- OpenAI-compatible client, `base_url=https://openrouter.ai/api/v1`, key from `OPENROUTER_API_KEY`.
- `OPENROUTER_MODEL` defaults to `openrouter/free`, which routes to an available free model. The response reports which model actually answered.
- **Free-only guard**: config validation only accepts `openrouter/free` or ids ending in `:free`. There is no silent fallback.
- Timeout 60 s, 2 SDK retries with backoff on 429/5xx. Errors map to clear HTTP codes: 429 rate-limited, 503 unavailable or not configured, 504 timeout. The key is never logged or returned.

## Installation & local run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # add OPENROUTER_API_KEY

python -m scripts.scrape             # collect data (sitemaps live + parse snapshots)
python -m scripts.ingest             # build/update the Chroma index

uvicorn app.main:app --port 8000     # API → http://localhost:8000/docs
streamlit run app/frontend/streamlit_app.py   # UI → http://localhost:8501
```

Capturing pages (optional, for richer data): run `python -m scripts.snapshot_receiver`, open the URLs from `data/raw/darglobal_urls.json` in Chrome, and send each rendered page to the receiver. You can also use *Save page as → HTML only* into `data/raw/html/darglobal/`. Then re-run scrape + ingest.

## Docker

```bash
docker compose up --build -d         # api :8000, ui :8501, index in volume chroma_data
docker run -p 7860:7860 --env-file .env realestate-rag   # single container (same as cloud)
```

## Deployment

Hugging Face Spaces (Docker SDK, free CPU). See [docs/deployment_guide.md](docs/deployment_guide.md).

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | `status` ok/degraded, index chunk count, whether the LLM key is configured |
| GET | `/stats` | chunks/documents by source and page type, countries, models, scraping summary |
| POST | `/chat` | `{"question": str, "history": [{"role","content"}]}` → `{answer, sources[], model, grounded, latency_ms}` |
| POST | `/admin/ingest` | re-index `documents.jsonl`; disabled unless `ADMIN_TOKEN` is set; requires the `X-Admin-Token` header |

```bash
curl -X POST localhost:8000/chat -H 'content-type: application/json' \
     -d '{"question":"How many villas are for rent on Wasalt?"}'
```

## Testing

```bash
pytest -q                     # 51 tests (scrapers, cleaning, chunking, embeddings, retrieval, RAG, API, errors, sources)
pytest -q -m "not slow"       # skip the real-model test
python -m scripts.evaluate    # end-to-end evaluation with the real model → docs/eval_results.json
```

Results: [docs/test_report.md](docs/test_report.md).

## Limitations

- Bot protection means page content depends on browser snapshots, so coverage is limited to the pages captured.
- The Wasalt sitemap has no prices, cities or descriptions for individual listings. The bot says so instead of guessing.
- Free OpenRouter models vary in quality and are rate-limited (about 50 requests/day on a free account).
- Data is a point-in-time snapshot, shown with collection dates.
- On a free Hugging Face Space the app sleeps when idle, so the first load can take about a minute.

## Future improvements

- Hybrid search (BM25 + vectors) and a cross-encoder re-ranker for exact names and IDs
- Structured filters (country, type, price range) extracted from the question
- Scheduled refresh with change detection (the index is already incremental)
- Arabic support with a multilingual embedding model
- Ask both companies for an official data feed or API
- Answer-faithfulness checks (LLM-as-judge) in the evaluation
