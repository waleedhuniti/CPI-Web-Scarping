"""Daily product catalogue for every CPI division (config/catalogue.json), in the layout of the 8 Oct catalogue.

    python scripts/catalogue_crawl.py data/catalogue/2026-10-12

Stores selling their own goods only (no marketplaces / resellers): Carrefour and Lulu (search pages and the 8 Oct Lulu
category pages, with Scrapling's Chrome fingerprint) and Sharaf DG (its public product search, the same one its
website calls). Writes <out>/catalog.csv: one row per product and source, with the store's price, what that price is
for (Carrefour's by-weight cards: one weight step, e.g. 500 g, plus the per-kg price in the notes), the photo link,
the CPI division and the download group.
"""
import csv
import json
import random
import sys
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import scrapling_search as ss  # noqa: E402
from scrapling_category import price_basis  # noqa: E402

CONFIG = ROOT / "config/catalogue.json"
OUTLET = {"carrefour": "Carrefour", "lulu": "Lulu", "sharafdg": "Sharaf DG"}
SDG_SEARCH = "https://9khjlg93j1-dsn.algolia.net/1/indexes/products_index/query"
SDG_HEADERS = {"X-Algolia-Application-Id": "9KHJLG93J1", "X-Algolia-API-Key": "e81d5b30a712bb28f0f1d2a52fc92dd0",
               "Content-Type": "application/json", "Origin": "https://uae.sharafdg.com", "Referer": "https://uae.sharafdg.com/"}
BASIS = {"kg": "kg", "l": "litre", "pc": "piece", "bunch": "bunch"}
FIELDS = ["outlet", "store", "group", "division", "category", "title", "price", "regular_price", "size", "unit_price",
          "price_basis", "brand", "retailer_id", "availability", "url", "photo_url", "collected", "notes"]


def listing_pages(s, src):
    q = urllib.parse.quote_plus(src.get("query", ""))
    if src["kind"] == "search" and src["store"] == "carrefour":
        for n in range(src.get("pages", 1)):
            yield ss.parse_carrefour, f"https://www.carrefouruae.com/mafuae/en/search?keyword={q}&currentPage={n}"
    elif src["kind"] == "search" and src["store"] == "lulu":
        for n in range(1, src.get("pages", 1) + 1):
            yield ss.parse_lulu, f"https://gcc.luluhypermarket.com/en-ae/list/?search_text={q}&page={n}"
    elif src["kind"] == "lulu_category":
        yield ss.parse_lulu, f"https://gcc.luluhypermarket.com/en-ae/{src['slug']}/?page_size=50"


def sharafdg(s, src):
    f = f'post_status:publish AND "taxonomies.taxonomies_hierarchical.product_cat.lvl1":"{src["facet"]}"'
    body = json.dumps({"params": urllib.parse.urlencode({"query": "", "hitsPerPage": src.get("per_page", 60), "filters": f})})
    p = s.post(SDG_SEARCH, data=body, headers=SDG_HEADERS)
    out = []
    for h in json.loads(p.body).get("hits", []):
        try:
            price = float(h.get("price") or 0)
            regular = float(h.get("regular_price") or price)
        except ValueError:
            continue
        if price <= 0:
            continue
        brand = ((h.get("taxonomies") or {}).get("product_brand") or [""])[0]
        out.append(dict(title=h.get("post_title", ""), price=price, regular_price=max(price, regular), size_text="",
                        url=h.get("permalink", ""), photo=h.get("images", ""), brand=brand, retailer_id=h.get("sku", ""),
                        in_stock=str(h.get("in_stock")) == "1"))
    return out


def row_for(src, r, collected):
    per, basis = price_basis(dict(title=r["title"], price=float(r["price"]), size_text=r.get("size_text", "")))
    size = (r.get("size_text") or "").split(" - ")[0].strip()
    notes = []
    if basis in ("kg", "l") and per is not None and size:
        notes.append(f"Price is for {size}; AED {per} per {BASIS[basis]}")
    if r.get("regular_price") and float(r["regular_price"]) > float(r["price"]):
        notes.append(f"Was AED {r['regular_price']}")
    notes.append("Public UAE listing; Dubai branch availability not confirmed")
    rid = r.get("retailer_id") or ((urllib.parse.urlparse(r["url"]).path.rstrip("/").split("/p/") + [""])[1].split("/")[0])
    return dict(outlet=OUTLET[src["store"]], store=src["store"], group=src["group"], division=src["division"],
                category=src["category"], title=r["title"], price=r["price"], regular_price=r.get("regular_price", ""),
                size=size, unit_price=per if per is not None else "", price_basis=basis, brand=r.get("brand", ""),
                retailer_id=rid, availability="Out of stock" if r.get("in_stock") is False else "Available",
                url=r["url"], photo_url=r.get("photo", ""), collected=collected, notes=" · ".join(notes))


def main(out_dir, delay=1.2):
    from scrapling.fetchers import FetcherSession
    cfg = json.load(open(CONFIG, encoding="utf-8"))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    collected = (datetime.now(timezone.utc) + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M")
    rows, seen, log = [], set(), []
    with FetcherSession(impersonate="chrome", timeout=30, retries=3) as s:
        for n, src in enumerate(cfg["sources"], 1):
            got = []
            try:
                if src["kind"] == "algolia":
                    got = sharafdg(s, src)
                else:
                    for parse, url in listing_pages(s, src):
                        page = s.get(url)
                        got += parse(page, src.get("query", src["category"])) if page.status == 200 else []
                        time.sleep(delay + random.random())
            except Exception as e:
                log.append(f"{src['store']} | {src['category']}: FAILED {str(e)[:120]}")
            new = 0
            for r in got:
                key = (src["store"], r["url"])
                if not r.get("url") or not r.get("title") or key in seen:
                    continue
                seen.add(key)
                rows.append(row_for(src, r, collected))
                new += 1
            log.append(f"{src['store']} | {src['group']} | {src['category']}: {new} products")
            print(f"[{n}/{len(cfg['sources'])}] {log[-1]}", flush=True)
    with open(out_dir / "catalog.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    (out_dir / "crawl_log.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    by = {}
    for r in rows:
        by[r["group"]] = by.get(r["group"], 0) + 1
    print(f"{len(rows)} products -> {out_dir / 'catalog.csv'}  {by}")


if __name__ == "__main__":
    main(sys.argv[1])
