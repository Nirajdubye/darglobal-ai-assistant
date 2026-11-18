# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    ANONYMIZED_TELEMETRY=False \
    API_URL=http://127.0.0.1:8000 \
    PORT=7860

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake the embedding model into the image (no download at startup).
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY app ./app
COPY scripts ./scripts
COPY data/processed ./data/processed
COPY start.sh ./
COPY .streamlit ./.streamlit

# Build the vector index at image build time so the container starts ready.
RUN python -m scripts.ingest && chmod +x start.sh && chown -R appuser:appuser /app
USER appuser

EXPOSE 7860 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# Default: API + UI in one container (Hugging Face Spaces). docker-compose overrides per service.
CMD ["./start.sh"]
