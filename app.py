"""Gradio interface for Hugging Face Spaces (Free CPU tier).
Enables instant 1-click deployment with public HTTPS URL.
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import gradio as gr
from app.config import get_settings
from app.ingestion.indexing import VectorIndex
from app.ingestion.pipeline import build_index
from app.rag.generator import OpenRouterGenerator
from app.rag.retriever import Retriever
from app.services.chat_service import ChatService

# Initialize RAG components
settings = get_settings()
index = VectorIndex(settings.chroma_dir, settings.collection_name, embedding_model=settings.embedding_model)

if index.count() == 0 and settings.documents_path.exists():
    print(f"Building vector index from {settings.documents_path}...")
    build_index(settings, index)

generator = OpenRouterGenerator(settings)
service = ChatService(Retriever(index, settings), generator, settings)


def chat_fn(message, history):
    # Support both tuple history [(u, b), ...] and message dicts [{"role": "user", "content": ...}, ...]
    hist = []
    if history:
        for item in history:
            if isinstance(item, dict):
                hist.append({"role": item.get("role", "user"), "content": item.get("content", "")})
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                if item[0]:
                    hist.append({"role": "user", "content": str(item[0])})
                if item[1]:
                    hist.append({"role": "assistant", "content": str(item[1])})

    try:
        res = service.answer(message, hist)
        answer = res.get("answer", "")
        sources = res.get("sources", [])
        
        if sources:
            answer += "\n\n---\n**Verified Sources:**\n"
            for s in sources[:4]:
                title = s.get("title") or "Website Reference"
                url = s.get("url") or "#"
                src = s.get("source") or "Data"
                score = s.get("score", 0)
                cited = " *(Cited)*" if s.get("cited") else ""
                answer += f"- [{title}]({url}) · *{src}* (Relevance: {score:.2f}){cited}\n"
        return answer
    except Exception as e:
        return f"An error occurred: {str(e)}"


EXAMPLES = [
    "Which countries does DarGlobal have projects in?",
    "Tell me about DaVinci Tower by Pagani in Dubai.",
    "What DarGlobal projects are available in Oman?",
    "What luxury brands does DarGlobal partner with for its branded residences?",
    "What is the starting price and payment plan for Les Vagues by Elie Saab in Spain?",
    "How many property listings does Wasalt have in total, and how many are for sale vs rent?",
    "What is the typical size of a villa listed on Wasalt?",
]

demo = gr.ChatInterface(
    fn=chat_fn,
    title="🏛️ DarGlobal & Wasalt AI Real Estate Assistant",
    description="Retrieval-Augmented Assistant built for the **DarGlobal Junior AI Engineer** technical assignment. Answers questions about DarGlobal's luxury portfolio and Wasalt's Saudi property listings using verified public website data with source citations.",
    examples=EXAMPLES,
    cache_examples=False,
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
