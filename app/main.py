"""FastAPI application entry point: `uvicorn app.main:app`."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import get_settings
from app.ingestion.indexing import VectorIndex
from app.ingestion.pipeline import build_index
from app.rag.generator import OpenRouterGenerator
from app.rag.retriever import Retriever
from app.services.chat_service import ChatService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")


def create_app(index: VectorIndex | None = None, generator: OpenRouterGenerator | None = None) -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        idx = index or VectorIndex(settings.chroma_dir, settings.collection_name,
                                   embedding_model=settings.embedding_model)
        if idx.count() == 0 and settings.documents_path.exists():
            logger.info("Index empty - building from %s", settings.documents_path)
            build_index(settings, idx)
        gen = generator or OpenRouterGenerator(settings)
        if not gen.configured:
            logger.warning("OPENROUTER_API_KEY is not set - /chat will return 503 for questions needing the LLM")
        idx.embedder  # warm up the embedding model so the first request is fast
        app.state.index = idx
        app.state.chat_service = ChatService(Retriever(idx, settings), gen, settings)
        logger.info("Ready: %d chunks, model=%s", idx.count(), settings.openrouter_model)
        yield

    app = FastAPI(
        title="Real Estate RAG Assistant API",
        description="Answers questions about DarGlobal projects and Wasalt listings using retrieval-augmented "
                    "generation over publicly available website data. Independent technical demo - not "
                    "affiliated with DarGlobal or Wasalt.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(router)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        msg = "; ".join(f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors())
        return JSONResponse(status_code=422, content={"detail": msg or "Invalid request"})

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

    return app


app = create_app()
