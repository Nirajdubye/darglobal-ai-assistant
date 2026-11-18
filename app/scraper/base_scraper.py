"""Shared scraping infrastructure.

Two ways to obtain HTML:

* **live**     - polite HTTP fetch with robots.txt check, rate limiting, retries and
                 bot-challenge detection. Used for robots.txt and sitemaps.
* **snapshot** - HTML pages captured in a normal browser session and saved to
                 ``data/raw/html/<site>/``. Both DarGlobal (Imperva) and Wasalt
                 (Cloudflare) serve a bot challenge to plain HTTP clients, and we do
                 not circumvent it, so page content comes from these snapshots.

Site-specific scrapers only implement ``parse_page``; everything else lives here.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
import re
import time
import urllib.robotparser
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urlparse

import requests
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = logging.getLogger(__name__)

CHALLENGE_MARKERS = (
    "_Incapsula_Resource",          # Imperva
    "cf_chl_opt",                   # Cloudflare managed challenge
    "challenges.cloudflare.com",
    "Just a moment...",
    "Attention Required! | Cloudflare",
)

SNAPSHOT_URL_PATTERNS = (
    re.compile(r"<!--\s*source-url:\s*(\S+)"),          # written by our capture tool
    re.compile(r"<!--\s*saved from url=\(\d+\)(\S+?)\s*-->"),  # Chrome "Save page as"
    re.compile(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)'),
    re.compile(r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)'),
)


class BotChallengeError(RuntimeError):
    """Raised when a response is a bot-protection challenge rather than content."""


class RetryableHTTPError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_url(url: str) -> str:
    """Canonical form used for de-duplication: no fragment, no trailing slash, lowercase host."""
    url, _ = urldefrag(url.strip())
    p = urlparse(url)
    path = p.path.rstrip("/") or "/"
    query = f"?{p.query}" if p.query else ""
    return f"{p.scheme or 'https'}://{p.netloc.lower()}{path}{query}"


def url_id(url: str) -> str:
    return hashlib.sha1(normalize_url(url).encode()).hexdigest()[:16]


def is_challenge_page(html: str) -> bool:
    head = html[:20000]
    return any(m in head for m in CHALLENGE_MARKERS)


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


@dataclass
class PropertyRecord:
    """One property / project / page. Missing values stay None - never invented."""

    url: str
    source: str                      # "DarGlobal" | "Wasalt"
    title: str
    page_type: str = "project"       # project | listing | company | article | partner
    description: str | None = None
    location: str | None = None
    city: str | None = None
    country: str | None = None
    property_type: str | None = None
    listing_type: str | None = None  # sale | rent
    price: str | None = None
    payment_plan: str | None = None
    bedrooms: str | None = None
    bathrooms: str | None = None
    area_sqm: str | None = None
    amenities: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    specifications: dict[str, str] = field(default_factory=dict)
    body_text: str | None = None     # remaining readable page text
    extraction_method: str = "snapshot"  # snapshot | sitemap | live
    extracted_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)


class PoliteFetcher:
    """requests.Session wrapper: robots.txt, rate limit, retries, timeouts, challenge detection."""

    def __init__(self, delay: float | None = None, timeout: float | None = None, user_agent: str | None = None):
        s = get_settings()
        self.delay = s.request_delay_seconds if delay is None else delay
        self.timeout = timeout or s.request_timeout_seconds
        self.user_agent = user_agent or s.user_agent
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent, "Accept-Language": "en"})
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._last_request = 0.0

    def allowed(self, url: str) -> bool:
        p = urlparse(url)
        root = f"{p.scheme}://{p.netloc}"
        if root not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                resp = self.session.get(f"{root}/robots.txt", timeout=self.timeout)
                rp.parse(resp.text.splitlines() if resp.status_code == 200 else [])
            except requests.RequestException:
                rp.parse([])  # unreachable robots.txt -> treat as allow-all (RFC 9309)
            self._robots[root] = rp
        if p.path.endswith("robots.txt"):
            return True
        return self._robots[root].can_fetch(self.user_agent, url)

    def _throttle(self) -> None:
        wait = self.delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    @retry(
        retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout, RetryableHTTPError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=20),
        reraise=True,
    )
    def get(self, url: str) -> requests.Response:
        if not self.allowed(url):
            raise PermissionError(f"robots.txt disallows {url}")
        self._throttle()
        resp = self.session.get(url, timeout=self.timeout)
        if resp.status_code == 429 or resp.status_code >= 500:
            raise RetryableHTTPError(f"HTTP {resp.status_code} for {url}")
        if resp.status_code == 403 and is_challenge_page(resp.text):
            raise BotChallengeError(f"Bot-protection challenge at {url}")
        resp.raise_for_status()
        return resp

    def get_html(self, url: str) -> str:
        html = self.get(url).text
        if is_challenge_page(html):
            raise BotChallengeError(f"Bot-protection challenge at {url}")
        return html

    def get_sitemap_urls(self, sitemap_url: str) -> list[dict]:
        """Return [{'loc':..., 'lastmod':...}] from a (possibly gzipped) sitemap."""
        content = self.get(sitemap_url).content
        if content[:2] == b"\x1f\x8b":
            content = gzip.decompress(content)
        return parse_sitemap_xml(content)


def parse_sitemap_xml(content: bytes | str) -> list[dict]:
    soup = BeautifulSoup(content, "xml")
    out, seen = [], set()
    for node in soup.find_all("url"):
        loc = node.find("loc")
        if not loc or not loc.text.strip():
            continue
        url = normalize_url(loc.text)
        if url in seen:
            continue
        seen.add(url)
        lastmod = node.find("lastmod")
        out.append({"loc": url, "lastmod": lastmod.text.strip() if lastmod else None})
    return out


def snapshot_url(html: str) -> str | None:
    head = html[:50000]
    for pat in SNAPSHOT_URL_PATTERNS:
        m = pat.search(head)
        if m:
            return normalize_url(m.group(1))
    return None


class BaseScraper(ABC):
    source: str = ""
    site_key: str = ""   # folder name under data/raw/html

    def __init__(self, fetcher: PoliteFetcher | None = None):
        self.settings = get_settings()
        self.fetcher = fetcher or PoliteFetcher()
        self.stats = {"pages_seen": 0, "parsed": 0, "skipped_challenge": 0, "skipped_duplicate": 0,
                      "skipped_out_of_scope": 0, "errors": 0}

    @property
    def snapshot_dir(self) -> Path:
        return self.settings.html_dir / self.site_key

    @abstractmethod
    def parse_page(self, html: str, url: str) -> PropertyRecord | None:
        """Turn one HTML page into a record, or None if the page is out of scope."""

    def iter_snapshots(self):
        if not self.snapshot_dir.exists():
            return
        for path in sorted(self.snapshot_dir.glob("*.htm*")):
            yield path, path.read_text(encoding="utf-8", errors="ignore")

    def scrape_snapshots(self) -> list[PropertyRecord]:
        records, seen = [], set()
        for path, html in self.iter_snapshots():
            self.stats["pages_seen"] += 1
            if is_challenge_page(html):
                self.stats["skipped_challenge"] += 1
                logger.warning("Snapshot %s is a challenge page, skipped", path.name)
                continue
            url = snapshot_url(html)
            if not url:
                self.stats["errors"] += 1
                logger.warning("Snapshot %s has no source URL, skipped", path.name)
                continue
            if url in seen:
                self.stats["skipped_duplicate"] += 1
                continue
            seen.add(url)
            try:
                rec = self.parse_page(html, url)
            except Exception:  # one bad page must not stop the run
                self.stats["errors"] += 1
                logger.exception("Failed to parse %s", url)
                continue
            if rec is None:
                self.stats["skipped_out_of_scope"] += 1
                continue
            records.append(rec)
            self.stats["parsed"] += 1
        return records

    # ---------- shared HTML helpers ----------
    @staticmethod
    def soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    @staticmethod
    def meta(soup: BeautifulSoup, *names: str) -> str | None:
        for n in names:
            tag = soup.find("meta", attrs={"property": n}) or soup.find("meta", attrs={"name": n})
            if tag and tag.get("content"):
                return clean_text(tag["content"])
        return None

    @staticmethod
    def json_ld(soup: BeautifulSoup) -> list[dict]:
        out = []
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            items = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
            out.extend(i for i in items if isinstance(i, dict))
        return out

    @staticmethod
    def main_text(soup: BeautifulSoup, max_chars: int = 12000) -> str:
        """Readable text with navigation, scripts, footers and forms removed."""
        soup = BeautifulSoup(str(soup), "lxml")  # work on a copy
        for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "form",
                         "iframe", "button", "select", "input"]):
            tag.decompose()
        lines, seen = [], set()
        for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "td", "th", "span", "div"]):
            if el.find(["p", "li", "div", "h1", "h2", "h3", "h4", "table"]):
                continue  # only leaf-ish blocks, avoid repeating parent text
            t = clean_text(el.get_text(" "))
            if len(t) < 3 or t.lower() in seen:
                continue
            seen.add(t.lower())
            lines.append(t)
        return "\n".join(lines)[:max_chars]
