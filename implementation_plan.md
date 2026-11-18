# Implementation Plan

Today: 2026-11-18. Deadline: 2026-11-20. Available: ~2 working days. Plan is P0-first; each phase ends with tests run.

## Project structure (changes vs. brief, and why)

Brief structure kept, plus:
- `app/scraper/fetcher.py` is folded into `base_scraper.py` (live + snapshot modes).
- `scripts/capture_urls.py` — builds the page list to capture in the browser (from sitemaps, robots-filtered).
- `scripts/evaluate.py` + `tests/eval_questions.json` — the 15+ question evaluation.
- `start.sh` — runs API + UI in one container for Hugging Face Spaces (single-port platform).
- `docs/` — test report and deployment guide.

## Phases

| # | Phase | Output | Est. |
|---|---|---|---|
| 0 | Approval of data-collection approach (see website_research.md §3) | decision | — |
| 1 | Skeleton: structure, config, requirements, .env.example, .gitignore, git init | runnable package | 0.5 h |
| 2 | Scrapers: base fetcher, sitemap parsers, robots check; URL capture list | `data/raw/urls_*.json` | 1.5 h |
| 3 | Data capture: ~45 DG project pages + ~15 DG company pages + ~100 Wasalt listings via real browser | `data/raw/html/` | 1.5–2 h |
| 4 | Parsers + cleaner → `documents.jsonl`, scraping summary | `data/processed/`, `scraping_summary.json` | 1.5 h |
| 5 | Chunker, embeddings, Chroma indexing (upsert, de-dup, persist) | `data/chroma_db/` | 1 h |
| 6 | RAG: retriever, prompt, OpenRouter generator, chat service | CLI answers | 1.5 h |
| 7 | FastAPI endpoints + error handling + logging | `/docs` works | 1 h |
| 8 | Streamlit UI | local chat works | 1.5 h |
| 9 | Tests (pytest, mocked LLM) + 15-question live evaluation | test_report.md | 1.5 h |
| 10 | Docker + compose, verify in container | image runs | 1 h |
| 11 | Deploy (HF Spaces), set secret, verify public URL externally | live URL | 1 h |
| 12 | README, deployment guide | docs | 1 h |

Total ≈ 15 h → feasible by 20 Nov if phase 3 isn't blocked. Fallback if browser capture is blocked: ship with Wasalt sitemap data + whatever DG pages were captured, and document the limitation.

## What I need from you

1. **Approve data-collection approach A + B** (browser-assisted snapshots + sitemap metadata), or choose another.
2. **OpenRouter API key** — create at https://openrouter.ai/keys, put it in `darglobal-ai-assistant/.env` yourself (`OPENROUTER_API_KEY=...`). Don't paste it in chat. Note: free tier ≈ 50 requests/day without credits (1000/day after a one-time $10 credit purchase — optional, not required).
3. **Hugging Face account** (free) + an access token with write scope for deployment — or pick another host.
4. For browser capture: Standard browser session snapshots (or saving rendered HTML pages manually).

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Bot protection blocks even browser capture / CAPTCHAs | Less data | You solve CAPTCHAs manually; sitemap data as fallback; document honestly |
| OpenRouter free model rate-limit / outage during demo | Chat errors | Retry w/ backoff, friendly error, `openrouter/free` router picks any available free model; low-similarity questions answered without LLM |
| Free models vary in quality | Weaker answers | Strict prompt, low temperature, sources from metadata |
| HF Space sleeps after inactivity | Slow first load (~1 min) | Mention in README; ping before submitting |
| Image size (torch) | Slow build | CPU-only torch wheel; model downloaded at build time |
| Data staleness | Old prices | Extraction timestamp shown with every source |
| Affiliation confusion | Legal/ethics | UI + README disclaimer: independent demo, not affiliated |

## Deadline estimate

Achievable by 20 Nov **if** the data-collection decision is made today. Critical path: data capture (phase 3) → everything else is standard engineering.
