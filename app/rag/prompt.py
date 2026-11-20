"""Prompt construction. Grounding rules live here."""
from __future__ import annotations

SYSTEM_PROMPT = """You are a knowledgeable real estate assistant for DarGlobal and Wasalt.

RULES:
1. Use ONLY the information provided in the context below. Do not assume or fabricate prices, dates, amenities, or locations.
2. If the question asks for information not contained in the context, politely state that the specific details are not available in the current portfolio data.
3. Write clear, natural, well-formatted responses (using bullet points or concise paragraphs where appropriate).
4. Do NOT output bracketed citation numbers like [1], [2], or [3] in your response text. Sources are displayed separately.
5. If the user asks about Wasalt sitemap data (property type, area in sqm, bedrooms, orientation), explain that specific pricing and descriptions may require checking the direct listing link."""


def format_context(chunks: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        m = c.get("metadata", {})
        blocks.append(
            f"Document {i}: {m.get('title', '')} | Source: {m.get('source', '')} | URL: {m.get('url', '')}\n{c.get('text', '')}"
        )
    return "\n\n---\n\n".join(blocks)


def build_messages(question: str, chunks: list[dict], history: list[dict] | None = None,
                   history_turns: int = 4) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in (history or [])[-history_turns * 2:]:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            messages.append({"role": m["role"], "content": m["content"][:2000]})
    messages.append({
        "role": "user",
        "content": f"<context>\n{format_context(chunks)}\n</context>\n\nQuestion: {question}\n\n"
                   "Answer clearly using only the provided context. Do not include bracket citation numbers like [1] or [2].",
    })
    return messages
