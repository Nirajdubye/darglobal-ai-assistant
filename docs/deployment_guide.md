# Deployment Guide

Target: **Hugging Face Spaces (Docker SDK, free CPU Basic: 2 vCPU / 16 GB RAM)**.

Why this platform
- Free, Docker-native, public HTTPS URL, secrets stored encrypted outside the image.
- 16 GB RAM fits PyTorch + the MiniLM embedding model comfortably (Render's free tier has 512 MB, which is too small).
- Only one public port, so `start.sh` runs FastAPI internally on `127.0.0.1:8000` and Streamlit publicly on `7860`.

Persistence: the free Space disk is ephemeral, so the Chroma index is **built into the image** (`RUN python -m scripts.ingest`). If it is ever missing at startup, the API rebuilds it from `data/processed/documents.jsonl`, so restarts are always safe. Locally, `docker compose` uses the named volume `chroma_data`.

## One-time setup (needs your account)

1. Create a free account at https://huggingface.co/join.
2. Create a Space: https://huggingface.co/new-space
   - Name: `real-estate-rag-assistant` (any name)
   - SDK: **Docker** → *Blank*
   - Hardware: **CPU basic (free)**
   - Visibility: **Public**
3. Space → **Settings → Variables and secrets → New secret**
   - `OPENROUTER_API_KEY` = your key from https://openrouter.ai/keys
   - (optional variable) `OPENROUTER_MODEL` = `openrouter/free`
4. Create an access token with **write** scope: https://huggingface.co/settings/tokens

## Push the code

```bash
cd darglobal-ai-assistant
git remote add space https://huggingface.co/spaces/<HF_USERNAME>/real-estate-rag-assistant
git push space main          # username = HF username, password = the write token
```

The Space builds the Dockerfile (~6-10 min first time) and starts on port 7860 (declared in the README front matter: `app_port: 7860`).

## Verify (from any machine)

```bash
URL=https://<HF_USERNAME>-real-estate-rag-assistant.hf.space
curl -s $URL/                                  # Streamlit page (HTML)
# API health is internal; check it through the UI sidebar ("Online") or the Space logs:
#   "Ready: N chunks, model=openrouter/free"
python -m scripts.evaluate --api http://127.0.0.1:8000   # inside the container, or locally against compose
```

## Local Docker

```bash
cp .env.example .env            # add OPENROUTER_API_KEY
docker compose up --build -d
curl -s localhost:8000/health
open http://localhost:8501      # UI
docker compose down             # index persists in volume chroma_data
```

Single-container mode (same as the Space):

```bash
docker build -t realestate-rag .
docker run --rm -p 7860:7860 --env-file .env realestate-rag
```

## Updating data

```bash
python -m scripts.scrape         # sitemaps + browser snapshots -> data/processed/documents.jsonl
python -m scripts.ingest         # incremental: only changed chunks are re-embedded
git commit -am "Refresh data" && git push space main
```

## Security notes
- `.env` is in `.gitignore` and `.dockerignore`; the key exists only as a platform secret / runtime env var.
- The Streamlit UI calls the API; it never receives the key.
- `POST /admin/ingest` is disabled unless `ADMIN_TOKEN` is set, and then requires the `X-Admin-Token` header.
- Only free models are accepted (`openrouter/free` or ids ending in `:free`); the app refuses to start with any other model.
