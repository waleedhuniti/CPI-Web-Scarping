"""Name search for barcoded basket lines the barcode search did not find (many products carry several barcodes and a
retailer lists only one of them).

    python scripts/name_fallback.py lulu data/runs/<run>          # updates <run>/lulu_matched.csv in place

For every line with status not_found it searches the retailer by the English query written for it
(data/basket/specs_en.json: query_en, then query_alt) and accepts a listing only when
  - every word of the brand (brand_en) is in the title,
  - every must_have phrase is supported (two thirds of its words) and no must_not phrase appears,
  - the title states exactly the basket size (0.5% tolerance; a multipack counts as its total).
The best listing (most product words, then the lowest price) replaces the row: status name_match, title, price, url.
"""
import csv
import json
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from cpi.basket import load_basket_any  # noqa: E402
from cpi.decision import NAME_MATCH  # noqa: E402
from cpi.quantity import all_quantities, parse_quantity, same_quantity  # noqa: E402
import match_run  # noqa: E402
import scrapling_search as ss  # noqa: E402
from scrapling_category import STOP, has_word, phrase_ok, words  # noqa: E402

SEARCH = {"carrefour": "https://www.carrefouruae.com/mafuae/en/search?keyword={q}",
          "lulu": "https://gcc.luluhypermarket.com/en-ae/list/?search_text={q}"}
SPECS = ROOT / "data/basket/specs_en.json"


def load_specs():
    if SPECS.exists():
        return {s["c"]: s for s in json.loads(SPECS.read_text(encoding="utf-8"))}
    return {s["c"]: s for s in json.loads((ROOT / "data/runs/2026-10-05/name_queries.json").read_text(encoding="utf-8"))}


def loose_ok(tw, phrase):
    """A descriptive phrase holds when, for one of its alternatives, at least two thirds of its words are in the title
    ('extra long grain' is satisfied by 'Extra Long ... Basmati'); a one-word phrase must be there."""
    for a in [x for x in re.split(r"\s*/\s*", phrase) if x.strip()]:
        core = [w for w in words(a) if w not in STOP]
        if not core or sum(has_word(tw, w) for w in core) >= max(1, -(-2 * len(core) // 3)):
            return True
    return False


def accept(title, spec, want_q):
    tw = words(title)
    brand = [w for w in words(spec.get("brand_en", "")) if w not in STOP]
    if brand and not all(has_word(tw, w) for w in brand):
        return -1
    musts = [m for m in spec.get("must_have", []) if not re.search(r"\d", m)]
    if not all(loose_ok(tw, m) for m in musts):
        return -1
    if any(phrase_ok(tw, n) and any(w not in STOP for w in words(n)) for n in spec.get("must_not", [])):
        return -1
    if not want_q.ok or not any(same_quantity(q, want_q) for q in all_quantities(title)):
        return -1
    return sum(phrase_ok(tw, m) for m in musts) + len(brand)


def run(retailer, run_dir, delay=1.5):
    from scrapling.fetchers import FetcherSession
    run_dir = Path(run_dir)
    path = run_dir / f"{retailer}_matched.csv"
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    items = {match_run.search_form(i.barcode_raw): i for i in load_basket_any(ROOT) if i.barcode_kind == "gtin"}
    specs = load_specs()
    todo = [r for r in rows if r["status"] == "not_found" and r["barcode"] in items]
    parse = ss.parse_carrefour if retailer == "carrefour" else ss.parse_lulu
    found = 0
    with FetcherSession(impersonate="chrome", timeout=30, retries=3) as s:
        for n, r in enumerate(todo, 1):
            it = items[r["barcode"]]
            spec = specs.get(it.item_code, {})
            want_q = parse_quantity(it.qty_raw)
            best = None
            for query in dict.fromkeys(q for q in (spec.get("query_en"), spec.get("query_alt")) if q):
                try:
                    page = s.get(SEARCH[retailer].format(q=quote_plus(query)))
                    listings = parse(page, query) if page.status == 200 else []
                except Exception as e:
                    print(f"[{n}/{len(todo)}] {r['barcode']}: search failed {str(e)[:80]}", flush=True)
                    listings = []
                for lst in listings:
                    score = accept(lst["title"], spec, want_q)
                    if score >= 0 and (best is None or (score, -lst["price"]) > (best[0], -best[1]["price"])):
                        best = (score, lst, query)
                time.sleep(delay + random.random())
                if best:
                    break
            if best:
                _, lst, query = best
                r.update(status=NAME_MATCH, score="", reasons=f"found by name search: {query}", title=lst["title"],
                         price=lst["price"], regular_price=lst["regular_price"], in_stock="", url=lst["url"])
                found += 1
            print(f"[{n}/{len(todo)}] {r['barcode']} {it.qty_raw}: " + (f"FOUND {best[1]['title'][:60]} AED {best[1]['price']}" if best else "not found"), flush=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{retailer}: name search on {len(todo)} lines not found by barcode -> {found} found")


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 1.5)
