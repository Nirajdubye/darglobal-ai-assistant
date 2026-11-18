# Website Research

Research date: 2026-11-18. All findings come from real HTTP requests made from the development machine.

## 1. DarGlobal — https://darglobal.co.uk/

| Check | Finding |
|---|---|
| robots.txt | 200 OK. `User-agent: *` allows `/`, `/blog/`, `/press/`, `/projects/`. Disallows tracking params (`utm_*`, `sfmc_*`), `?s=` search, `?post_type=`, `/sitemap_index.xml`. Project pages are **allowed**. |
| Sitemap | `https://darglobal.co.uk/sitemap.xml` → 200, plain XML, **480 URLs** (lastmod 2026-11-10). |
| Sitemap breakdown | 265 `/blog/*`, 72 `/press/*`, 26 `/insights/*`, ~45 project/landing pages (e.g. `/les-vagues`, `/w-residences`, `/trump-tower-jeddah`, `/aida-*`, `/rayana/*`, `/amaya/*`, `/one-of-one/*`), 12 `/partners/*`, 13 `/projects/properties-in-<country>[/<type>]` listing pages. |
| Countries in URL structure | UAE, UK, Spain, Oman, Qatar, Saudi Arabia |
| Tech stack | Next.js (`x-powered-by: Next.js`) |
| Bot protection | **Imperva / Incapsula** (`x-cdn: Imperva`, `visid_incap_*` cookies). Plain HTTP clients receive a ~200-byte page containing only `<script src="/_Incapsula_Resource?...">` and `noindex,nofollow`. Retrying with a cookie jar gives the same challenge page. |
| Static or JS? | Content cannot be judged without passing the challenge. Next.js sites usually server-render HTML, so after the challenge the HTML is likely parseable by BeautifulSoup. |
| Terms | `/terms-of-uses` and `/terms-conditions` exist but are behind the same protection — must be read in a browser before scraping. |

**Useful data:** project name, location/country, property type (villas/apartments/hotel rooms/plots), branded partner (Trump, Pagani, Missoni, Fendi Casa, Elie Saab, W Hotels, Marriott…), amenities, descriptions, sometimes starting price & payment plan. Blog/press/insights give company background.

## 2. Wasalt — https://wasalt.sa/

| Check | Finding |
|---|---|
| robots.txt | 200 OK. `User-agent: *` → `Allow: /`, `Disallow: /search`, `/cdn-cgi/rum`. Comment: *"We're allowing AI access to most areas to support future integrations"*. Property pages are **allowed**. `/search` is allowed only for named AI bots (ChatGPT-User, anthropic-ai, PerplexityBot) — **not for us**, so we will not touch `/search`. |
| llms.txt | Referenced in robots.txt, but returns **403 Cloudflare challenge**. |
| Sitemaps | Hosted on `cdn.wasalt.sa` → **200, no protection**. 10 sitemaps (EN/AR × static, product, category, rental PDP, rental SRP). |
| Product sitemap (EN) | 10.4 MB, **60,000 listing URLs** (45,389 sale / 14,611 rent; ~36k apartments, ~11.6k villas, ~5k floors, ~4.9k land, ~1.4k buildings). Slugs encode real facts, e.g. `/en/property/sale/villa-333-sqm-facing-east-on-20m-width-street-5841671`. |
| Static sitemap | Area landing pages like `/en/properties-for-sale-in-taif-al-malaab`. |
| Category sitemap | 9 info pages (`/en/s/privacy-policy`, `/en/s/masterplan`, `/en/s/wasalt-business`…). |
| Bot protection | **Cloudflare managed challenge** on every HTML page (`/`, `/en`, listing pages, `llms.txt`) → HTTP 403 "Just a moment…". |
| Static or JS? | Unknown until a browser view; likely Next.js SSR. |

**Useful data:** listing type (sale/rent), property type, size (sqm), bedrooms, orientation, street width, listing ID, URL, lastmod — available *now* from the sitemap. Price, city/district, amenities, description need the listing page.

## 3. Core constraint — both sites block automated HTTP clients

The brief says *"Do not bypass CAPTCHA, authentication, access controls or anti-bot restrictions."* Both sites put an anti-bot layer (Imperva, Cloudflare) in front of every content page. Using headless Playwright, stealth plugins, TLS-fingerprint spoofing or cookie replay to get past these challenges **would be bypassing them**, so the plan does not do that.

### Compliant collection options

| Option | What it is | Compliant? | Data quality | Effort |
|---|---|---|---|---|
| **A. Browser-assisted snapshot (recommended)** | Pages opened at human pace in a real Chrome browser or using interactive session snapshots. Rendered HTML saved to `data/raw/html/`. The Python scrapers (BeautifulSoup) then parse those saved snapshots. If a CAPTCHA appears, you solve it as a normal visitor. | Yes — normal user viewing allowed public pages, robots.txt-compliant, low volume (~60 DG + ~100 Wasalt pages). | High (full page content) | Medium |
| **B. Sitemap metadata (Wasalt)** | Parse the officially published, unprotected CDN sitemaps. | Yes — sitemaps exist for crawlers. | Medium (no price/description) | Low |
| C. Headless Playwright solving challenges | Automated browser that passes the JS challenge. | **No** — counts as bypassing anti-bot. Not recommended. | High | Medium–High, fragile |
| D. Ask DarGlobal for a data export / permission | Email HR. | Yes | Best | Unknown delay |

**Recommendation: A + B.** The scrapers stay real code (`requests` fetcher with retries/rate-limit + BS4 parsers). The fetch layer has two modes: `live` (used for sitemaps/robots, and works for pages if protection is ever lifted) and `snapshot` (parses HTML files saved from a real browser). This is honest, reproducible, and easy to explain in the interview: *"The sites use Imperva and Cloudflare bot protection. I did not circumvent it; I captured public pages through a normal browser session and ran my parsers on those snapshots."*

## 4. Deployment-relevant findings

- Scraping cannot run inside the cloud container (it would be blocked anyway). **Scrape/ingest happens offline; the built dataset and Chroma index ship with the image.**
- Embedding model must run on CPU in a small container → `sentence-transformers/all-MiniLM-L6-v2` (~90 MB, 384-dim).
- Dataset is small (hundreds to low thousands of chunks) → ChromaDB on local disk is plenty.
