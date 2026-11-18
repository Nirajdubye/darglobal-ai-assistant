import pytest

from app.config import Settings, is_free_model
from app.ingestion.chunker import chunk_document, split_text
from app.ingestion.cleaner import clean_records, normalize_text, remove_boilerplate


def test_normalize_text():
    assert normalize_text("  Café  “luxury” – villas \n\n  ") == 'Café "luxury" - villas'


def test_remove_boilerplate():
    text = "Great sea views\nAccept all cookies\nRead more\nGreat sea views\n© 2026 DarGlobal"
    assert remove_boilerplate(text) == "Great sea views"


def test_clean_records_dedup_and_metadata(sample_docs):
    recs = [{"url": "https://x.com/a", "source": "DarGlobal", "title": "A", "description": "Same text " * 10}] * 2
    docs, stats = clean_records(recs)
    assert stats == {"input": 2, "empty": 0, "duplicate": 1, "output": 1}
    d = sample_docs[0]
    assert d["metadata"]["url"] == "https://darglobal.co.uk/les-vagues"
    assert "Price: EUR 1,250,000" in d["text"]
    assert all(isinstance(v, (str, int, float, bool)) for v in d["metadata"].values())  # Chroma-safe


def test_missing_fields_not_written():
    docs, _ = clean_records([{"url": "https://x.com/b", "source": "Wasalt", "title": "Villa for sale",
                              "description": "A villa listing with garden and parking available now."}])
    assert "Price:" not in docs[0]["text"] and docs[0]["metadata"]["price"] == ""


def test_split_text_respects_size_and_overlap():
    text = " ".join(f"Sentence number {i} about luxury villas." for i in range(80))
    chunks = split_text(text, chunk_size=200, overlap=40)
    assert len(chunks) > 5
    assert all(len(c) <= 200 + 5 for c in chunks)
    assert chunks[1].split()[0] in chunks[0]           # overlap carries text across


def test_split_text_validation():
    with pytest.raises(ValueError):
        split_text("abc", chunk_size=100, overlap=100)
    assert split_text("   ") == []


def test_chunks_keep_source_metadata(sample_docs):
    doc = {**sample_docs[0], "text": sample_docs[0]["text"] + "\n" + ("More details about the project. " * 60)}
    chunks = chunk_document(doc, chunk_size=300, overlap=50)
    assert len(chunks) > 2
    assert len({c["id"] for c in chunks}) == len(chunks)
    for c in chunks:
        assert c["metadata"]["url"] == "https://darglobal.co.uk/les-vagues"
        assert c["metadata"]["source"] == "DarGlobal"
    assert chunks[1]["text"].startswith("[DarGlobal] Les Vagues by Elie Saab")


def test_free_model_guard():
    assert is_free_model("openrouter/free")
    assert is_free_model("meta-llama/llama-3.3-70b-instruct:free")
    assert not is_free_model("openai/gpt-4o")
    with pytest.raises(ValueError):
        Settings(openrouter_model="openai/gpt-4-turbo", _env_file=None)
