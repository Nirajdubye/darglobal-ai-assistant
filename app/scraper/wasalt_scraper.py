"""Wasalt (wasalt.sa) scraper.

Two data sources, both compliant:
1. Public sitemaps on cdn.wasalt.sa (no bot protection, listed in robots.txt).
   Listing URLs encode real facts: sale/rent, type, size, bedrooms, facing, street width, id.
2. Browser snapshots of listing pages (wasalt.sa itself serves a Cloudflare challenge
   to plain HTTP clients, which we do not circumvent).
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlparse

import pandas as pd

from app.scraper.base_scraper import BaseScraper, PropertyRecord, clean_text, normalize_url, utc_now

CDN = "https://cdn.wasalt.sa/sitemap"
PRODUCT_SITEMAP = f"{CDN}/product_sitemap_en_sa.xml.gz"
STATIC_SITEMAP = f"{CDN}/static_sitemap_en_sa.xml.gz"
CATEGORY_SITEMAP = f"{CDN}/category_sitemap_en_sa.xml.gz"

LISTING_RE = re.compile(r"/en/property/(sale|rent)/([a-z0-9-]+)-(\d+)$")
KSA_CITIES = [
    "riyadh", "jeddah", "makkah", "mecca", "madinah", "medina", "dammam", "al-khobar", "khobar", "dhahran",
    "taif", "abha", "khamis-mushait", "tabuk", "buraydah", "hail", "jazan", "najran", "al-ahsa", "hofuf",
    "jubail", "yanbu", "al-kharj", "unaizah", "qatif", "al-baha", "sakaka", "arar", "rabigh", "diriyah",
]
STATIC_RE = re.compile(r"/en/([a-z-]+?)-for-(sale|rent)-in-([a-z0-9-]+)$")


def parse_listing_slug(url: str) -> dict | None:
    """Turn a listing URL into facts. Returns None for non-listing URLs."""
    m = LISTING_RE.search(urlparse(url).path)
    if not m:
        return None
    listing_type, slug, listing_id = m.groups()
    alt = re.match(r"^(\d+)-bedrooms?-([a-z-]+?)-(?:rent|sale)$", slug)   # e.g. 3-bedrooms-apartment-rent
    if alt:
        beds_alt, property_type = int(alt.group(1)), alt.group(2).replace("-", " ")
    else:
        ptype = re.match(r"([a-z]+(?:-[a-z]+)*?)(?=-\d|-with|-facing|$)", slug)
        property_type = ptype.group(1).replace("-", " ") if ptype else slug.split("-")[0]
        beds_alt = None
    area = re.search(r"(?:^|-)(\d+)-sqm", slug)
    beds = re.search(r"with-(\d+)-bedrooms?", slug)
    facing = re.search(r"facing-((?:\d-streets)|(?:north|south|east|west)(?:-(?:east|west))?)", slug)
    street = re.search(r"on-(\d+)m-width-street", slug)
    return {
        "listing_id": listing_id,
        "listing_type": listing_type,
        "property_type": property_type,
        "area_sqm": int(area.group(1)) if area else None,
        "bedrooms": int(beds.group(1)) if beds else beds_alt,
        "facing": facing.group(1).replace("-", " ") if facing else None,
        "street_width_m": int(street.group(1)) if street else None,
    }


# Upper bounds for a believable area. Wasalt URLs label a number "sqm", but for most
# apartments/floors it is far too large (median ~1,900 "sqm"), so we do not trust it.
MAX_PLAUSIBLE_SQM = {"apartment": 1000, "floor": 1500, "room": 300, "villa": 10000, "duplex": 2000}


def plausible_area(property_type: str, area) -> bool:
    if area is None or pd.isna(area):
        return False
    limit = next((v for k, v in MAX_PLAUSIBLE_SQM.items() if k in str(property_type)), None)
    return area >= 10 and (limit is None or area <= limit)


def slug_title(f: dict) -> str:
    parts = [f["property_type"].title()]
    if f["area_sqm"] and plausible_area(f["property_type"], f["area_sqm"]):
        parts.append(f"{int(f['area_sqm'])} sqm")
    if f["bedrooms"] is not None:
        parts.append(f"{f['bedrooms']} bedroom{'s' if f['bedrooms'] != 1 else ''}")
    if f["facing"]:
        parts.append(f"facing {f['facing']}")
    if f["street_width_m"]:
        parts.append(f"on {f['street_width_m']}m wide street")
    return f"{', '.join(parts)} for {f['listing_type']}"


def city_of(location_slug: str) -> str | None:
    for c in sorted(KSA_CITIES, key=len, reverse=True):
        if location_slug == c or location_slug.startswith(c + "-"):
            return c.replace("-", " ").title()
    return None


class WasaltScraper(BaseScraper):
    source = "Wasalt"
    site_key = "wasalt"

    # ------------------------------------------------------------------ sitemap
    def fetch_sitemaps(self) -> dict[str, list[dict]]:
        return {
            "product": self.fetcher.get_sitemap_urls(PRODUCT_SITEMAP),
            "static": self.fetcher.get_sitemap_urls(STATIC_SITEMAP),
            "category": self.fetcher.get_sitemap_urls(CATEGORY_SITEMAP),
        }

    @staticmethod
    def listings_frame(product_entries: list[dict]) -> pd.DataFrame:
        rows = []
        for e in product_entries:
            facts = parse_listing_slug(e["loc"])
            if facts:
                rows.append({"url": e["loc"], "lastmod": e.get("lastmod"), **facts})
        df = pd.DataFrame(rows)
        return df.drop_duplicates(subset="listing_id") if not df.empty else df

    def sitemap_listing_records(self, df: pd.DataFrame, sample_per_group: int = 25, seed: int = 42) -> list[PropertyRecord]:
        """A stratified sample (by sale/rent x property type) of individual listings."""
        if df.empty:
            return []
        sample = (df.groupby(["listing_type", "property_type"], group_keys=False)
                    .apply(lambda g: g.sample(min(len(g), sample_per_group), random_state=seed)))
        out = []
        for r in sample.itertuples():
            f = {k: _clean_value(v) for k, v in r._asdict().items()}
            specs = {k: str(f[k]) for k in ("listing_id", "facing", "street_width_m") if f.get(k) is not None and not pd.isna(f[k])}
            out.append(PropertyRecord(
                url=r.url, source=self.source, title=slug_title(f), page_type="listing",
                country="Saudi Arabia", property_type=r.property_type, listing_type=r.listing_type,
                area_sqm=str(int(r.area_sqm)) if plausible_area(r.property_type, r.area_sqm) else None,
                bedrooms=None if pd.isna(r.bedrooms) else str(int(r.bedrooms)),
                specifications=specs, extraction_method="sitemap",
                description=f"Wasalt listing #{r.listing_id}: {slug_title(f)}. Listed/updated {r.lastmod}. "
                            "Price, city and district are not included in the sitemap entry - see the listing page."
                            + ("" if pd.isna(r.area_sqm) or plausible_area(r.property_type, r.area_sqm) else
                               " The area stated in the listing URL looks implausible, so it is omitted."),
            ))
        return out

    def market_summary_records(self, df: pd.DataFrame, static_entries: list[dict]) -> list[PropertyRecord]:
        """Aggregate statistics computed with pandas from the full public sitemap."""
        if df.empty:
            return []
        now = utc_now()
        total = len(df)
        by_lt = df["listing_type"].value_counts().to_dict()
        lines = [
            f"Wasalt public sitemap snapshot ({now[:10]}): {total:,} English-language property listings "
            f"({by_lt.get('sale', 0):,} for sale, {by_lt.get('rent', 0):,} for rent), all in Saudi Arabia.",
            "Listings by property type and purpose:",
        ]
        ct = df.groupby(["property_type", "listing_type"]).size().unstack(fill_value=0)
        ct["total"] = ct.sum(axis=1)
        for ptype, row in ct.sort_values("total", ascending=False).head(15).iterrows():
            lines.append(f"- {ptype}: {int(row['total']):,} total "
                         f"({int(row.get('sale', 0)):,} for sale, {int(row.get('rent', 0)):,} for rent)")
        lines.append("Typical size (median area in sqm, using only listings whose stated area is plausible):")
        stated = df.dropna(subset=["area_sqm"])
        ok = stated[[plausible_area(t, a) for t, a in zip(stated["property_type"], stated["area_sqm"])]]
        sizes = ok.groupby("property_type")["area_sqm"].agg(["median", "count"])
        totals = stated.groupby("property_type").size()
        unreliable = []
        for ptype, row in sizes.sort_values("count", ascending=False).head(8).iterrows():
            if row["count"] < 0.7 * totals[ptype]:      # >30% implausible -> the field is not trustworthy
                unreliable.append(ptype)
                continue
            lines.append(f"- {ptype}: median {int(row['median'])} sqm (based on {int(row['count']):,} of "
                         f"{int(totals[ptype]):,} listings that state an area)")
        if unreliable:
            lines.append(f"- No reliable size figure for: {', '.join(unreliable)} (more than 30% of the stated "
                         "areas in their URLs are implausibly large).")
        beds = df.dropna(subset=["bedrooms"])
        if not beds.empty:
            dist = beds[beds["property_type"] == "apartment"]["bedrooms"].astype(int).value_counts().sort_index()
            lines.append("Apartment listings by bedroom count: " +
                         ", ".join(f"{b} bed: {n:,}" for b, n in dist.head(7).items()))
        facing = df["facing"].dropna().value_counts().head(5)
        if not facing.empty:
            lines.append("Most common facing directions (villas/land/buildings): " +
                         ", ".join(f"{k} ({v:,})" for k, v in facing.items()))
        lines.append("Note: these are counts of listing URLs in Wasalt's public sitemap, not verified market data. "
                     "Many apartment and floor URLs state areas that are far too large to be real (for example "
                     "tens of thousands of sqm), so those values were excluded from the size statistics. "
                     "The sitemap does not contain prices.")
        records = [PropertyRecord(
            url="https://wasalt.sa/en", source=self.source, title="Wasalt listings overview (sitemap statistics)",
            page_type="company", country="Saudi Arabia", body_text="\n".join(lines),
            extraction_method="sitemap", extracted_at=now,
        )]

        # City coverage from the SEO city/area landing pages (Wasalt's category sitemap).
        cities: dict[str, set] = {}
        for e in static_entries:
            m = STATIC_RE.search(urlparse(e["loc"]).path)
            if not m:
                continue
            ptypes, purpose, loc = m.groups()
            loc = re.sub(r"-for-sar-.*$", "", loc)
            city = city_of(loc)
            if city:
                cities.setdefault(city, set()).add(f"{ptypes.replace('-', ' ')} for {purpose}")
        if cities:
            body = ["Saudi cities with dedicated Wasalt search pages, and the categories available:"]
            for city in sorted(cities):
                body.append(f"- {city}: {', '.join(sorted(cities[city])[:8])}")
            records.append(PropertyRecord(
                url="https://wasalt.sa/en", source=self.source, title="Wasalt city coverage",
                page_type="company", country="Saudi Arabia", body_text="\n".join(body),
                extraction_method="sitemap", extracted_at=now,
            ))
        return records

    # ------------------------------------------------------------------ pages
    def parse_page(self, html: str, url: str) -> PropertyRecord | None:
        url = normalize_url(url)
        path = urlparse(url).path
        if "/search" in path:
            return None  # disallowed by robots.txt for generic bots
        soup = self.soup(html)
        facts = parse_listing_slug(url) or {}
        h1 = soup.find("h1")
        title = clean_text(h1.get_text(" ")) if h1 else (self.meta(soup, "og:title") or path)
        body = self.main_text(soup)
        if len(body) < 50:
            return None
        rec = PropertyRecord(
            url=url, source=self.source, title=title,
            page_type="listing" if facts else "company",
            description=self.meta(soup, "description", "og:description"),
            country="Saudi Arabia", body_text=body,
            listing_type=facts.get("listing_type"), property_type=facts.get("property_type"),
            area_sqm=str(facts["area_sqm"]) if facts.get("area_sqm") else None,
            bedrooms=str(facts["bedrooms"]) if facts.get("bedrooms") is not None else None,
        )
        self._enrich_from_structured(soup, rec)
        if not rec.price:
            m = re.search(r"((?:SAR|SR|ر\.س)\s?[\d,]+(?:\.\d+)?(?:\s?(?:/\s?(?:year|month|yearly|monthly)))?)", body, re.I)
            rec.price = clean_text(m.group(1)) if m else None
        return rec

    def _enrich_from_structured(self, soup, rec: PropertyRecord) -> None:
        """Use JSON-LD / Next.js data when present; only copies values that exist."""
        for item in self.json_ld(soup):
            offers = item.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            if offers.get("price") and not rec.price:
                rec.price = f"{offers.get('priceCurrency', '')} {offers['price']}".strip()
            addr = item.get("address") or {}
            if isinstance(addr, dict):
                rec.city = rec.city or addr.get("addressLocality")
                rec.location = rec.location or ", ".join(
                    x for x in (addr.get("streetAddress"), addr.get("addressLocality"), addr.get("addressRegion")) if x) or None
            for key in ("numberOfRooms", "numberOfBedrooms"):
                if item.get(key) and not rec.bedrooms:
                    rec.bedrooms = str(item[key])
            if item.get("numberOfBathroomsTotal"):
                rec.bathrooms = str(item["numberOfBathroomsTotal"])
            feats = item.get("amenityFeature") or []
            rec.amenities += [clean_text(f.get("name")) for f in feats if isinstance(f, dict) and f.get("name")]

        nd = soup.find("script", id="__NEXT_DATA__")
        if nd and nd.string:
            try:
                data = json.loads(nd.string)
            except json.JSONDecodeError:
                return
            found = _find_keys(data, {"city", "district", "price", "salePrice", "bathroom", "bathrooms", "amenities"})
            rec.city = rec.city or _first_str(found.get("city"))
            district = _first_str(found.get("district"))
            if district:
                rec.location = rec.location or ", ".join(x for x in (district, rec.city) if x)
            price = found.get("salePrice") or found.get("price")
            if price and not rec.price and isinstance(price[0], (int, float, str)):
                rec.price = f"SAR {price[0]}"
            baths = found.get("bathrooms") or found.get("bathroom")
            if baths and not rec.bathrooms and isinstance(baths[0], (int, str)):
                rec.bathrooms = str(baths[0])


def _clean_value(v):
    """pandas NaN -> None, whole floats (from NaN-containing int columns) -> int."""
    if isinstance(v, float):
        if pd.isna(v):
            return None
        if v.is_integer():
            return int(v)
    return v


def _find_keys(obj, keys: set[str], out: dict | None = None, depth: int = 0) -> dict:
    out = {} if out is None else out
    if depth > 12:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys and v not in (None, "", [], {}):
                out.setdefault(k, []).append(v)
            _find_keys(v, keys, out, depth + 1)
    elif isinstance(obj, list):
        for v in obj[:200]:
            _find_keys(v, keys, out, depth + 1)
    return out


def _first_str(values) -> str | None:
    for v in values or []:
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, dict):
            for k in ("name", "en", "title"):
                if isinstance(v.get(k), str):
                    return v[k]
    return None
