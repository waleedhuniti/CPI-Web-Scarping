"""Daily product catalogue for every CPI division (config/catalogue.json), in the layout of the 8 Oct catalogue.

    python scripts/catalogue_crawl.py data/catalogue/2026-10-12
    python scripts/catalogue_crawl.py data/catalogue/2026-10-12 --stores=zara,max --append   # add stores to the day
    python scripts/catalogue_crawl.py <dir> --stores=max --part-only   # one store per process, then:
    python scripts/catalogue_crawl.py <dir> --merge

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
OUTLET = {"carrefour": "Carrefour", "lulu": "Lulu", "sharafdg": "Sharaf DG", "zara": "Zara", "centrepoint": "Centrepoint", "max": "Max"}
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


def zara(s, src):
    """Zara's own category feed (the one its pages load): prices are in fils, one row per product (first colour)."""
    p = s.get(f"https://www.zara.com/ae/en/category/{src['category_id']}/products?ajax=true")
    out = []
    for g in json.loads(p.body).get("productGroups", []):
        for e in g.get("elements", []):
            for c in e.get("commercialComponents") or []:
                if c.get("type") != "Product" or not c.get("price") or c.get("priceUnavailable"):
                    continue
                colors = (c.get("detail") or {}).get("colors") or [{}]
                x = (colors[0].get("xmedia") or c.get("xmedia") or [{}])[0]
                photo = f"https://static.zara.net{x['path']}/{x['name']}.jpg?ts={x.get('timestamp', '')}&w=300" if x.get("path") else ""
                seo = c.get("seo") or {}
                old = c.get("oldPrice") or colors[0].get("oldPrice")
                colour = colors[0].get("name", "")
                out.append(dict(title=c["name"].title() + (f" ({colour.title()})" if colour else ""), price=c["price"] / 100,
                                regular_price=(old or c["price"]) / 100, size_text="",
                                url=f"https://www.zara.com/ae/en/{seo.get('keyword', '')}-p{seo.get('seoProductId', '')}.html",
                                photo=photo, brand="Zara", retailer_id=seo.get("seoProductId", ""),
                                in_stock=c.get("availability", "in_stock") == "in_stock"))
                if len(out) >= src.get("per_page", 60):
                    return out
    return out


def landmark(src):
    """Centrepoint (Landmark: Splash, Shoe Mart, Babyshop, Lifestyle, Max ...) search page through Scrapling's stealth
    browser (Cloudflare); the products are in the page's state (__NEXT_DATA__ -> initialState, base64 JSON)."""
    import base64
    import re
    from scrapling.fetchers import StealthyFetcher
    q = urllib.parse.quote(src["query"])
    site = src.get("site", "https://www.centrepointstores.com/ae/en")
    p = StealthyFetcher.fetch(f"{site}/search?q={q}", headless=True,
                              solve_cloudflare=True, network_idle=True, timeout=120000)
    m = re.search(r'__NEXT_DATA__" type="application/json">(.*?)</script>', p.html_content, re.S)
    if not m:
        return []
    state = json.loads(base64.b64decode(json.loads(m.group(1))["props"]["initialState"] + "==").decode("utf-8", "ignore"))
    out = []
    for h in ((state.get("algoliaProductReducer") or {}).get("data") or {}).get("hits", []):
        try:
            price, was = float(h.get("price") or h.get("sale_price")), float(h.get("wasPrice") or h.get("price"))
        except (TypeError, ValueError):
            continue
        concept = ((h.get("concept") or {}).get("en") or "").title().replace("Shoemart", "Shoe Mart")
        colour = (h.get("color") or {}).get("en", "")
        out.append(dict(title=((h.get("name") or {}).get("en") or h.get("title", "")) + (f" ({colour})" if colour else ""),
                        price=price, regular_price=max(price, was), size_text="",
                        url=site + (h.get("url") or h.get("uri") or ""),
                        photo=h.get("thumbnailImg") or h.get("thumb_image") or "",
                        brand=(h.get("brandDisplayValue") or {}).get("en") or h.get("brand", ""), retailer_id=h.get("sku", ""),
                        in_stock=str(h.get("inStock")) == "1",
                        outlet=src.get("outlet") or (f"{concept} (Centrepoint)" if concept else "Centrepoint")))
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
    return dict(outlet=r.get("outlet") or OUTLET[src["store"]], store=src["store"], group=src["group"], division=src["division"],
                category=src["category"], title=r["title"], price=r["price"], regular_price=r.get("regular_price", ""),
                size=size, unit_price=per if per is not None else "", price_basis=basis, brand=r.get("brand", ""),
                retailer_id=rid, availability="Out of stock" if r.get("in_stock") is False else "Available",
                url=r["url"], photo_url=r.get("photo", ""), collected=collected, notes=" · ".join(notes))


def save_rows(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def crawl_store(store, sources, collected, delay, progress, part=None):
    """One store's sources, one request at a time; Carrefour, Lulu and Sharaf DG run side by side."""
    from scrapling.fetchers import FetcherSession
    rows, seen, log = [], set(), []
    with FetcherSession(impersonate="chrome", timeout=30, retries=3) as s:
        for src in sources:
            got = []
            try:
                if src["kind"] == "algolia":
                    got = sharafdg(s, src)
                elif src["kind"] == "zara":
                    got = zara(s, src)
                elif src["kind"] == "landmark":
                    got = landmark(src)
                else:
                    for parse, url in listing_pages(s, src):
                        page = s.get(url)
                        got += parse(page, src.get("query", src["category"])) if page.status == 200 else []
                        time.sleep(delay + random.random())
            except Exception as e:
                log.append(f"{store} | {src['category']}: FAILED {str(e)[:120]}")
            new = 0
            for r in got:
                key = r.get("url")
                if not key or not r.get("title") or key in seen:
                    continue
                seen.add(key)
                rows.append(row_for(src, r, collected))
                new += 1
            log.append(f"{store} | {src['group']} | {src['category']}: {new} products")
            progress(log[-1])
            if part:                       # keep what is done so a stop or a hang loses nothing
                save_rows(part, rows)
    return rows, log


def merge(out_dir):
    """Put the part_<store>.csv files of a day into catalog.csv (a store's part replaces its old rows)."""
    out_dir = Path(out_dir)
    parts = {p.stem[5:]: list(csv.DictReader(open(p, encoding="utf-8-sig"))) for p in sorted(out_dir.glob("part_*.csv"))}
    old = [r for r in csv.DictReader(open(out_dir / "catalog.csv", encoding="utf-8-sig"))] if (out_dir / "catalog.csv").exists() else []
    rows = [r for r in old if r["store"] not in parts] + [r for rs in parts.values() for r in rs]
    save_rows(out_dir / "catalog.csv", rows)
    by = {}
    for r in rows:
        by[r["store"]] = by.get(r["store"], 0) + 1
    print(f"{len(rows)} products in {out_dir / 'catalog.csv'}  {by}")


def main(out_dir, delay=1.0, only=None, append=False, part_only=False):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    cfg = json.load(open(CONFIG, encoding="utf-8"))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    collected = (datetime.now(timezone.utc) + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M")
    stores = {}
    for src in cfg["sources"]:
        if not only or src["store"] in only:
            stores.setdefault(src["store"], []).append(src)
    total = sum(len(v) for v in stores.values())
    lock, done = threading.Lock(), [0]

    def progress(line):
        with lock:
            done[0] += 1
            print(f"[{done[0]}/{total}] {line}", flush=True)

    with ThreadPoolExecutor(len(stores)) as ex:
        results = list(ex.map(lambda kv: crawl_store(kv[0], kv[1], collected, delay, progress,
                                                     out_dir / f"part_{kv[0]}.csv"), stores.items()))
    rows = [r for rs, _ in results for r in rs]
    log = [line for _, ls in results for line in ls]
    if part_only:                                           # one store per process; merge() combines them
        print(f"{len(rows)} products in the part file")
        return
    if append and (out_dir / "catalog.csv").exists():      # add these stores to the day's catalogue
        old = [r for r in csv.DictReader(open(out_dir / "catalog.csv", encoding="utf-8-sig")) if r["store"] not in stores]
        rows = old + rows
        log = (out_dir / "crawl_log.txt").read_text(encoding="utf-8").splitlines() + log
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
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = next((a.split("=", 1)[1].split(",") for a in sys.argv if a.startswith("--stores=")), None)
    if "--merge" in sys.argv:
        merge(args[0])
    else:
        main(args[0], only=only, append="--append" in sys.argv, part_only="--part-only" in sys.argv)
