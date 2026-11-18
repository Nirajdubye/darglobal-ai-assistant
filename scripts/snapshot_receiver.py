"""Local helper that stores pages viewed in a normal browser session as HTML snapshots.

Run:  python -m scripts.snapshot_receiver        (listens on 127.0.0.1:8765 only)

While you browse an allowed page, the page's rendered HTML can be POSTed here as
{"url": location.href, "html": document.documentElement.outerHTML}. It is saved to
data/raw/html/<site>/<url-hash>.html with a `source-url` comment, which the scrapers parse.

Alternative without this helper: Chrome "Save page as -> Webpage, HTML only" into
data/raw/html/darglobal/ or data/raw/html/wasalt/ (Chrome records the URL in the file).
"""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.scraper.base_scraper import is_challenge_page, normalize_url, url_id, utc_now  # noqa: E402

SITES = {"darglobal.co.uk": "darglobal", "www.darglobal.co.uk": "darglobal", "wasalt.sa": "wasalt",
         "www.wasalt.sa": "wasalt"}


def save_snapshot(url: str, html: str) -> Path:
    host = urlparse(url).netloc.lower()
    if host not in SITES:
        raise ValueError(f"host {host} not in scope")
    if is_challenge_page(html):
        raise ValueError("page is a bot-challenge page, not content - not saved")
    if "/search" in urlparse(url).path and SITES[host] == "wasalt":
        raise ValueError("/search is disallowed by wasalt robots.txt")
    folder = get_settings().html_dir / SITES[host]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{url_id(url)}.html"
    path.write_text(f"<!-- source-url: {normalize_url(url)} captured-at: {utc_now()} -->\n{html}", encoding="utf-8")
    return path


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        origin = self.headers.get("Origin", "")
        if urlparse(origin).netloc.lower() in SITES:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 15_000_000:
                raise ValueError("payload too large")
            data = json.loads(self.rfile.read(length))
            path = save_snapshot(data["url"], data["html"])
            code, body = 200, {"saved": str(path.name)}
        except Exception as e:  # report any problem back to the caller
            code, body = 400, {"error": str(e)}
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, fmt, *args):
        sys.stderr.write("snapshot: " + fmt % args + "\n")


if __name__ == "__main__":
    print("Snapshot receiver on http://127.0.0.1:8765 (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
