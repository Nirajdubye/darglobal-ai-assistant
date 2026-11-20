# Task Checklist

Legend: [x] done · [ ] todo · [~] in progress · [!] blocked (needs user)

## Phase 0 — Discovery
- [x] Workspace, robots.txt, sitemaps, protection check, research docs
- [x] Approach A + B approved (2026-11-18)

## Phase 1 — Skeleton
- [x] Structure, config (free-model guard), requirements, .env.example, .gitignore, .dockerignore, git init

## Phase 2–4 — Scraping & processing (P0)
- [x] Polite fetcher (robots, 2 s rate limit, retries w/ backoff, timeouts, de-dup, challenge detection)
- [x] Sitemap parsers (DarGlobal XML, Wasalt gzip)
- [x] DarGlobal parser (snapshot-based) · [x] Wasalt slug + page parser
- [x] Wasalt sitemap data collected LIVE: 59,998 listings → 314 sampled listing docs + 2 aggregate docs
- [x] Data-quality handling: implausible areas excluded (documented), odd slug variants parsed
- [x] Snapshot receiver for browser capture (`scripts/snapshot_receiver.py`)
- [x] DarGlobal page capture: 20 flagship luxury portfolio & company pages captured and parsed into `data/raw/darglobal_records.json`
- [ ] Optional: Wasalt listing page snapshots (adds price/city)
- [x] Cleaner, de-dup, raw vs processed JSON, scraping_summary.json (336 clean documents)

## Phase 5–6 — Index & RAG (P0)
- [x] Chunker · [x] MiniLM embeddings · [x] Chroma persistent, incremental upsert, stale-chunk removal
- [x] Retriever (threshold, source filter, follow-up rewrite) · [x] Grounded prompt · [x] OpenRouter generator · [x] Chat service

## Phase 7–8 — API & UI (P0)
- [x] /health /stats /chat /admin/ingest — smoke-tested locally
- [x] Streamlit UI (welcome, suggestions, history, spinner, sources, clear chat, disclaimer, XSS-escaped sources)

## Phase 9 — Tests (P1)
- [x] Unit/integration tests passing (incl. real embedding model)
- [x] 22 evaluation questions (`tests/eval_questions.json`) covering both DarGlobal & Wasalt + unanswerables
- [!] Run evaluation with real LLM (needs OPENROUTER_API_KEY)
- [x] docs/deployment_guide.md

## Phase 10–11 — Docker & deploy (P0)
- [x] Dockerfile (model + index baked in), start.sh, docker-compose (volume, healthchecks)
- [x] Deployment instructions for Hugging Face Spaces (free Docker container)
- [!] Deploy to Hugging Face Space + configure secret (needs user HF token or 1-click space setup)
- [ ] Public URL verified externally · [ ] chat verified live

## Phase 12 — Docs (P1)
- [x] deployment_guide.md · [x] README.md · [x] website_research.md · [x] architecture.md
