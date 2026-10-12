"""Product photo links for the catalogue and the basket, cached in data/photos.json (product URL -> photo URL).

    python scripts/collect_photos.py data/runs/2026-10-12_full [more run folders ...]

1. Every page of the categories in config/categories.json: the listing parsers return each product's photo.
2. Products in the given runs that still have no photo (barcode / name search hits, catalogue rows): their product page
   (og:image or JSON-LD image).
New crawls record the photo themselves (scrapling_search parsers -> catalog.csv photo_url); this fills the gap for
runs collected before that.
"""
import csv
import json
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import scrapling_search as ss  # noqa: E402

CACHE = ROOT / "data/photos.json"


def load():
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def save(cache):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=0, sort_keys=True))


def page_photo(html):
    for pat in (r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', r'"image"\s*:\s*"(https://[^"]+)"',
                r'"image"\s*:\s*\[\s*"(https://[^"]+)"'):
        m = re.search(pat, html)
        if m and not m.group(1).endswith(".svg"):
            return m.group(1)
    return ""


def crawl_listings(s, cache, delay):
    cfg = json.load(open(ROOT / "config/categories.json"))
    for retailer in ("carrefour", "lulu"):
        parse = ss.parse_carrefour if retailer == "carrefour" else ss.parse_lulu
        for cat in cfg[retailer]:
            seen = set()
            for n in range(60):
                try:
                    rows = parse(s.get(cat["url"].format(page0=n, page1=n + 1)), cat["name"])
                except Exception:
                    rows = []
                new = [r for r in rows if r["url"] not in seen]
                for r in new:
                    seen.add(r["url"])
                    if r.get("photo"):
                        cache[r["url"]] = r["photo"]
                time.sleep(delay + random.random())
                if not new:
                    break
            print(f"{retailer} | {cat['name']}: {len(seen)} products, photos cached {len(cache)}", flush=True)


def product_urls(run_dirs):
    urls = set()
    for d in run_dirs:
        for f in Path(d).glob("*.csv"):
            for r in csv.DictReader(open(f, encoding="utf-8-sig")):
                u = r.get("url", "")
                if r.get("photo_url"):                       # the source already gave a photo
                    continue
                if u.startswith("http") and ("carrefouruae" in u or "luluhypermarket" in u):
                    urls.add(u)
    return urls


def main(run_dirs, delay=1.2, skip_listings=False):
    from scrapling.fetchers import FetcherSession
    cache = load()
    with FetcherSession(impersonate="chrome", timeout=30, retries=2) as s:
        if not skip_listings:
            crawl_listings(s, cache, delay)
            save(cache)
        todo = sorted(u for u in product_urls(run_dirs) if u not in cache)
        for n, u in enumerate(todo, 1):
            try:
                p = s.get(u)
                html = p.body.decode("utf-8", "ignore") if isinstance(p.body, bytes) else str(p.body)
                cache[u] = page_photo(html) if p.status == 200 else ""
            except Exception:
                cache[u] = ""
            if n % 50 == 0:
                print(f"product pages {n}/{len(todo)}", flush=True)
                save(cache)
            time.sleep(delay + random.random())
    save(cache)
    print(f"{sum(1 for v in cache.values() if v)} product photos in {CACHE.relative_to(ROOT)}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args, skip_listings="--skip-listings" in sys.argv)
