import gzip
import urllib.robotparser
from unittest.mock import MagicMock

import pytest

from app.scraper.base_scraper import (BotChallengeError, PoliteFetcher, is_challenge_page, normalize_url,
                                      parse_sitemap_xml, snapshot_url)
from app.scraper.darglobal_scraper import DarGlobalScraper, classify
from app.scraper.wasalt_scraper import WasaltScraper, city_of, parse_listing_slug
from tests.conftest import CHALLENGE_HTML, DG_PROJECT_HTML, WASALT_LISTING_HTML


def test_normalize_url_dedup():
    assert normalize_url("https://DarGlobal.co.uk/les-vagues/#gallery") == "https://darglobal.co.uk/les-vagues"


def test_challenge_detection():
    assert is_challenge_page(CHALLENGE_HTML)
    assert is_challenge_page("<title>Just a moment...</title><script>window._cf_chl_opt={}</script>")
    assert not is_challenge_page(DG_PROJECT_HTML)


def test_sitemap_parsing_dedups():
    xml = b"""<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://a.com/x</loc><lastmod>2026-11-01</lastmod></url>
    <url><loc>https://a.com/x/</loc></url><url><loc>https://a.com/y</loc></url></urlset>"""
    out = parse_sitemap_xml(xml)
    assert [u["loc"] for u in out] == ["https://a.com/x", "https://a.com/y"]
    assert out[0]["lastmod"] == "2026-11-01"


def test_fetcher_reads_gzip_sitemap_and_detects_challenge():
    f = PoliteFetcher(delay=0)
    f.allowed = lambda url: True
    xml = b'<urlset><url><loc>https://wasalt.sa/en/a</loc></url></urlset>'
    ok = MagicMock(status_code=200, content=gzip.compress(xml), text="")
    f.session.get = MagicMock(return_value=ok)
    assert f.get_sitemap_urls("https://cdn.wasalt.sa/s.xml.gz")[0]["loc"] == "https://wasalt.sa/en/a"

    blocked = MagicMock(status_code=403, text="<title>Just a moment...</title> cf_chl_opt")
    f.session.get = MagicMock(return_value=blocked)
    with pytest.raises(BotChallengeError):
        f.get("https://wasalt.sa/en")


def test_fetcher_respects_robots():
    f = PoliteFetcher(delay=0)
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(["User-agent: *", "Disallow: /search"])
    f._robots["https://wasalt.sa"] = rp
    assert not f.allowed("https://wasalt.sa/search?q=villa")
    with pytest.raises(PermissionError):
        f.get("https://wasalt.sa/search?q=villa")


def test_snapshot_url_sources():
    assert snapshot_url("<!-- source-url: https://darglobal.co.uk/neptune captured-at: x -->") == "https://darglobal.co.uk/neptune"
    assert snapshot_url("<!-- saved from url=(0035)https://darglobal.co.uk/w-residences -->") == "https://darglobal.co.uk/w-residences"
    assert snapshot_url(DG_PROJECT_HTML) == "https://darglobal.co.uk/les-vagues"


def test_darglobal_classification():
    assert classify("/les-vagues") == "project"
    assert classify("/blog/some-post") == "article"
    assert classify("/partners/pagani") == "partner"
    assert classify("/about") == "company"
    assert classify("/pay-online") is None


def test_darglobal_project_extraction():
    rec = DarGlobalScraper(fetcher=MagicMock()).parse_page(DG_PROJECT_HTML, "https://darglobal.co.uk/les-vagues")
    assert rec.title == "Les Vagues by Elie Saab"
    assert rec.country == "Spain"
    assert "Marbella" in rec.location
    assert rec.price == "EUR 1,250,000"
    assert "30/70" in rec.payment_plan
    assert "Infinity pool" in rec.amenities
    assert rec.specifications.get("Handover") == "Q4 2027"
    assert "villa" in rec.property_type
    assert "All rights reserved" not in rec.body_text  # footer removed


def test_darglobal_missing_fields_stay_none():
    html = "<html><head><link rel='canonical' href='https://darglobal.co.uk/neptune'></head><body><h1>Neptune</h1>" \
           "<p>An exclusive residential tower with sea views and premium finishes throughout every home.</p></body></html>"
    rec = DarGlobalScraper(fetcher=MagicMock()).parse_page(html, "https://darglobal.co.uk/neptune")
    assert rec.price is None and rec.payment_plan is None and rec.amenities == []


def test_wasalt_slug_parsing():
    f = parse_listing_slug("https://wasalt.sa/en/property/sale/villa-333-sqm-facing-east-on-20m-width-street-5841671")
    assert f == {"listing_id": "5841671", "listing_type": "sale", "property_type": "villa", "area_sqm": 333,
                 "bedrooms": None, "facing": "east", "street_width_m": 20}
    g = parse_listing_slug("https://wasalt.sa/en/property/rent/apartment-50-sqm-with-1-bedroom-5896837")
    assert (g["property_type"], g["area_sqm"], g["bedrooms"], g["listing_type"]) == ("apartment", 50, 1, "rent")
    assert parse_listing_slug("https://wasalt.sa/en/s/privacy-policy") is None


def test_wasalt_city_parsing():
    assert city_of("al-khobar-al-aqrabiyah") == "Al Khobar"
    assert city_of("riyadh") == "Riyadh"
    assert city_of("unknown-place") is None


def test_wasalt_listing_page_structured_data():
    url = "https://wasalt.sa/en/property/sale/villa-333-sqm-facing-east-on-20m-width-street-5841671"
    rec = WasaltScraper(fetcher=MagicMock()).parse_page(WASALT_LISTING_HTML, url)
    assert rec.price == "SAR 2500000"
    assert rec.city == "Riyadh"
    assert rec.bathrooms == "4"
    assert rec.area_sqm == "333" and rec.listing_type == "sale"


def test_wasalt_sitemap_records_and_summary():
    w = WasaltScraper(fetcher=MagicMock())
    entries = [{"loc": f"https://wasalt.sa/en/property/sale/villa-{300 + i}-sqm-{1000 + i}", "lastmod": "2026-11-16"}
               for i in range(5)]
    entries += [{"loc": "https://wasalt.sa/en/property/rent/apartment-with-2-bedrooms-2000", "lastmod": "2026-11-16"}]
    df = w.listings_frame(entries)
    recs = w.sitemap_listing_records(df, sample_per_group=2)
    assert len(recs) == 3 and all(r.extraction_method == "sitemap" for r in recs)
    assert all(r.price is None for r in recs)  # sitemap has no prices - must not be invented
    summary = w.market_summary_records(df, [{"loc": "https://wasalt.sa/en/villas-for-sale-in-riyadh-al-malqa"}])
    assert "6 English-language property listings" in summary[0].body_text
    assert "Riyadh" in summary[1].body_text


def test_snapshot_pipeline_skips_challenge_and_duplicates(monkeypatch, settings):
    monkeypatch.setattr("app.scraper.base_scraper.get_settings", lambda: settings)
    d = settings.html_dir / "darglobal"
    d.mkdir(parents=True)
    (d / "a.html").write_text(DG_PROJECT_HTML)
    (d / "b.html").write_text(DG_PROJECT_HTML)          # duplicate URL
    (d / "c.html").write_text(CHALLENGE_HTML)           # challenge page
    s = DarGlobalScraper(fetcher=MagicMock())
    recs = s.scrape_snapshots()
    assert len(recs) == 1
    assert s.stats["skipped_duplicate"] == 1 and s.stats["skipped_challenge"] == 1


def test_wasalt_bedroom_first_slug_and_implausible_area():
    from app.scraper.wasalt_scraper import plausible_area
    f = parse_listing_slug("https://wasalt.sa/en/property/rent/3-bedrooms-apartment-rent-5883115")
    assert (f["property_type"], f["bedrooms"], f["listing_type"]) == ("apartment", 3, "rent")
    assert plausible_area("apartment", 120) and not plausible_area("apartment", 54387)
    assert plausible_area("land", 54387)
