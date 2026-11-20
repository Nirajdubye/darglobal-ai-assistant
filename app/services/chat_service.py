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
    "I do not have information about that in the collected DarGlobal or Wasalt property database. "
    "I can help answer questions regarding DarGlobal luxury developments (such as DaVinci Tower by Pagani, "
    "Trump Tower Dubai/Jeddah, W Residences, The Astera by Aston Martin, Tierra Viva, and AIDA Muscat) "
    "or Wasalt property listings across Saudi Arabia."
)
GREETING_RE = re.compile(r"^\s*(hi|hello|hey|salam|salaam|marhaba|good (morning|afternoon|evening)|thanks?( you)?|thank you)\W*$", re.I)
GREETING_ANSWER = (
    "Hello! I am your real estate AI assistant. I can answer questions about DarGlobal's luxury projects "
    "and Wasalt property listings. What would you like to know?"
)


class QueryValidationError(ValueError):
    pass


def clean_text_citations(text: str) -> str:
    """Remove [1], [2], [1][2][5] citation numbers from text for natural readability."""
    if not text:
        return text
    # Remove bracketed numbers like [1], [2], [12]
    cleaned = re.sub(r"\[\d+\]", "", text)
    # Fix any double spaces or spacing before punctuation caused by removal
    cleaned = re.sub(r" +", " ", cleaned)
    cleaned = re.sub(r" (?=[\.,:;!])", "", cleaned)
    return cleaned.strip()


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
    def build_sources(chunks: list[dict]) -> list[dict]:
        """Sources come from retrieval metadata, de-duplicated by URL."""
        if not chunks:
            return []
        out, seen = [], set()
        for c in chunks:
            m = c.get("metadata", {})
            url = m.get("url", "#")
            if url in seen:
                continue
            seen.add(url)
            out.append({
                "title": m.get("title", ""), "url": url, "source": m.get("source", ""),
                "score": c.get("score", 0.0), "page_type": m.get("page_type", ""),
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
            clean_answer = clean_text_citations(gen.text)
            return {
                "answer": clean_answer,
                "sources": self.build_sources(chunks),
                "model": gen.model,
                "grounded": True,
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }
        except Exception as e:
            logger.exception("LLM generation error: %s", e)
            titles = [c["metadata"].get("title", "") for c in chunks[:3] if c.get("metadata", {}).get("title")]
            snippet = ", ".join(titles) if titles else "luxury developments"
            fallback = (
                f"Based on the collected property data, relevant records include {snippet}. "
                "However, there was a temporary delay generating the full response. Please try asking again."
            )
            return {
                "answer": fallback,
                "sources": self.build_sources(chunks),
                "model": None,
                "grounded": True,
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }
