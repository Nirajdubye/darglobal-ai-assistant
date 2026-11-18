# Architecture

## High-level flow

```
 OFFLINE (dev machine)                                   ONLINE (container)
 ─────────────────────                                   ──────────────────
 robots.txt + sitemaps ──► URL list                      Streamlit UI (:7860, public)
        │                                                     │  HTTP (internal)
 Real-browser snapshots ──► data/raw/html/*.html              ▼
        │                                                FastAPI (:8000, internal)
 BS4 parsers (DG / Wasalt) ──► data/raw/*.json                │
        │                                                ChatService
 cleaner ──► data/processed/documents.jsonl                   │
        │                                          ┌──────────┴──────────┐
 chunker ──► chunks (+ metadata, source URL)       ▼                     ▼
        │                                      Retriever            Generator
 embeddings (MiniLM-L6-v2) ──► ChromaDB ───────► (Chroma query)    (OpenRouter, free model)
        data/chroma_db/  (baked into image / mounted volume)
```

## Components

| Module | Responsibility |
|---|---|
| `app/config.py` | Pydantic-settings; all config from env (`OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, chunk size, top-k…). Rejects non-free models. |
| `app/scraper/base_scraper.py` | Polite fetcher: robots.txt check, rate limit (≥2 s/req), retries with exponential backoff (tenacity), timeouts, URL de-dup, challenge-page detection, `live` / `snapshot` modes. |
| `app/scraper/darglobal_scraper.py` | Sitemap → project URLs; parses name, country, location, type, description, amenities, price/payment plan if present, partner brand. |
| `app/scraper/wasalt_scraper.py` | Sitemap parser (60k URLs → structured slug fields, sampled) + listing-page parser (price, city, district, beds/baths, area, features, description). |
| `app/ingestion/cleaner.py` | Whitespace/unicode normalisation, boilerplate removal, content-hash de-dup. |
| `app/ingestion/chunker.py` | Recursive char/sentence splitter, configurable size/overlap; each chunk prefixed with a header (`Project: X | Country: Y | Source: Z`) so it is self-describing. |
| `app/ingestion/embeddings.py` | Lazy-loaded SentenceTransformer singleton, normalised vectors. |
| `app/ingestion/indexing.py` | Chroma `PersistentClient`, cosine space; chunk id = `sha1(url + chunk_index + content_hash)` → **upsert** gives incremental updates and no duplicates; stale chunks for a re-scraped URL deleted. |
| `app/rag/retriever.py` | Query embedding → top-k, optional `source` metadata filter (DarGlobal / Wasalt), score threshold. |
| `app/rag/prompt.py` | System prompt with grounding rules; numbered context blocks `[1] … (url)`. |
| `app/rag/generator.py` | OpenAI SDK pointed at `https://openrouter.ai/api/v1`; timeout, retry on 429/5xx, clear error types. |
| `app/services/chat_service.py` | Validate → rewrite follow-up using last turns → retrieve → build prompt → generate → attach sources. |
| `app/api/routes.py` | `GET /health`, `GET /stats`, `POST /chat`, `POST /admin/ingest` (token-protected). |
| `app/frontend/streamlit_app.py` | Chat UI; calls API only — never sees the API key. |

## Key design decisions (interview-ready)

1. **Why custom RAG instead of LangChain?** Fewer moving parts, every step is visible and testable, easy to explain. ~150 lines.
2. **Why all-MiniLM-L6-v2?** 384-dim, ~90 MB, fast on CPU, good English semantic search. Index fits in RAM; container stays small.
3. **Why ChromaDB?** Embedded (no separate server), persistent on disk, supports metadata filters.
4. **Grounding / anti-hallucination**
   - Prompt: answer *only* from context; say "not available in the collected data" otherwise; never estimate prices.
   - Retrieval threshold: if best similarity < threshold, skip the LLM and return a fixed "I don't have that information" answer (cheap, zero hallucination).
   - Sources returned come from retrieved metadata, not from the LLM's text, so URLs can't be invented.
   - `temperature=0.1`.
5. **Follow-ups:** last N turns sent to the LLM; the retrieval query is the current question + previous user question (simple, no extra LLM call), so "what about its payment plan?" still retrieves the right project.
6. **Free-model safety:** config validator only accepts `openrouter/free` or ids ending in `:free`; no fallback to paid models.
7. **Secrets:** key only in env / platform secrets; `.env` in `.gitignore` and `.dockerignore`; Streamlit never receives it.

## Deployment topology

- **Local:** `docker compose up` → two services (`api`, `ui`) from the same image, `./data` volume for Chroma persistence, healthchecks.
- **Cloud (recommended: Hugging Face Spaces, Docker SDK, free CPU tier 2 vCPU / 16 GB):** single container runs both processes (small `start.sh`: uvicorn on 8000 + Streamlit on 7860). Prebuilt Chroma index copied into the image; if missing at startup the app re-indexes from `data/processed/`, so restarts are safe even on ephemeral disk.
