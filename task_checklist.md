# Task Checklist

Legend: [x] done · [ ] todo · [~] in progress · [!] blocked

## Phase 0 — Discovery
- [x] Inspect workspace (no existing project; Python 3.12, Docker 29, Compose 2.40 available)
- [x] robots.txt both sites
- [x] Sitemaps both sites (DG 480 URLs; Wasalt 60k listing URLs on CDN)
- [x] Rendering / protection check (DG: Imperva; Wasalt: Cloudflare — both block plain HTTP)
- [x] website_research.md, architecture.md, implementation_plan.md
- [!] User approval of data-collection approach
- [ ] OpenRouter key in `.env` (user)
- [ ] Hosting account (user)

## Phase 1 — Skeleton
- [ ] Folder structure, config, requirements, .env.example, .gitignore, .dockerignore, git init

## Phase 2–4 — Scraping & processing (P0)
- [ ] Base fetcher (robots, rate limit, retries, timeouts, de-dup, challenge detection)
- [ ] Sitemap parsers
- [ ] Browser capture of DG pages
- [ ] Browser capture of Wasalt listings
- [ ] DG parser · [ ] Wasalt parser
- [ ] Cleaner, de-dup, raw vs processed JSON, scraping summary

## Phase 5–6 — Index & RAG (P0)
- [ ] Chunker · [ ] Embeddings · [ ] Chroma persistent upsert
- [ ] Retriever · [ ] Prompt · [ ] OpenRouter generator · [ ] Chat service w/ follow-ups

## Phase 7–8 — API & UI (P0)
- [ ] /health /stats /chat /admin/ingest
- [ ] Streamlit UI + disclaimer

## Phase 9 — Tests (P1)
- [ ] Unit tests (extraction, cleaning, chunking, embeddings, retrieval, generation, API, errors, sources)
- [ ] 15+ question evaluation · [ ] test_report.md

## Phase 10–11 — Docker & deploy (P0)
- [ ] Dockerfile, compose, healthchecks, verified locally
- [ ] Deployed · [ ] Public URL verified externally · [ ] /health verified · [ ] chat verified

## Phase 12 — Docs (P1)
- [ ] README · [ ] deployment guide
