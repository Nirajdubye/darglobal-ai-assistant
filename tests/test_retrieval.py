import pytest

from app.ingestion.chunker import chunk_documents
from app.ingestion.indexing import VectorIndex
from app.rag.retriever import Retriever, build_search_query, detect_source_filter


def test_index_upsert_is_incremental_and_dedup(index, sample_docs):
    chunks = chunk_documents(sample_docs, 300, 50)
    first = index.upsert_chunks(chunks)
    assert first["added"] == len(chunks)
    second = index.upsert_chunks(chunks + chunks[:1])   # same content again + in-batch duplicate
    assert second["added"] == 0 and second["unchanged"] == len(chunks)
    assert index.count() == len(chunks)


def test_changed_page_replaces_stale_chunks(index, sample_docs):
    index.upsert_chunks(chunk_documents(sample_docs, 300, 50))
    url = "https://darglobal.co.uk/les-vagues"
    changed = [{**sample_docs[0], "text": sample_docs[0]["text"] + " Now with a padel court."}]
    new_chunks = chunk_documents(changed, 300, 50)
    stats = index.upsert_chunks(new_chunks)
    assert stats["stale_deleted"] >= 1
    stored = index.collection.get(where={"url": url})
    assert set(stored["ids"]) == {c["id"] for c in new_chunks}     # only the new version remains
    assert any("padel" in d for d in stored["documents"])


def test_index_persists_between_restarts(tmp_path, fake_embedder, sample_docs):
    a = VectorIndex(tmp_path / "db", "coll", embedder=fake_embedder)
    a.upsert_chunks(chunk_documents(sample_docs, 300, 50))
    n = a.count()
    b = VectorIndex(tmp_path / "db", "coll", embedder=fake_embedder)   # new client = "restart"
    assert b.count() == n > 0


def test_similarity_search_ranks_relevant_first(index, sample_docs, settings):
    index.upsert_chunks(chunk_documents(sample_docs, 300, 50))
    hits = Retriever(index, settings).retrieve("golf villas in Muscat Oman")
    assert hits[0]["metadata"]["url"] == "https://darglobal.co.uk/aida-trump-villas"
    assert hits == sorted(hits, key=lambda h: h["score"], reverse=True)


def test_source_filter(index, sample_docs, settings):
    index.upsert_chunks(chunk_documents(sample_docs, 300, 50))
    hits = Retriever(index, settings).retrieve("Wasalt apartment for rent")
    assert hits and all(h["metadata"]["source"] == "Wasalt" for h in hits)
    assert detect_source_filter("darglobal vs wasalt") is None


def test_min_similarity_threshold(index, sample_docs, settings):
    index.upsert_chunks(chunk_documents(sample_docs, 300, 50))
    strict = settings.model_copy(update={"min_similarity": 0.99})
    assert Retriever(index, strict).retrieve("quantum chromodynamics lecture notes") == []


def test_follow_up_query_rewrite():
    hist = [{"role": "user", "content": "Tell me about Les Vagues"}, {"role": "assistant", "content": "..."}]
    assert build_search_query("What is its payment plan?", hist) == "Tell me about Les Vagues What is its payment plan?"
    long_q = "Which DarGlobal projects in the United Kingdom offer apartments near Hyde Park in London"
    assert build_search_query(long_q, hist) == long_q
    assert build_search_query("hello", []) == "hello"


@pytest.mark.slow
def test_real_embedding_model_semantics():
    """Uses the real MiniLM model (downloads ~90 MB on first run)."""
    from app.ingestion.embeddings import Embedder
    e = Embedder.get("sentence-transformers/all-MiniLM-L6-v2")
    q, good, bad = e.embed(["beachfront apartment in Spain", "seaside flat on the Spanish coast",
                            "office parking regulations"])
    dot = lambda a, b: sum(x * y for x, y in zip(a, b))  # noqa: E731
    assert len(q) == 384
    assert abs(dot(q, q) - 1) < 1e-3          # normalised
    assert dot(q, good) > dot(q, bad) + 0.2
