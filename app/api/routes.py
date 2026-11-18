from __future__ import annotations

import json
import logging
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool

from app.config import Settings, get_settings
from app.ingestion.pipeline import build_index
from app.models.schemas import (ChatRequest, ChatResponse, ErrorResponse, HealthResponse, IngestResponse,
                                StatsResponse)
from app.rag.generator import LLMError
from app.services.chat_service import ChatService, QueryValidationError

logger = logging.getLogger(__name__)
router = APIRouter()


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(request: Request, settings: Settings = Depends(get_settings)):
    index = request.app.state.index
    chunks = index.count()
    llm_ok = request.app.state.chat_service.generator.configured
    return HealthResponse(status="ok" if chunks and llm_ok else "degraded", index_ready=chunks > 0,
                          chunks=chunks, llm_configured=llm_ok, model=settings.openrouter_model)


@router.get("/stats", response_model=StatsResponse, tags=["system"])
def stats(request: Request, settings: Settings = Depends(get_settings)):
    summary_path = settings.processed_dir / "scraping_summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else None
    return StatsResponse(**request.app.state.index.stats(), embedding_model=settings.embedding_model,
                         llm_model=settings.openrouter_model, scraping_summary=summary)


@router.post("/chat", response_model=ChatResponse, tags=["chat"],
             responses={422: {"model": ErrorResponse}, 429: {"model": ErrorResponse},
                        503: {"model": ErrorResponse}, 504: {"model": ErrorResponse}})
async def chat(body: ChatRequest, service: ChatService = Depends(get_chat_service)):
    history = [m.model_dump() for m in body.history]
    try:
        result = await run_in_threadpool(service.answer, body.question, history)
    except QueryValidationError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e
    except LLMError as e:
        logger.warning("LLM error (%s): %s", type(e).__name__, e)
        raise HTTPException(e.status_code, e.user_message) from e
    return ChatResponse(**result)


@router.post("/admin/ingest", response_model=IngestResponse, tags=["admin"],
             responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def admin_ingest(request: Request, x_admin_token: str = Header(default=""),
                       settings: Settings = Depends(get_settings)):
    """Re-index `data/processed/documents.jsonl` (incremental). Requires the X-Admin-Token header."""
    if not settings.admin_token:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Admin ingestion is disabled.")
    if not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid admin token.")
    result = await run_in_threadpool(build_index, settings, request.app.state.index)
    return IngestResponse(**result)
