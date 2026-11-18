"""DarGlobal (darglobal.co.uk) scraper.

URL discovery: the public sitemap (live, allowed by robots.txt).
Content: browser snapshots (the site is behind Imperva bot protection).
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from app.scraper.base_scraper import BaseScraper, PropertyRecord, clean_text, normalize_url

BASE = "https://darglobal.co.uk"
SITEMAP = f"{BASE}/sitemap.xml"

# Non-property pages that are still useful company knowledge.
COMPANY_PATHS = {
    "/", "/about", "/faq", "/why-invest", "/hospitality", "/commercial", "/development-management",
    "/luxury-golf-communities", "/tokenization", "/invest-crypto", "/projects", "/one-of-one",
    "/partners", "/investor", "/dg-circle", "/exclusive-membership", "/insignia", "/live-all-in",
}
# Pages with no property knowledge (forms, legal, payments, careers, thank-you pages...).
EXCLUDED_PATHS = {
    "/pay-online", "/pay-online/status", "/thank-you", "/success", "/bookyourunit", "/careers",
    "/internships", "/internship-application", "/become-a-broker", "/become-an-agent", "/get-in-touch",
    "/privacy-policy", "/terms-conditions", "/terms-of-uses", "/broker-contest-terms-conditions",
    "/landingpage/newstaticlandingpagehtml", "/new-home-page", "/landing-page", "/campaigns",
    "/win-a-trip-to-dubai", "/blog", "/press", "/insights", "/aston-martin-media",
}
ARTICLE_PREFIXES = ("/blog/", "/press/", "/insights/")

COUNTRY_KEYWORDS = {
    "United Arab Emirates": ["dubai", "abu dhabi", "uae", "united arab emirates", "jumeirah", "business bay"],
    "Oman": ["oman", "muscat", "aida"],
    "Saudi Arabia": ["saudi", "jeddah", "riyadh", "ksa"],
    "Qatar": ["qatar", "doha", "simaisma", "rayana"],
    "United Kingdom": ["london", "united kingdom", " uk ", "mayfair", "knightsbridge", "albert hall"],
    "Spain": ["spain", "marbella", "sotogrande", "costa del sol", "andalusia", "la collina"],
    "Maldives": ["maldives"],
}
URL_COUNTRY = {
    "properties-in-uae": "United Arab Emirates", "properties-in-uk": "United Kingdom",
    "properties-in-spain": "Spain", "properties-in-oman": "Oman", "properties-in-qatar": "Qatar",
    "properties-in-saudi-arabia": "Saudi Arabia", "aida": "Oman", "rayana": "Qatar",
    "trump-tower-jeddah": "Saudi Arabia", "trump-plaza": "Saudi Arabia",
}
PROPERTY_TYPES = ["penthouse", "villa", "mansion", "apartment", "townhouse", "plot", "hotel room",
                  "residence", "studio", "duplex", "branded residence", "serviced apartment"]

PRICE_RE = re.compile(
    r"(?:starting (?:price|from)|prices? (?:start(?:ing)?|from)|from|starting at)\s*:?\s*"
    r"((?:AED|USD|US\$|\$|GBP|£|EUR|€|SAR|OMR|QAR)\s?[\d.,]+\s?(?:million|m|k|bn)?)",
    re.I,
)
PAYMENT_RE = re.compile(
    r"([^.\n]{0,80}(?:payment plan|\d{1,2}\s?/\s?\d{1,2}\b|post[- ]handover|down ?payment|instal?ments?)[^.\n]{0,120})",
    re.I,
)
SECTION_HINTS = {"amenities": ("amenit", "facilit", "lifestyle"), "features": ("feature", "highlight", "key fact")}


def classify(path: str) -> str | None:
    p = path.lower().rstrip("/") or "/"
    if p in EXCLUDED_PATHS:
        return None
    if p.startswith(ARTICLE_PREFIXES):
        return "article"
    if p.startswith("/partners/"):
        return "partner"
    if p in COMPANY_PATHS or p.startswith("/projects"):
        return "company"
    return "project"


class DarGlobalScraper(BaseScraper):
    source = "DarGlobal"
    site_key = "darglobal"

    def discover_urls(self, include_articles: int = 0) -> list[dict]:
        """Sitemap URLs in scope, robots-filtered. Articles are optional (there are 360+)."""
        entries = self.fetcher.get_sitemap_urls(SITEMAP)
        out, articles = [], 0
        for e in entries:
            kind = classify(urlparse(e["loc"]).path)
            if kind is None or not self.fetcher.allowed(e["loc"]):
                continue
            if kind == "article":
                if articles >= include_articles:
                    continue
                articles += 1
            out.append({**e, "page_type": kind})
        return out

    def parse_page(self, html: str, url: str) -> PropertyRecord | None:
        url = normalize_url(url)
        path = urlparse(url).path
        page_type = classify(path)
        if page_type is None:
            return None
        soup = self.soup(html)

        h1 = soup.find("h1")
        title = clean_text(h1.get_text(" ")) if h1 else None
        og_title = self.meta(soup, "og:title")
        page_title = clean_text(soup.title.get_text()) if soup.title else None
        title = title or og_title or page_title or path.strip("/").replace("-", " ").title()
        description = self.meta(soup, "description", "og:description")
        body = self.main_text(soup)
        if len(body) < 80 and not description:
            return None  # empty shell page, nothing to learn from
        haystack = f" {title} {description or ''} {body} ".lower()

        rec = PropertyRecord(url=url, source=self.source, title=title, page_type=page_type,
                             description=description, body_text=body)
        rec.country = self._country(path, haystack)
        if page_type in ("project", "company"):
            rec.property_type = self._property_types(haystack)
            m = PRICE_RE.search(body)
            rec.price = clean_text(m.group(1)) if m else None
            plans = {clean_text(x) for x in PAYMENT_RE.findall(body) if "plan" in x.lower() or "/" in x}
            rec.payment_plan = "; ".join(sorted(plans)[:3]) or None
            rec.location = self._location(haystack)
            rec.amenities = self._section_items(soup, SECTION_HINTS["amenities"])
            rec.features = self._section_items(soup, SECTION_HINTS["features"])
            rec.specifications = self._specs(soup)
        return rec

    # ---------- helpers ----------
    @staticmethod
    def _country(path: str, haystack: str) -> str | None:
        for key, country in URL_COUNTRY.items():
            if key in path.lower():
                return country
        hits = {c: sum(haystack.count(k) for k in kws) for c, kws in COUNTRY_KEYWORDS.items()}
        best = max(hits, key=hits.get)
        return best if hits[best] > 0 else None

    @staticmethod
    def _location(haystack: str) -> str | None:
        places = ["Dubai", "Business Bay", "Jumeirah", "Abu Dhabi", "Muscat", "Jeddah", "Riyadh", "Doha",
                  "Simaisma", "London", "Mayfair", "Marbella", "Sotogrande", "Costa del Sol", "Maldives", "AIDA"]
        found = [p for p in places if p.lower() in haystack]
        return ", ".join(found[:3]) or None

    @staticmethod
    def _property_types(haystack: str) -> str | None:
        found = [t for t in PROPERTY_TYPES if re.search(rf"\b{t}s?\b", haystack)]
        return ", ".join(found[:4]) or None

    @staticmethod
    def _section_items(soup, hints: tuple[str, ...]) -> list[str]:
        """Collect list items/short lines that follow a heading such as 'Amenities'."""
        items: list[str] = []
        for heading in soup.find_all(["h2", "h3", "h4", "h5"]):
            if not any(h in heading.get_text(" ").lower() for h in hints):
                continue
            for sib in heading.find_all_next(limit=60):
                if sib.name in ("h1", "h2", "h3") and sib is not heading:
                    break
                if sib.name in ("li", "p", "span", "h4", "h5", "h6"):
                    t = clean_text(sib.get_text(" "))
                    if 2 < len(t) <= 80 and t not in items:
                        items.append(t)
            if items:
                break
        return items[:30]

    @staticmethod
    def _specs(soup) -> dict[str, str]:
        """Key/value pairs from tables and <dl> lists (bedrooms, sizes, handover...)."""
        specs: dict[str, str] = {}
        for row in soup.find_all("tr"):
            cells = [clean_text(c.get_text(" ")) for c in row.find_all(["th", "td"])]
            if len(cells) == 2 and cells[0] and cells[1] and len(cells[0]) < 40:
                specs[cells[0]] = cells[1][:120]
        for dl in soup.find_all("dl"):
            for dt, dd in zip(dl.find_all("dt"), dl.find_all("dd")):
                specs[clean_text(dt.get_text())] = clean_text(dd.get_text(" "))[:120]
        return dict(list(specs.items())[:25])
