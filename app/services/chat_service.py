"""Orchestrates one chat turn: validate -> retrieve -> prompt -> generate -> attach sources."""
from __future__ import annotations

import logging
import re
import time

from app.config import Settings
from app.rag.generator import OpenRouterGenerator
from app.rag.prompt import build_messages
from app.rag.retriever import Retriever

logger = logging.getLogger(__name__)

NO_INFO_ANSWER = (
    "I don't have information about that in the data I collected from the public DarGlobal and Wasalt "
    "websites, so I can't answer it reliably. Try asking about a specific DarGlobal project (for example "
    "its location, amenities or payment plan) or about Wasalt property listings in Saudi Arabia."
)
GREETING_RE = re.compile(r"^\s*(hi|hello|hey|salam|salaam|marhaba|good (morning|afternoon|evening)|thanks?( you)?|thank you)\W*$", re.I)
GREETING_ANSWER = (
    "Hello! I can answer questions about DarGlobal's luxury projects and Wasalt's Saudi property listings, "
    "using information collected from their public websites. What would you like to know?"
)


class QueryValidationError(ValueError):
    pass


class ChatService:
    def __init__(self, retriever: Retriever, generator: OpenRouterGenerator, settings: Settings):
        self.retriever = retriever
        self.generator = generator
        self.settings = settings

    def validate(self, question: str) -> str:
        q = (question or "").strip()
        if not q:
            raise QueryValidationError("Question must not be empty.")
        if len(q) > self.settings.max_question_chars:
            raise QueryValidationError(f"Question is too long (max {self.settings.max_question_chars} characters).")
        if not re.search(r"\w", q):
            raise QueryValidationError("Question must contain words.")
        return q

    @staticmethod
    def build_sources(answer: str, chunks: list[dict]) -> list[dict]:
        """Sources come from retrieval metadata (never from LLM text), cited ones first, de-duplicated by URL."""
        if not chunks:
            return []
        cited = {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
        ordered = [c for i, c in enumerate(chunks, 1) if i in cited] + \
                  [c for i, c in enumerate(chunks, 1) if i not in cited]
        out, seen = [], set()
        for c in ordered:
            m = c.get("metadata", {})
            url = m.get("url", "#")
            if url in seen:
                continue
            seen.add(url)
            idx = chunks.index(c) + 1
            out.append({
                "title": m.get("title", ""), "url": url, "source": m.get("source", ""),
                "score": c.get("score", 0.0), "cited": idx in cited, "page_type": m.get("page_type", ""),
                "country": m.get("country") or None, "price": m.get("price") or None,
                "extracted_at": m.get("extracted_at") or None,
            })
        return out

    def answer(self, question: str, history: list[dict] | None = None) -> dict:
        started = time.perf_counter()
        try:
            q = self.validate(question)
        except QueryValidationError as e:
            return {
                "answer": str(e),
                "sources": [],
                "model": None,
                "grounded": False,
                "latency_ms": int((time.perf_counter() - started) * 1000)
            }

        history = history or []

        if GREETING_RE.match(q):
            return {
                "answer": GREETING_ANSWER,
                "sources": [],
                "model": None,
                "grounded": False,
                "latency_ms": int((time.perf_counter() - started) * 1000)
            }

        # 1. Retrieve with auto-recovery
        try:
            chunks = self.retriever.retrieve(q, history)
        except Exception as e:
            logger.exception("Initial retrieval failed: %s; trying connection reset...", e)
            try:
                self.retriever.index.reset_connection()
                chunks = self.retriever.retrieve(q, history)
            except Exception as e2:
                logger.exception("Fallback retrieval also failed: %s", e2)
                chunks = []

        if not chunks:
            logger.info("No relevant context for question: %r", q[:120])
            return {
                "answer": NO_INFO_ANSWER,
                "sources": [],
                "model": None,
                "grounded": False,
                "latency_ms": int((time.perf_counter() - started) * 1000)
            }

        # 2. Generate answer via OpenRouter
        try:
            messages = build_messages(q, chunks, history, self.settings.history_turns)
            gen = self.generator.generate(messages)
            return {
                "answer": gen.text,
                "sources": self.build_sources(gen.text, chunks),
                "model": gen.model,
                "grounded": True,
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }
        except Exception as e:
            logger.exception("LLM generation error: %s", e)
            # Graceful summary from retrieved chunks
            titles = [c["metadata"].get("title", "") for c in chunks[:3] if c.get("metadata", {}).get("title")]
            snippet = ", ".join(titles) if titles else "luxury developments"
            fallback = (
                f"Based on the collected property data, relevant records include {snippet}. "
                "However, there was a temporary delay generating the full response. Please try asking again."
            )
            return {
                "answer": fallback,
                "sources": self.build_sources("", chunks),
                "model": None,
                "grounded": True,
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }
