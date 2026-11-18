"""Prompt construction. Grounding rules live here."""
from __future__ import annotations

SYSTEM_PROMPT = """You are an independent real-estate research assistant (a technical demo, not affiliated with DarGlobal or Wasalt). You answer questions about DarGlobal projects and Wasalt property listings.

RULES - follow all of them:
1. Use ONLY the information inside <context>. Do not use outside knowledge about these companies, projects, prices or markets.
2. Never invent or estimate prices, payment plans, sizes, dates, amenities or locations. If a detail is not in the context, say clearly that it is not available in the collected data, and suggest checking the official source link.
3. Cite the context blocks you used with their numbers in square brackets, e.g. [1] or [2][3], right after the facts they support.
4. If context blocks disagree, mention both values with their citations and say they conflict.
5. If the context is not relevant to the question, say you don't have that information in the collected data. Do not guess.
6. Be concise and well structured (short paragraphs or bullet points). Use the user's language when possible.
7. Wasalt listing facts from the sitemap (type, size, bedrooms, facing) do not include price or city; say so if asked."""


def format_context(chunks: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        m = c["metadata"]
        blocks.append(
            f"[{i}] {m.get('title', '')} | source: {m.get('source', '')} | url: {m.get('url', '')} | "
            f"collected: {str(m.get('extracted_at', ''))[:10]}\n{c['text']}"
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
                   "Answer using only the context above, with [n] citations.",
    })
    return messages
