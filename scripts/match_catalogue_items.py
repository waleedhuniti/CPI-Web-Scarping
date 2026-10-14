"""Price the basket items that have no barcode and no category spec (match_mode 'name') from the day's catalogue.

    python scripts/match_catalogue_items.py data/catalogue/2026-10-13 [out.csv]

The official name of these items carries the brand and model in Latin letters (e.g. 'Siemens Dishwasher SN25D800GC',
'Apple iPhone 17 256GB', 'LG 55 inch UHD AI UA85 4K Smart TV'). A catalogue listing is accepted only when
  - every model-like token of the name (letters + digits, e.g. SN25D800GC, 55K55S30) is in the listing title, or, for names
    without such a token, every Latin word of the name is,
  - every number of the name (storage, size) is in the title as a whole number,
  - the title adds no variant word (pro, max, plus, ultra, mini, fe, air, lite, ...) that the name does not have.
Items with no usable Latin text (Arabic-only names) are left 'not found' (they need an English spec: config/ or the panel).
Output: one row per basket item (found / not found), same columns as the panel's basket run.
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QTY = re.compile(r"^\d+(\.\d+)?(g|gm|kg|ml|l|ltr|litre|gb|tb|w|kw|cm|mm|m|inch|in|pcs|pc|pack|mah|hz|btu|ton|v|x\d+)?$")
VARIANT = {"pro", "max", "plus", "ultra", "mini", "fe", "air", "lite", "se", "prime", "edge", "fold", "flip", "neo", "gt", "turbo"}
STOP = {"the", "and", "with", "for", "of", "in", "a", "an", "to", "by", "from", "new", "set", "pack", "pcs", "black", "white", "grey",
        "gray", "silver", "blue", "red", "green", "gold", "pink", "purple", "natural", "titanium", "inch", "smart", "series"}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def words(s):
    return [w for w in re.findall(r"[a-z0-9]+(?:[.\-/][a-z0-9]+)*", s.lower())]


def model_tokens(name):
    out = []
    for t in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-/\.]*", name):
        n = norm(t)
        if len(n) >= 3 and re.search(r"\d", n) and re.search(r"[a-z]", n) and not QTY.match(n):
            out.append(n)
    return out


def required(name):
    """(model tokens, latin words, numbers) a listing must carry."""
    models = model_tokens(name)
    ws = [w for w in words(name) if re.fullmatch(r"[a-z]+", w) and len(w) > 1 and w not in STOP]
    nums = [n for n in re.findall(r"(?<![A-Za-z0-9.])\d+(?:\.\d+)?(?![A-Za-z0-9.])", name)]
    sizes = [norm(m) for m in re.findall(r"\d+(?:\.\d+)?\s*(?:gb|tb|ml|g|kg|l|litre|ltr|inch)\b", name, re.I)]
    return models, ws, nums, sizes


def pieces(text):
    """Number of pieces/pack count stated in a name or title (4Pcs, Pack of 6, 6 x 125ml), or None."""
    t = text.lower()
    m = re.search(r"(\d+)\s*(?:pcs|pc|pieces|piece|pack|sachets?|bags?)\b", t) or re.search(r"(?:pack of|set of)\s*(\d+)", t) or re.search(r"\b(\d+)\s*x\s*\d", t)
    return int(m.group(1)) if m else None


def latin_share(name):
    lat = len(re.findall(r"[A-Za-z]", name))
    ara = len(re.findall(r"[\u0600-\u06ff]", name))
    return lat / max(1, lat + ara)


def accept(name, title):
    models, ws, nums, sizes = required(name)
    t = norm(title)
    tw = set(words(title))
    if models:
        if not all(m in t for m in models):
            return False
    else:
        if len(ws) < 2 or latin_share(name) < 0.7 or not all(w in tw for w in ws):
            return False
        if not all(re.search(rf"(?<![0-9.]){re.escape(n)}(?![0-9.])", title.lower()) for n in nums):
            return False
    if sizes and not all(s in t for s in sizes):
        return False
    pn, pt = pieces(name), pieces(title)
    if pn is not None and pn != pt:
        return False
    extra = (VARIANT & tw) - set(words(name))
    return not extra


def main(cat_dir, out_csv=None):
    cat_dir = Path(cat_dir)
    basket = json.load(open(ROOT / "data/basket/basket.json", encoding="utf-8"))
    cat = list(csv.DictReader(open(cat_dir / "catalog.csv", encoding="utf-8-sig")))
    cat = [c for c in cat if c.get("price")]
    items = [b for b in basket if b["match_mode"] == "name"]
    rows, found = [], 0
    for b in items:
        hits = [c for c in cat if accept(b["name_ar"], c["title"])]
        by_store = {}
        for c in hits:
            by_store.setdefault(c["outlet"], []).append(c)
        if not hits:
            rows.append(dict(item_code=b["item_code"], retailer="", status="not_found", accepted="no", title="", price="", url="",
                             note="no listing with this brand/model" if re.search(r"[A-Za-z]{3}", b["name_ar"]) else "Arabic-only name: needs an English spec"))
            continue
        for outlet, cs in by_store.items():
            c = sorted(cs, key=lambda x: float(x["price"]))[len(cs) // 2]       # the median listing, then pinned like the category lines
            found += 1
            rows.append(dict(item_code=b["item_code"], retailer=outlet, status="found", accepted="yes", title=c["title"], price=c["price"],
                             regular_price=c.get("regular_price", ""), url=c["url"], photo=c.get("photo_url", ""), retailer_id=c.get("retailer_id", ""),
                             note=f"{len(cs)} listing(s)"))
    cols = sorted({k for r in rows for k in r})
    if out_csv:
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols, restval="")
            w.writeheader()
            w.writerows(rows)
    items_found = len({r["item_code"] for r in rows if r["accepted"] == "yes"})
    print(f"{len(items)} 'name' items: {items_found} found at {found} store listings")
    return rows


if __name__ == "__main__":
    main(*sys.argv[1:3])
