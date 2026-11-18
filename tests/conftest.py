"""Shared fixtures. HTML fixtures here are hand-written test inputs for the parsers,
not scraped data."""
from __future__ import annotations

import hashlib
import math
import re

import pytest

from app.config import Settings
from app.ingestion.indexing import VectorIndex
from app.rag.generator import Generation

DG_PROJECT_HTML = """<!doctype html><html><head>
<title>Les Vagues by Elie Saab | DarGlobal</title>
<meta name="description" content="Beachfront residences in Marbella, Spain designed by Elie Saab.">
<link rel="canonical" href="https://darglobal.co.uk/les-vagues">
</head><body>
<nav><a>Home</a><a>Projects</a></nav>
<h1>Les Vagues by Elie Saab</h1>
<p>Luxury beachfront villas and apartments on the Costa del Sol in Marbella, Spain.</p>
<p>Prices starting from EUR 1,250,000 for two-bedroom apartments.</p>
<p>Flexible payment plan: 30/70 with 30% during construction.</p>
<h2>Amenities</h2>
<ul><li>Infinity pool</li><li>Private beach club</li><li>Spa and wellness centre</li></ul>
<h2>Key facts</h2>
<table><tr><th>Bedrooms</th><td>2 - 5</td></tr><tr><th>Handover</th><td>Q4 2027</td></tr></table>
<footer>© DarGlobal All rights reserved</footer>
</body></html>"""

WASALT_LISTING_HTML = """<!doctype html><html><head>
<title>Villa for sale in Riyadh</title>
<link rel="canonical" href="https://wasalt.sa/en/property/sale/villa-333-sqm-facing-east-on-20m-width-street-5841671">
<script type="application/ld+json">{"@type":"Product","name":"Villa","offers":{"price":"2500000","priceCurrency":"SAR"},
"address":{"addressLocality":"Riyadh","addressRegion":"Riyadh Region"},"numberOfBathroomsTotal":4}</script>
</head><body><h1>Villa 333 sqm facing east</h1>
<p>Modern villa in Al Malqa district with private garden and driver room.</p></body></html>"""

CHALLENGE_HTML = '<html><head><script src="/_Incapsula_Resource?SWJIYLWA=abc"></script></head><body></body></html>'


class FakeEmbedder:
    """Deterministic bag-of-words embedding: texts sharing words are similar."""
    dimension = 256

    def embed(self, texts):
        out = []
        for t in texts:
            v = [0.0] * self.dimension
            for w in re.findall(r"[a-z0-9]+", t.lower()):
                v[int(hashlib.md5(w.encode()).hexdigest(), 16) % self.dimension] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out

    def embed_query(self, text):
        return self.embed([text])[0]


class FakeGenerator:
    configured = True

    def __init__(self, text="Les Vagues is in Marbella, Spain [1].", exc=None):
        self.text, self.exc, self.calls = text, exc, []

    def generate(self, messages):
        self.calls.append(messages)
        if self.exc:
            raise self.exc
        return Generation(text=self.text, model="test/model:free")


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path / "data", openrouter_api_key="test-key", min_similarity=0.05,
                    chunk_size=300, chunk_overlap=50, _env_file=None)


@pytest.fixture
def fake_embedder():
    return FakeEmbedder()


@pytest.fixture
def index(tmp_path, fake_embedder):
    return VectorIndex(tmp_path / "chroma", "test", embedder=fake_embedder)


@pytest.fixture
def sample_docs():
    from app.ingestion.cleaner import clean_records
    recs = [
        {"url": "https://darglobal.co.uk/les-vagues", "source": "DarGlobal", "title": "Les Vagues by Elie Saab",
         "page_type": "project", "country": "Spain", "location": "Marbella", "price": "EUR 1,250,000",
         "amenities": ["Infinity pool", "Private beach club"],
         "description": "Luxury beachfront villas in Marbella, Spain designed by Elie Saab."},
        {"url": "https://darglobal.co.uk/aida-trump-villas", "source": "DarGlobal", "title": "AIDA Trump Villas",
         "page_type": "project", "country": "Oman", "location": "Muscat",
         "description": "Clifftop golf villas at AIDA in Muscat, Oman, with Trump-branded golf course."},
        {"url": "https://wasalt.sa/en/property/rent/apartment-120-sqm-with-3-bedrooms-123",
         "source": "Wasalt", "title": "Apartment, 120 sqm, 3 bedrooms for rent", "page_type": "listing",
         "country": "Saudi Arabia", "listing_type": "rent", "property_type": "apartment", "area_sqm": "120",
         "bedrooms": "3", "description": "Wasalt listing #123 apartment for rent with 3 bedrooms."},
    ]
    docs, _ = clean_records(recs)
    return docs
