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


_C_IMG = re.compile(r"https://cdn\.mafrservices\.com/[^\"'\s\\]+?/(\d+)_main\.(?:jpg|jpeg|png|webp)")
_L_IMG = re.compile(r"https://[a-z0-9.-]+/products/[^\"'\s\\]+?\.(?:jpg|jpeg|png|webp)")


def _html(sel):
    b = getattr(sel, "body", None)
    if isinstance(b, bytes):
        return b.decode("utf-8", "ignore")
    return str(getattr(sel, "html_content", "") or b or "")


def carrefour_photos(page):
    """Carrefour product id -> photo URL, from the image links on the page (the file name is '<id>_main.jpg')."""
    return {m.group(1): m.group(0) for m in _C_IMG.finditer(_html(page))}


def lulu_photo(page_html, href):
    """The product photo nearest to the product's link on a Lulu page (photo and link sit in the same card;
    the smallest rendition '..._size256x..._cropCenter.jpg' when present)."""
    best = ""
    for pos in [m.start() for m in re.finditer(re.escape(href), page_html)][:3]:
        imgs = [(abs(m.start() - pos), m.group(0)) for m in _L_IMG.finditer(page_html, max(0, pos - 6000), pos + 6000)]
        if imgs:
            d = min(i[0] for i in imgs)
            near = [u for dist, u in imgs if dist <= d + 1500]
            best = next((u for u in near if "_size256" in u), near[0])
            break
    return best


def parse_carrefour(page, code):
    """Product cards on a Carrefour search page -> raw rows (reuses the card regex of cpi.retailers.carrefour)."""
    rows, photos = [], carrefour_photos(page)
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
                             size_text=lst.extra["size_text"], photo=photos.get(lst.extra["product_id"], "")))
    return list({r["product_id"]: r for r in rows}.values())


def parse_lulu(page, code):
    """Product cards on a Lulu search page: each price node, climbed to the card that holds its product link."""
    num = lambda t: float(m.group(0)) if (m := re.search(r"\d+(?:\.\d+)?", (t or "").replace(",", ""))) else 0.0
    rows, page_html = [], _html(page)
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
                         in_stock=None, url=url, photo=lulu_photo(page_html, href)))
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
    ap.add_argument("--no-names", action="store_true", help="skip the name search for barcodes not found")
    ap.add_argument("--stop-after", type=int, default=0, help="stop asking the shop after N refused pages in a row (0 = never); "
                    "the pages not asked stay unread (listed in <retailer>_failed.json), no retries, and <retailer>_status.json says 'blocked'")
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
    halt = {"streak": 0, "on": False, "not_asked": 0}

    def read_pages(session, todo, label=""):
        """Search every barcode of `todo`; returns the ones whose page could not be read."""
        bad = []
        for n, code in enumerate(todo, 1):
            if a.stop_after and halt["streak"] >= a.stop_after:      # the shop is refusing us: stop asking, leave the rest unread
                halt["on"] = True
                halt["not_asked"] += len(todo) - n + 1
                bad.extend(todo[n - 1:])
                print(f"{label}stopped after {halt['streak']} refused pages in a row; {len(todo) - n + 1} barcodes not asked (unread)", flush=True)
                break
            try:
                page = session.get(site["url"](code))
                html = page.body.decode("utf-8", "ignore") if isinstance(page.body, bytes) else str(page.body)
                if not site["page_ok"](page, html):
                    raise RuntimeError(f"HTTP {page.status}, {len(html)} bytes - not a search result page")
                rows = site["parse"](page, code)
                halt["streak"] = 0
                raw.extend(rows)
                searched.append(code)
                print(f"{label}[{n}/{len(todo)}] {code}: {len(rows)} product(s)" + (f" - {rows[0]['title']} AED {rows[0]['price']}" if rows else ""))
            except Exception as e:                                   # one bad page must not stop the run
                bad.append(code)
                halt["streak"] += 1
                print(f"{label}[{n}/{len(todo)}] {code}: FAILED {type(e).__name__}: {str(e)[:120]}")
            time.sleep(a.delay + random.random())
        return bad

    with FetcherSession(impersonate="chrome", timeout=30, retries=3) as s:
        failed = read_pages(s, codes)
        for rnd, wait in enumerate((30, 90), 1):                     # pages that failed (a shop busy or blocking for a moment) get two more tries
            if not failed or halt["on"]:
                break
            print(f"\nretry {rnd}: {len(failed)} page(s) failed, waiting {wait} s", flush=True)
            time.sleep(wait)
            failed = read_pages(s, failed, label=f"retry{rnd} ")

    raw_path = run_dir / f"{a.retailer}_raw.jsonl"
    with open(raw_path, "w", encoding="utf-8") as f:
        for r in raw:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (run_dir / f"{a.retailer}_searched.json").write_text(json.dumps(searched))
    (run_dir / f"{a.retailer}_failed.json").write_text(json.dumps(failed))
    tot = len(searched) + len(failed)
    state = "not_read" if not tot else "blocked" if not searched or halt["on"] and len(failed) >= 0.9 * tot else "ok" if len(failed) <= 0.05 * tot else "partial"
    (run_dir / f"{a.retailer}_status.json").write_text(json.dumps(dict(read=len(searched), failed=len(failed), not_asked=halt["not_asked"], state=state)) + "\n")
    print(f"\n{a.retailer}: {len(codes)} barcodes, {len(searched)} pages read, {len(failed)} failed, {len(raw)} product rows ({state})")
    if raw:
        match_run.main(a.retailer, raw_path, run_dir / f"{a.retailer}_searched.json")
        if not a.no_names and not a.limit:
            import name_fallback                                  # barcodes not found: same brand + size by name
            name_fallback.run(a.retailer, run_dir, a.delay)


if __name__ == "__main__":
    main()
