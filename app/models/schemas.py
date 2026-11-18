from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=8000)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000,
                          examples=["What amenities does Les Vagues by Elie Saab offer?"])
    history: list[ChatMessage] = Field(default_factory=list, max_length=20,
                                       description="Previous turns, oldest first, for follow-up questions.")


class Source(BaseModel):
    title: str
    url: str
    source: str
    score: float = Field(..., description="Cosine similarity of the best matching chunk (0-1).")
    cited: bool = Field(..., description="True if the answer cites this source.")
    page_type: str = ""
    country: str | None = None
    price: str | None = None
    extracted_at: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    model: str | None = Field(None, description="Model that produced the answer (None if answered without the LLM).")
    grounded: bool = Field(..., description="True if the answer was generated from retrieved context.")
    latency_ms: int


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    index_ready: bool
    chunks: int
    llm_configured: bool
    model: str


class StatsResponse(BaseModel):
    chunks: int
    documents: int
    by_source: dict[str, int]
    by_page_type: dict[str, int]
    countries: list[str]
    embedding_model: str
    llm_model: str
    scraping_summary: dict | None = None


class IngestResponse(BaseModel):
    documents: int
    chunks: int
    index: dict


class ErrorResponse(BaseModel):
    detail: str
