"""Search by name + brand + size for basket items that the barcode did not settle.

Step 1 - build the search URLs (one per item and retailer, plus an alternative query when there is one):

    python scripts/name_search.py urls data/runs/2026-10-05/name_queries.json data/runs/2026-10-05

  Items searched at a retailer are those without a final accepted barcode match there (barcode not found, size
  doubts, page-check doubts) and every item without a barcode. Writes <retailer>_name_urls.json (crawler input)
  and name_url_map.json (url -> item code, query).

Step 2 - crawl the URLs with apify/website-content-crawler (cheerio, maxCrawlDepth 0, ignoreCanonicalUrl true).

Step 3 - turn the crawled pages into candidate lists:

    python scripts/name_search.py candidates <retailer> <dataset.json> data/runs/2026-10-05

  Writes <retailer>_name_candidates.json: per item, every listing seen on its search pages with the price, the
  size read from the title, whether that size equals the basket size, and a name/brand score. Nothing is accepted
  here; the decision is made in step 4 (judging) and every accepted row keeps the listing URL as evidence.
"""
import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cpi.basket import load_basket  # noqa: E402
from cpi.matcher import ACCEPTED, Listing, name_score  # noqa: E402
from cpi.quantity import Quantity, all_quantities, pack_count, same_quantity  # noqa: E402
from cpi.retailers import carrefour, lulu  # noqa: E402

SEARCH = {
    "carrefour": "https://www.carrefouruae.com/mafuae/en/search?keyword={q}",
    "lulu": "https://gcc.luluhypermarket.com/en-ae/list/?search_text={q}",
}
QUERY_PARAM = {"carrefour": "keyword", "lulu": "search_text"}
_PRODUCT_LINK = {
    "carrefour": re.compile(r"\[([^\]\n]{3,})\]\((https://www\.carrefouruae\.com/[^)\s]*?/p/\d+)[^)\s]*\)"),
    "lulu": re.compile(r"\[([^\]\n]{3,})\]\((https://gcc\.luluhypermarket\.com/en-ae/[^)\s]*?/p/[^)\s/?]+)/?\??\)"),
}


def final_accepted(run_dir: Path, retailer: str) -> set:
    """Item codes with an accepted barcode match that also survived the product-page check."""
    check = run_dir / f"{retailer}_matched_page_check.csv"
    matched = run_dir / f"{retailer}_matched.csv"
    if check.exists():
        return {r["item_code"] for r in csv.DictReader(open(check, encoding="utf-8-sig")) if r["final_status"] in ACCEPTED}
    return {r["item_code"] for r in csv.DictReader(open(matched, encoding="utf-8-sig")) if r["status"] in ACCEPTED}


def build_urls(queries_path, run_dir):
    run_dir = Path(run_dir)
    queries = {q["c"]: q for q in json.load(open(queries_path, encoding="utf-8"))}
    url_map = {}
    for retailer in SEARCH:
        done = final_accepted(run_dir, retailer)
        urls = []
        for code, q in queries.items():
            if code in done:
                continue
            for kind in ("query_en", "query_alt"):
                text = (q.get(kind) or "").strip()
                if not text:
                    continue
                url = SEARCH[retailer].format(q=quote_plus(text))
                if url not in url_map:
                    urls.append({"url": url})
                url_map.setdefault(url, []).append({"item_code": code, "query": text, "kind": kind, "retailer": retailer})
        json.dump(urls, open(run_dir / f"{retailer}_name_urls.json", "w"), indent=0)
        print(f"{retailer}: {len({u['item_code'] for v in url_map.values() for u in v if u['retailer'] == retailer})} items, "
              f"{len(urls)} search pages")
    json.dump(url_map, open(run_dir / "name_url_map.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)


def page_listings(retailer, markdown, query) -> list:
    """Every product card on a search page: the retailer parser's fields plus the raw card text (for the judge)."""
    if retailer == "lulu" and "No results found" in markdown:
        return []
    parsed = (carrefour.parse_search_markdown(markdown, query) if retailer == "carrefour"
              else lulu.parse_search_markdown(markdown, query))
    by_url = {p.url.rstrip("/"): p for p in parsed}
    links = list(_PRODUCT_LINK[retailer].finditer(markdown))
    out, seen = [], set()
    for i, m in enumerate(links):
        url = m.group(2).rstrip("/")
        title = m.group(1).strip()
        if url in seen or title.startswith("!"):
            continue
        seen.add(url)
        end = links[i + 1].start() if i + 1 < len(links) else m.end() + 300
        card = markdown[m.end():min(end, m.end() + 300)].split("[")[0]       # stop at the next link / image
        card = re.sub(r"\s+", " ", card).strip()
        p = by_url.get(url)
        # size the price is for: Carrefour prints it on the card ('AED5.00 500g - Approx 6 pieces/KG',
        # 'AED181.97 2.60KG Min Order 2 kg'), Lulu in the title ('Orange Valencia 2.5 kg')
        sized = all_quantities(title) or all_quantities(re.sub(r"AED\s?[\d.,]+|per\s+\w+|pieces?/KG", " ", card))
        price = p.price if p else None
        per_kg = per_l = None
        if price and sized and sized[0].unit == "g" and sized[0].total > 0:
            per_kg = round(price / sized[0].total * 1000, 2)
        if price and sized and sized[0].unit == "ml" and sized[0].total > 0:
            per_l = round(price / sized[0].total * 1000, 2)
        out.append({
            "title": title, "url": url, "price": p.price if p else None,
            "regular_price": p.regular_price if p else None,
            "unit_price": (p.extra.get("unit_price") if p else None) or None,
            "unit_basis": (p.extra.get("unit_basis") if p else "") or "",
            "card": card[:200], "priced_size": f"{sized[0].total:g}{sized[0].unit}" if sized else "",
            "price_per_kg": per_kg, "price_per_l": per_l,
        })
    return out


def build_candidates(retailer, dataset_path, run_dir):
    run_dir = Path(run_dir)
    url_map = json.load(open(run_dir / "name_url_map.json", encoding="utf-8"))
    basket = {i.item_code: i for i in load_basket(ROOT / "data/basket/basket_source.xlsx")}
    data = json.load(open(dataset_path, encoding="utf-8"))
    pages = data["items"] if isinstance(data, dict) else data
    per_item, unread = {}, []
    for pg in pages:
        q = parse_qs(urlparse(pg["url"]).query).get(QUERY_PARAM[retailer], [""])[0]
        key = SEARCH[retailer].format(q=quote_plus(q))
        targets = url_map.get(key) or url_map.get(pg["url"]) or []
        md = pg.get("markdown") or ""
        listings = page_listings(retailer, md, q)
        if not listings and not (retailer == "lulu" and "No results found" in md) and len(md) < 2000:
            unread.append(pg["url"])
        for t in targets:
            rec = per_item.setdefault(t["item_code"], {"queries": [], "listings": {}})
            rec["queries"].append({"query": q, "kind": t["kind"], "results": len(listings)})
            for lst in listings:
                rec["listings"].setdefault(lst["url"], lst)

    out = []
    for code, rec in per_item.items():
        it = basket[code]
        item_q = Quantity(it.qty_raw, it.qty_unit, it.qty_total, it.qty_count, it.qty_flag)
        n = pack_count(it.name_ar)
        cands = []
        for lst in rec["listings"].values():
            qs = all_quantities(lst["title"])
            size_equal = None
            if item_q.ok and qs:
                size_equal = any(same_quantity(item_q, x) or (n > 1 and x.unit == item_q.unit and
                                 abs(x.total - n * item_q.total) <= 0.005 * x.total) for x in qs)
            score = name_score(it.name_ar, it.brand_ar, Listing(retailer, lst["title"]))
            cands.append(dict(lst, size_in_title=[f"{x.total:g}{x.unit}" for x in qs], size_equal=size_equal,
                              name_score=round(score, 2)))
        cands.sort(key=lambda c: (c["size_equal"] is True, c["name_score"]), reverse=True)
        out.append({"item_code": code, "retailer": retailer, "name_ar": it.name_ar, "brand_ar": it.brand_ar,
                    "qty_raw": it.qty_raw, "basket_size": f"{item_q.total:g}{item_q.unit}" if item_q.ok else "",
                    "origin_raw": it.origin_raw, "fresh_type": it.fresh_type, "queries": rec["queries"],
                    "candidates": cands})
    dest = run_dir / f"{retailer}_name_candidates.json"
    json.dump(out, open(dest, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with_size = sum(1 for o in out if any(c["size_equal"] for c in o["candidates"]))
    print(f"{retailer}: {len(pages)} pages, {len(out)} items, {sum(1 for o in out if o['candidates'])} with listings, "
          f"{with_size} with a listing of the basket size | pages that did not render: {len(unread)}")
    print("written", dest)


if __name__ == "__main__":
    if sys.argv[1] == "urls":
        build_urls(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "candidates":
        build_candidates(sys.argv[2], sys.argv[3], sys.argv[4])
