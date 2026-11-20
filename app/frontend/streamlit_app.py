"""Streamlit chat UI. Talks to the FastAPI backend only - it never sees the OpenRouter key."""
from __future__ import annotations

import html
import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 120

SUGGESTED = [
    "Which countries does DarGlobal have projects in?",
    "Tell me about DarGlobal's branded residences with luxury partners.",
    "What DarGlobal projects are available in Oman?",
    "How many properties are listed on Wasalt for rent vs for sale?",
    "What is the typical size of a villa listed on Wasalt?",
    "Which Saudi cities does Wasalt cover?",
]
WELCOME = (
    "Welcome! I'm a real estate research assistant. Ask me about **DarGlobal** luxury projects "
    "(UAE, Oman, Saudi Arabia, Qatar, UK, Spain) or **Wasalt** property listings in Saudi Arabia. "
    "Every answer is based on information collected from their public websites, with source links."
)

st.set_page_config(page_title="Real Estate AI Assistant", page_icon="🏛️", layout="wide")

st.markdown("""
<style>
:root { --gold: #b8975a; --ink: #1c1c1c; }
.block-container { padding-top: 1.6rem; max-width: 1100px; }
.hero { border-bottom: 1px solid rgba(184,151,90,.45); padding-bottom: .8rem; margin-bottom: 1rem; }
.hero h1 { font-family: Georgia, 'Times New Roman', serif; font-weight: 500; letter-spacing: .5px; margin: 0; font-size: 2.05rem; }
.hero p { color: #7a7a7a; margin: .25rem 0 0; font-size: .95rem; }
.gold { color: var(--gold); }
.src { border-left: 3px solid var(--gold); padding: .35rem .7rem; margin: .35rem 0; background: rgba(184,151,90,.07); border-radius: 4px; font-size: .88rem; }
.src a { text-decoration: none; font-weight: 600; }
.src small { color: #888; }
.badge { display:inline-block; padding: 1px 8px; border-radius: 10px; font-size: .72rem; margin-right: 6px; background: rgba(184,151,90,.18); }
.disclaimer { font-size: .78rem; color: #888; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_local_service():
    try:
        import json
        from app.config import get_settings
        from app.ingestion.indexing import VectorIndex
        from app.ingestion.pipeline import build_index
        from app.rag.generator import OpenRouterGenerator
        from app.rag.retriever import Retriever
        from app.services.chat_service import ChatService
        s = get_settings()
        idx = VectorIndex(s.chroma_dir, s.collection_name, embedding_model=s.embedding_model)
        if idx.count() == 0 and s.documents_path.exists():
            build_index(s, idx)
        gen = OpenRouterGenerator(s)
        svc = ChatService(Retriever(idx, s), gen, s)
        return svc, idx, s
    except Exception as e:
        return None, None, None


@st.cache_data(ttl=60, show_spinner=False)
def fetch(path: str):
    try:
        r = requests.get(f"{API_URL}{path}", timeout=2)
        if r.ok:
            return r.json()
    except requests.RequestException:
        pass
    
    svc, idx, s = get_local_service()
    if idx:
        if path == "/health":
            chunks = idx.count()
            llm_ok = svc.generator.configured if svc else False
            return {
                "status": "ok" if chunks and llm_ok else "degraded",
                "index_ready": chunks > 0,
                "chunks": chunks,
                "llm_configured": llm_ok,
                "model": s.openrouter_model,
            }
        elif path == "/stats":
            summary_path = s.processed_dir / "scraping_summary.json"
            import json
            summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else None
            return {
                **idx.stats(),
                "embedding_model": s.embedding_model,
                "llm_model": s.openrouter_model,
                "scraping_summary": summary,
            }
    return None


def ask(question: str, history: list[dict]) -> dict:
    try:
        r = requests.post(f"{API_URL}/chat", json={"question": question, "history": history}, timeout=10)
        if r.ok:
            return r.json()
    except requests.RequestException:
        pass
    
    # In-process fallback for standalone Streamlit execution
    svc, _, _ = get_local_service()
    if svc:
        try:
            return svc.answer(question, history)
        except Exception as e:
            return {"error": str(e)}
    return {"error": "Cannot reach the assistant backend. Please verify your OPENROUTER_API_KEY."}


def render_sources(sources: list[dict]) -> None:
    if not sources:
        return
    with st.expander(f"Sources ({len(sources)})", expanded=False):
        for s in sources:
            esc = html.escape
            url = s["url"] if s["url"].startswith(("https://", "http://")) else "#"
            badge = f"<span class='badge'>{esc(s['source'])}</span>"
            cited = " · cited" if s.get("cited") else ""
            extra = esc(" · ".join(x for x in [s.get("country"), s.get("price")] if x))
            date = esc((s.get("extracted_at") or "")[:10])
            st.markdown(
                f"<div class='src'>{badge}<a href='{esc(url, quote=True)}' target='_blank' rel='noopener'>{esc(s['title'])}</a><br>"
                f"<small>{extra + ' · ' if extra else ''}relevance {s['score']:.2f}{cited}"
                f"{' · collected ' + date if date else ''}</small></div>",
                unsafe_allow_html=True)


# ---------------- sidebar ----------------
with st.sidebar:
    st.markdown("### <span class='gold'>◆</span> About", unsafe_allow_html=True)
    st.write("Retrieval-augmented assistant over public DarGlobal and Wasalt website data.")
    health = fetch("/health")
    if health:
        ok = health["status"] == "ok"
        st.markdown(f"**Status:** {'🟢 Online' if ok else '🟠 Degraded'}")
        st.caption(f"{health['chunks']:,} indexed chunks · model `{health['model']}`")
    else:
        st.markdown("**Status:** 🔴 Backend unreachable")
    stats = fetch("/stats")
    if stats:
        cols = st.columns(2)
        for i, (src, n) in enumerate(sorted(stats["by_source"].items())):
            cols[i % 2].metric(f"{src} chunks", f"{n:,}")
        if stats.get("countries"):
            st.caption("Countries: " + ", ".join(stats["countries"]))
    st.divider()
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.markdown("<p class='disclaimer'>Independent technical demonstration built for a job application. "
                "Not affiliated with, endorsed by, or operated by DarGlobal or Wasalt. Information may be "
                "outdated - always verify on the official websites.</p>", unsafe_allow_html=True)

# ---------------- main ----------------
st.markdown("<div class='hero'><h1>Real Estate <span class='gold'>AI</span> Assistant</h1>"
            "<p>DarGlobal projects &amp; Wasalt listings — answers grounded in public website data</p></div>",
            unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.chat_message("assistant", avatar="🏛️"):
    st.markdown(WELCOME)

pending = None
if not st.session_state.messages:
    st.markdown("**Try asking:**")
    cols = st.columns(3)
    for i, q in enumerate(SUGGESTED):
        if cols[i % 3].button(q, key=f"sugg{i}", use_container_width=True):
            pending = q

for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar="🏛️" if m["role"] == "assistant" else "👤"):
        if m.get("error"):
            st.error(m["content"])
        else:
            st.markdown(m["content"])
            render_sources(m.get("sources", []))

typed = st.chat_input("Ask about a project, location, amenities, payment plans, listings…")
question = typed or pending
if question:
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages
               if not m.get("error")][-8:]
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="👤"):
        st.markdown(question)
    with st.chat_message("assistant", avatar="🏛️"):
        with st.spinner("Searching the collected data…"):
            res = ask(question, history)
        if "error" in res:
            st.error(res["error"])
            st.session_state.messages.append({"role": "assistant", "content": res["error"], "error": True})
        else:
            st.markdown(res["answer"])
            render_sources(res.get("sources", []))
            st.session_state.messages.append({"role": "assistant", "content": res["answer"],
                                              "sources": res.get("sources", [])})
