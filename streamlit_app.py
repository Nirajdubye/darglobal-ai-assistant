"""DarGlobal & Wasalt Real Estate AI Assistant - Streamlit App."""
from __future__ import annotations

import html
import os
import sys
from pathlib import Path

# SQLite compatibility for Linux (Streamlit Community Cloud)
try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import requests
import streamlit as st

# Forward Streamlit secrets to environment variables
try:
    if hasattr(st, "secrets"):
        for k, v in st.secrets.items():
            if isinstance(v, str) and k not in os.environ:
                os.environ[k] = v
except Exception:
    pass

# Ensure project root in sys.path
root = Path(__file__).resolve().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(page_title="DarGlobal & Wasalt AI Assistant", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

# Top header with Title and Clear Chat
col_title, col_btn = st.columns([6, 1])
with col_title:
    st.title("DarGlobal & Wasalt AI Assistant")
with col_btn:
    st.write("")
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


@st.cache_resource(show_spinner=False)
def get_local_service():
    try:
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
        st.error(f"Error loading assistant backend: {e}")
        return None, None, None


def ask(question: str, history: list[dict]) -> dict:
    if API_URL and API_URL != "http://localhost:8000":
        try:
            r = requests.post(f"{API_URL}/chat", json={"question": question, "history": history}, timeout=10)
            if r.ok:
                return r.json()
        except requests.RequestException:
            pass

    svc, _, _ = get_local_service()
    if svc:
        try:
            return svc.answer(question, history)
        except Exception as e:
            return {"error": str(e)}
    return {"error": "Assistant service is initializing. Please try again in a moment."}


def render_sources(sources: list[dict]) -> None:
    if not sources:
        return
    with st.expander(f"Sources ({len(sources)})", expanded=False):
        for s in sources:
            esc = html.escape
            url = s.get("url", "#")
            title = s.get("title") or url
            source_name = s.get("source", "Real Estate")
            st.markdown(f"- **[{source_name}]** [{esc(title)}]({esc(url)})")


# Sidebar (minimal)
with st.sidebar:
    if st.button("🗑️ Clear Chat", use_container_width=True, key="sidebar_clear"):
        st.session_state.messages = []
        st.rerun()

# Chat Messages History
if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if m.get("error"):
            st.error(m["content"])
        else:
            st.markdown(m["content"])
            if m.get("sources"):
                render_sources(m["sources"])

# User Chat Input
question = st.chat_input("Ask a question about DarGlobal or Wasalt properties...")
if question:
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
        if not m.get("error")
    ][-8:]
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            res = ask(question, history)
        if "error" in res:
            st.error(res["error"])
            st.session_state.messages.append({"role": "assistant", "content": res["error"], "error": True})
        else:
            st.markdown(res["answer"])
            if res.get("sources"):
                render_sources(res["sources"])
            st.session_state.messages.append(
                {"role": "assistant", "content": res["answer"], "sources": res.get("sources", [])}
            )
