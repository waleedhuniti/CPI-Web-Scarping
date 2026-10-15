"""Live name search for the basket's food lines that carry a Latin product name (match_mode 'name': 'Capri-Sun Mango Drink 200ml x Pack of 10').

    python scripts/name_live.py data/runs/<run>        # -> <run>/name_live.csv

The catalogue is a sample of each shop's range, so these named products are searched on the shop sites themselves (Carrefour, Lulu) and a
listing is taken only when it has the brand (spaces and hyphens ignored: Sun Top = Suntop), at least half of the other product words, and the
basket's pack size exactly (6 x 125 ml = 750 ml, whatever the way the title writes it). The cheapest of the accepted listings stands for the shop.
"""
import csv
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

SEARCH = {"carrefour": "https://www.carrefouruae.com/mafuae/en/search?keyword={q}",
          "lulu": "https://gcc.luluhypermarket.com/en-ae/list/?search_text={q}"}
GENERIC = {"juice", "drink", "fruit", "mixed", "blend", "natural", "flavoured", "flavored", "original", "classic", "tea", "black", "loose"}
NOISE = {"pack", "of", "x", "the", "and", "with", "in", "a", "ml", "g", "gm", "kg", "l", "litre", "liter", "litres", "pcs", "pc"}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def tokens(s):
    return [w for w in re.findall(r"[a-z]+", s.lower()) if w not in NOISE]


def accept(name, want_total, want_unit, title):
    toks = tokens(name)
    if len(toks) < 2:
        return False
    t = norm(title)
    brand = next((b for b in (toks[0] + toks[1], toks[0]) if b in t), None)       # Sun Top -> suntop; Capri-Sun -> caprisun
    if not brand:
        return False
    rest = [w for w in toks if w not in (toks[0], toks[1]) or len(toks[0]) > 4] if brand == toks[0] else toks[2:]
    rest = [w for w in rest if w != toks[0]]
    tw = set(tokens(title))
    must = [w for w in rest if w not in GENERIC]                  # the distinguishing words (orange, mango, whispers, summer) must all be there
    if any(not any(w == x or (len(w) > 4 and (x.startswith(w) or w.startswith(x))) for x in tw) for w in must):
        return False
    return size_ok(want_total, want_unit, title)


UNITS = {"ml": ("ml", 1), "l": ("ml", 1000), "ltr": ("ml", 1000), "litre": ("ml", 1000), "litres": ("ml", 1000), "liter": ("ml", 1000),
         "liters": ("ml", 1000), "g": ("g", 1), "gm": ("g", 1), "kg": ("g", 1000)}


def size_ok(want_total, want_unit, title):
    """The title's pack equals the basket's: size x pack count ('200ml, Pack of 10', '10 x 200 ml', '6 x 125 ml'), within 1%."""
    t = title.lower().replace(",", "")
    found = []
    for n, u in re.findall(r"(\d+(?:\.\d+)?)\s*(ml|litres?|liters?|ltr|l|kg|gm|g)\b", t):
        base, mult = UNITS[u]
        found.append((base, float(n) * mult))
    if not found or not want_total:
        return False
    packs = [int(x) for m in re.findall(r"pack of\s*(\d+)|(\d+)\s*x\b|\bx\s*(\d+)", t) for x in m if x] or [1]
    for base, size in found:
        if base != want_unit:
            continue
        for k in set(packs) | {1}:
            if abs(size * k - want_total) <= 0.01 * want_total + 0.5:
                return True
    return False


def run(run_dir, delay=1.2):
    from scrapling.fetchers import FetcherSession
    import scrapling_search as ss
    items = [b for b in json.load(open(ROOT / "data/basket/basket.json", encoding="utf-8"))
             if b["match_mode"] == "name" and b["item_code"].startswith("01") and len(re.findall(r"[A-Za-z]", b["name_ar"])) > 8]
    rows = []
    with FetcherSession(impersonate="chrome", timeout=30, retries=2) as s:
        for it in items:
            q = re.sub(r"\s*x\s*pack of\s*\d+|\s+\d+\s*(ml|l|litre|g|kg)\b", "", it["name_ar"], flags=re.I).strip()
            for shop, url in SEARCH.items():
                best = None
                try:
                    page = s.get(url.format(q=quote_plus(q)))
                    listings = (ss.parse_carrefour if shop == "carrefour" else ss.parse_lulu)(page, q) if page.status == 200 else []
                except Exception as e:
                    print(f"{it['item_code']} {shop}: search failed {str(e)[:60]}", flush=True)
                    listings = []
                for l in listings:
                    if accept(it["name_ar"], it.get("qty_total"), it.get("qty_unit"), l["title"]) and (best is None or l["price"] < best["price"]):
                        best = l
                time.sleep(delay)
                if best:
                    rows.append(dict(item_code=it["item_code"], retailer=shop, title=best["title"], price=best["price"], regular_price=best.get("regular_price", ""), url=best["url"]))
                print(f"{it['item_code']} {shop}: " + (f"{best['title'][:60]} AED {best['price']}" if best else "not found"), flush=True)
    out = Path(run_dir) / "name_live.csv"
    cols = ["item_code", "retailer", "title", "price", "regular_price", "url"]
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"name_live: {len({r['item_code'] for r in rows})} of {len(items)} lines found -> {out}")
    return rows


if __name__ == "__main__":
    run(sys.argv[1])
