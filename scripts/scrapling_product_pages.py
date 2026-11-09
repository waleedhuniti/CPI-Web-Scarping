"""Optional Scrapling browser fetcher for CPI product-page verification.

It intentionally does not solve or bypass CAPTCHA, Turnstile, or human checks.
Detected challenges are recorded for review, or can be completed by an operator
in a visible browser session with --manual-check.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ALLOWED_HOSTS = {
    "carrefour": {"www.carrefouruae.com", "carrefouruae.com"},
    "lulu": {"gcc.luluhypermarket.com"},
}
CHALLENGE_MARKERS = (
    "verify you are human", "are you human", "human verification",
    "complete the security check", "security verification",
    "checking your browser", "enable javascript and cookies to continue",
    "captcha", "turnstile", "access denied",
)


class _TextExtractor(HTMLParser):
    BLOCKS = {"address", "article", "br", "div", "footer", "h1", "h2", "h3",
              "li", "main", "p", "section", "tr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip += 1
        if not self._skip and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1
        if not self._skip and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self.parts.append(data.strip())

    def text(self) -> str:
        return re.sub(r"\n[ \t]*\n+", "\n", "\n".join(self.parts)).strip()


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html or "")
    return parser.text()


def extract_json_ld(html: str) -> list[Any]:
    found: list[Any] = []
    pattern = r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
    for raw in re.findall(pattern, html or "", flags=re.I | re.S):
        try:
            found.append(json.loads(raw.strip()))
        except (json.JSONDecodeError, TypeError):
            continue
    return found


def is_human_verification(status: int | None, html: str, text: str = "") -> bool:
    if status in {401, 403, 429, 503}:
        return True
    sample = f"{html[:50000]}\n{text}".lower()
    return any(marker in sample for marker in CHALLENGE_MARKERS)


def validate_url(retailer: str, url: str) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in ALLOWED_HOSTS[retailer]:
        raise ValueError(f"URL host is not an approved {retailer} product domain: {url}")


def _record(url: str, page: Any, html: str, body_text: str) -> dict:
    status = getattr(page, "status", None)
    if is_human_verification(status, html, body_text):
        return {
            "url": url, "fetch_status": "human_verification_required",
            "http_status": status, "html": "", "markdown": "", "jsonLd": [],
        }
    return {
        "url": url, "fetch_status": "ok", "http_status": status,
        "html": html, "markdown": body_text, "jsonLd": extract_json_ld(html),
    }


def fetch_product_pages(retailer: str, urls: list[str], manual_check: bool = False) -> list[dict]:
    try:
        from scrapling.fetchers import StealthyFetcher, StealthySession
    except ImportError as exc:
        raise RuntimeError(
            "Install optional dependency: pip install -r requirements-scrapling.txt; "
            "then run: scrapling install"
        ) from exc

    for url in urls:
        validate_url(retailer, url)

    output: list[dict] = []
    if manual_check:
        with StealthySession(headless=False, timeout=45000) as session:
            for index, url in enumerate(urls):
                try:
                    page = session.fetch(url, wait=1000)
                    html = page.html_content or ""
                    body_text = html_to_text(html)
                    if is_human_verification(getattr(page, "status", None), html, body_text):
                        print(f"Human verification detected for {url}. Complete it in the visible browser.")
                        input("After completing the retailer's verification, press Enter to retry...")
                        page = session.fetch(url, wait=1000)
                        html = page.html_content or ""
                        body_text = html_to_text(html)
                    output.append(_record(url, page, html, body_text))
                except Exception as exc:
                    output.append({"url": url, "fetch_status": "fetch_error", "error": str(exc)})
                if index < len(urls) - 1:
                    time.sleep(2)
    else:
        for index, url in enumerate(urls):
            try:
                # StealthyFetcher enables Scrapling's browser stealth patches.
                # No CAPTCHA or Cloudflare challenge solver is enabled.
                page = StealthyFetcher.fetch(url, headless=True, timeout=45000, wait=1000)
                html = page.html_content or ""
                output.append(_record(url, page, html, html_to_text(html)))
            except Exception as exc:
                output.append({"url": url, "fetch_status": "fetch_error", "error": str(exc)})
            if index < len(urls) - 1:
                time.sleep(2)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("retailer", choices=sorted(ALLOWED_HOSTS))
    parser.add_argument("urls_json", type=Path, help="JSON list of product URLs or objects containing url")
    parser.add_argument("output_json", type=Path, help="Output compatible with scripts/verify_pages.py")
    parser.add_argument("--manual-check", action="store_true",
                        help="Open a visible browser and pause for an operator if a human check appears")
    args = parser.parse_args()
    raw = json.loads(args.urls_json.read_text(encoding="utf-8"))
    urls = [item if isinstance(item, str) else item["url"] for item in raw]
    rows = fetch_product_pages(args.retailer, urls, manual_check=args.manual_check)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    blocked = sum(row.get("fetch_status") == "human_verification_required" for row in rows)
    errors = sum(row.get("fetch_status") == "fetch_error" for row in rows)
    print(f"Saved {len(rows)} pages; human checks: {blocked}; fetch errors: {errors}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
