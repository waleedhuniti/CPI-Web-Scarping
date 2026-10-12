"""Barcode search on Carrefour / Lulu with Scrapling (no Apify), then the usual barcode + size matching.

    pip install "scrapling[fetchers]"
    python scripts/scrapling_search.py carrefour data/runs/2026-10-11_scrapling            # all basket barcodes
    python scripts/scrapling_search.py lulu data/runs/2026-10-11_scrapling --limit 10      # first 10 only (a test)
    python scripts/scrapling_search.py carrefour <run_dir> --codes codes.json             # a chosen list of barcodes

Plain HTTP requests with Chrome's TLS fingerprint (Scrapling's `Fetcher`, impersonate="chrome") are enough for both
sites' search pages: Carrefour renders the product cards on the server, Lulu ships them in the page HTML.
One request at a time with a pause between them (--delay), three tries per page.

Writes into <run_dir>:
  <retailer>_raw.jsonl       one row per product card found (searched_barcode, title, price, regular_price, url, ...)
  <retailer>_searched.json   barcodes whose search page was read (no row = not carried)
  <retailer>_failed.json     barcodes whose page could not be read (blocked, timeout) - re-run them later
  <retailer>_matched.csv     scripts/match_run.py on the above: one row per basket barcode line
"""
import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from cpi.basket import load_basket_any  # noqa: E402
from cpi.retailers import carrefour, lulu  # noqa: E402
import match_run  # noqa: E402

CARREFOUR_HOST = "https://www.carrefouruae.com"
LULU_HOST = "https://gcc.luluhypermarket.com"


def _text(el, sep=" "):
    return re.sub(r"\s+", " ", el.get_all_text(separator=sep)).strip()


def _card(el, needle, levels=10):
    """Climb from `el` to the first ancestor whose text holds `needle` (the product card)."""
    card = el
    for _ in range(levels):
        if card is None or needle(card):
            return card
        card = card.parent
    return None


def parse_carrefour(page, code):
    """Product cards on a Carrefour search page -> raw rows (reuses the card regex of cpi.retailers.carrefour)."""
    rows = []
    for a in page.css('a[href*="/p/"]'):
        title = a.get_all_text(strip=True)
        if not title or not re.search(r"/p/\d+", a.attrib.get("href", "")):
            continue
        card = _card(a, lambda c: "AED" in c.get_all_text())
        if card is None:
            continue
        rest = _text(card)
        rest = rest[rest.find(title) + len(title):] if title in rest else rest
        url = CARREFOUR_HOST + a.attrib["href"] if a.attrib["href"].startswith("/") else a.attrib["href"]
        for lst in carrefour.parse_search_markdown(f"[{title}]({url}){rest}", code):
            rows.append(dict(searched_barcode=code, product_id=lst.extra["product_id"], title=lst.title, price=lst.price,
                             regular_price=lst.regular_price, in_stock=None, url=lst.url,
                             unit_price=lst.extra["unit_price"], unit_basis=lst.extra["unit_basis"],
                             size_text=lst.extra["size_text"]))
    return list({r["product_id"]: r for r in rows}.values())


def parse_lulu(page, code):
    """Product cards on a Lulu search page: each price node, climbed to the card that holds its product link."""
    num = lambda t: float(m.group(0)) if (m := re.search(r"\d+(?:\.\d+)?", (t or "").replace(",", ""))) else 0.0
    rows = []
    for node in page.css('[data-testid="product-price"]'):
        card = _card(node, lambda c: bool(c.css('a[href*="/p/"]')))
        if card is None:
            continue
        link = next((a for a in card.css('a[href*="/p/"]') if a.get_all_text(strip=True)), None)
        if link is None:
            continue
        price = num(_text(node))
        was = num(_text(card.css('[class*="line-through"]')[0])) if card.css('[class*="line-through"]') else 0.0
        href = link.attrib["href"]
        url = (LULU_HOST + href if href.startswith("/") else href).split("?")[0]
        rows.append(dict(searched_barcode=code, product_id=re.sub(r".*/p/([^/]+)/?$", r"\1", url),
                         title=link.get_all_text(strip=True), price=price, regular_price=was if was > price else price,
                         in_stock=None, url=url))
    return list({r["url"]: r for r in rows}.values())


SITES = {
    # page_ok: the page really is a rendered search result (not a block page or an empty shell)
    "carrefour": dict(url=lambda c: carrefour.search_url(c), parse=parse_carrefour,
                      page_ok=lambda p, html: p.status == 200 and "Carrefour" in (p.css("title::text").get() or "")),
    "lulu": dict(url=lambda c: lulu.search_url(c), parse=parse_lulu,
                 page_ok=lambda p, html: p.status == 200 and len(html) > 100_000 and "luluhypermarket" in html),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("retailer", choices=sorted(SITES))
    ap.add_argument("run_dir")
    ap.add_argument("--limit", type=int, default=0, help="search only the first N barcodes")
    ap.add_argument("--codes", help="JSON list of barcodes to search instead of the whole basket")
    ap.add_argument("--delay", type=float, default=1.5, help="seconds between requests (a random 0-1 s is added)")
    a = ap.parse_args()

    from scrapling.fetchers import FetcherSession   # imported here so --help works without Scrapling installed

    site, run_dir = SITES[a.retailer], Path(a.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    if a.codes:
        codes = [match_run.search_form(c) for c in json.load(open(a.codes))]
    else:
        items = [i for i in load_basket_any(ROOT) if i.barcode_kind == "gtin"]
        codes = list(dict.fromkeys(match_run.search_form(i.barcode_raw) for i in items))
    if a.limit:
        codes = codes[:a.limit]

    raw, searched, failed = [], [], []
    with FetcherSession(impersonate="chrome", timeout=30, retries=3) as s:
        for n, code in enumerate(codes, 1):
            try:
                page = s.get(site["url"](code))
                html = page.body.decode("utf-8", "ignore") if isinstance(page.body, bytes) else str(page.body)
                if not site["page_ok"](page, html):
                    raise RuntimeError(f"HTTP {page.status}, {len(html)} bytes - not a search result page")
                rows = site["parse"](page, code)
                raw += rows
                searched.append(code)
                print(f"[{n}/{len(codes)}] {code}: {len(rows)} product(s)" + (f" - {rows[0]['title']} AED {rows[0]['price']}" if rows else ""))
            except Exception as e:                                   # one bad page must not stop the run
                failed.append(code)
                print(f"[{n}/{len(codes)}] {code}: FAILED {type(e).__name__}: {str(e)[:120]}")
            time.sleep(a.delay + random.random())

    raw_path = run_dir / f"{a.retailer}_raw.jsonl"
    with open(raw_path, "w", encoding="utf-8") as f:
        for r in raw:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (run_dir / f"{a.retailer}_searched.json").write_text(json.dumps(searched))
    (run_dir / f"{a.retailer}_failed.json").write_text(json.dumps(failed))
    print(f"\n{a.retailer}: {len(codes)} barcodes, {len(searched)} pages read, {len(failed)} failed, {len(raw)} product rows")
    if raw:
        match_run.main(a.retailer, raw_path, run_dir / f"{a.retailer}_searched.json")


if __name__ == "__main__":
    main()
