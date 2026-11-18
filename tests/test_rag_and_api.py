from unittest.mock import MagicMock

import openai
import pytest
from fastapi.testclient import TestClient

from app.ingestion.chunker import chunk_documents
from app.rag.generator import LLMConfigError, LLMRateLimitError, LLMUnavailableError, OpenRouterGenerator
from app.rag.prompt import SYSTEM_PROMPT, build_messages
from app.rag.retriever import Retriever
from app.services.chat_service import NO_INFO_ANSWER, ChatService, QueryValidationError
from tests.conftest import FakeGenerator


@pytest.fixture
def service(index, sample_docs, settings):
    index.upsert_chunks(chunk_documents(sample_docs, 300, 50))
    return ChatService(Retriever(index, settings), FakeGenerator(), settings)


# ---------------- prompt ----------------
def test_prompt_contains_grounding_rules_context_and_history(sample_docs):
    chunks = [{"text": d["text"], "metadata": d["metadata"], "score": 0.9} for d in sample_docs[:2]]
    hist = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    msgs = build_messages("Where is Les Vagues?", chunks, hist)
    assert msgs[0]["content"] == SYSTEM_PROMPT and "ONLY" in SYSTEM_PROMPT and "Never invent" in SYSTEM_PROMPT
    assert [m["role"] for m in msgs] == ["system", "user", "assistant", "user"]
    assert "[1] Les Vagues by Elie Saab" in msgs[-1]["content"]
    assert "url: https://darglobal.co.uk/les-vagues" in msgs[-1]["content"]


# ---------------- chat service ----------------
def test_answer_has_sources_from_metadata(service):
    res = service.answer("Where is Les Vagues by Elie Saab located?")
    assert res["grounded"] and res["model"] == "test/model:free"
    assert res["sources"][0]["url"] == "https://darglobal.co.uk/les-vagues"
    assert res["sources"][0]["cited"] is True
    assert len({s["url"] for s in res["sources"]}) == len(res["sources"])


def test_hallucinated_citation_numbers_are_ignored(service):
    service.generator.text = "It costs a lot [9]."
    res = service.answer("Les Vagues price")
    assert all(s["url"].startswith("https://") for s in res["sources"])
    assert not any(s["cited"] for s in res["sources"])


def test_unknown_question_skips_llm(index, sample_docs, settings):
    index.upsert_chunks(chunk_documents(sample_docs, 300, 50))
    gen = FakeGenerator()
    svc = ChatService(Retriever(index, settings.model_copy(update={"min_similarity": 0.99})), gen, settings)
    res = svc.answer("What is the capital of Mongolia?")
    assert res["answer"] == NO_INFO_ANSWER and res["sources"] == [] and gen.calls == []


def test_greeting_skips_llm(service):
    res = service.answer("hello!")
    assert not res["grounded"] and service.generator.calls == []


@pytest.mark.parametrize("bad", ["", "   ", "???", "x" * 1001])
def test_validation(service, bad):
    with pytest.raises(QueryValidationError):
        service.answer(bad)


# ---------------- generator ----------------
def _gen(settings):
    g = OpenRouterGenerator(settings)
    g._client = MagicMock()
    return g


def test_generator_requires_key(settings):
    g = OpenRouterGenerator(settings.model_copy(update={"openrouter_api_key": ""}))
    assert not g.configured
    with pytest.raises(LLMConfigError):
        g.generate([{"role": "user", "content": "x"}])


def test_generator_maps_rate_limit(settings):
    g = _gen(settings)
    resp = MagicMock(status_code=429, headers={})
    g._client.chat.completions.create.side_effect = openai.RateLimitError("rate", response=resp, body=None)
    with pytest.raises(LLMRateLimitError):
        g.generate([{"role": "user", "content": "x"}])


def test_generator_empty_output_is_error(settings):
    g = _gen(settings)
    choice = MagicMock()
    choice.message.content = ""
    g._client.chat.completions.create.return_value = MagicMock(choices=[choice], model="m:free")
    with pytest.raises(LLMUnavailableError):
        g.generate([{"role": "user", "content": "x"}])


def test_generator_uses_configured_free_model(settings):
    g = _gen(settings)
    choice = MagicMock()
    choice.message.content = "ok"
    g._client.chat.completions.create.return_value = MagicMock(choices=[choice], model="x/y:free")
    out = g.generate([{"role": "user", "content": "x"}])
    assert out.text == "ok" and out.model == "x/y:free"
    assert g._client.chat.completions.create.call_args.kwargs["model"] == "openrouter/free"


# ---------------- API ----------------
@pytest.fixture
def client(index, sample_docs, settings, monkeypatch):
    index.upsert_chunks(chunk_documents(sample_docs, 300, 50))
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    from app.api.routes import get_settings as dep
    from app.main import create_app
    app = create_app(index=index, generator=FakeGenerator())
    app.dependency_overrides[dep] = lambda: settings
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["index_ready"] and body["llm_configured"]


def test_stats(client):
    body = client.get("/stats").json()
    assert body["by_source"]["DarGlobal"] >= 2 and "Spain" in body["countries"]


def test_chat_endpoint(client):
    r = client.post("/chat", json={"question": "Where is Les Vagues?", "history": []})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] and body["sources"][0]["url"].startswith("https://darglobal.co.uk")


def test_chat_validation_errors(client):
    assert client.post("/chat", json={}).status_code == 422
    assert client.post("/chat", json={"question": "   "}).status_code == 422
    assert client.post("/chat", json={"question": "a" * 2000}).status_code == 422


def test_chat_llm_error_mapped_to_http(client):
    client.app.state.chat_service.generator = FakeGenerator(exc=LLMRateLimitError("429"))
    r = client.post("/chat", json={"question": "Les Vagues amenities"})
    assert r.status_code == 429 and "rate-limited" in r.json()["detail"]
    assert "test-key" not in r.text


def test_admin_ingest_disabled_without_token(client):
    assert client.post("/admin/ingest").status_code == 404
