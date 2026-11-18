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
        cited = {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
        ordered = [c for i, c in enumerate(chunks, 1) if i in cited] + \
                  [c for i, c in enumerate(chunks, 1) if i not in cited]
        out, seen = [], set()
        for c in ordered:
            m = c["metadata"]
            if m["url"] in seen:
                continue
            seen.add(m["url"])
            idx = chunks.index(c) + 1
            out.append({
                "title": m.get("title", ""), "url": m["url"], "source": m.get("source", ""),
                "score": c["score"], "cited": idx in cited, "page_type": m.get("page_type", ""),
                "country": m.get("country") or None, "price": m.get("price") or None,
                "extracted_at": m.get("extracted_at") or None,
            })
        return out

    def answer(self, question: str, history: list[dict] | None = None) -> dict:
        started = time.perf_counter()
        q = self.validate(question)
        history = history or []

        if GREETING_RE.match(q):
            return {"answer": GREETING_ANSWER, "sources": [], "model": None, "grounded": False,
                    "latency_ms": int((time.perf_counter() - started) * 1000)}

        chunks = self.retriever.retrieve(q, history)
        if not chunks:
            logger.info("No relevant context for question: %r", q[:120])
            return {"answer": NO_INFO_ANSWER, "sources": [], "model": None, "grounded": False,
                    "latency_ms": int((time.perf_counter() - started) * 1000)}

        messages = build_messages(q, chunks, history, self.settings.history_turns)
        gen = self.generator.generate(messages)
        return {
            "answer": gen.text,
            "sources": self.build_sources(gen.text, chunks),
            "model": gen.model,
            "grounded": True,
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
