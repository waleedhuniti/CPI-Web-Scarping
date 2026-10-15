"""Match one retailer's raw barcode-search results against the basket and write a per-item results CSV.

    python scripts/match_run.py carrefour data/runs/2026-10-05/carrefour_raw.jsonl

Input: JSON lines with searched_barcode, title, price, regular_price, in_stock, url [, product_id].
Output: <raw>_matched.csv (one row per basket barcode line: matched or not) and a summary on stdout.
"""
import collections
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cpi import gtin  # noqa: E402
from cpi.basket import load_basket_any  # noqa: E402
from cpi.matcher import ACCEPTED, Listing, match  # noqa: E402


def search_form(raw) -> str:
    """The barcode as typed into the retailer's search box (restores the leading zero Excel dropped from UPC-A)."""
    d = gtin.digits_only(raw)
    return "0" + d if len(d) == 11 else d


def main(retailer, raw_path, searched_path=None):
    items = [i for i in load_basket_any(ROOT) if i.barcode_kind == "gtin"]
    raw = [json.loads(line) for line in open(raw_path, encoding="utf-8")]
    searched = set(json.load(open(searched_path))) if searched_path else None   # None = every barcode was searched
    by_code = collections.defaultdict(dict)                 # searched barcode -> {product_id/url: row}  (de-duplicated)
    for r in raw:
        by_code[r["searched_barcode"]][r.get("product_id") or r["url"]] = r

    out, counts, groups = [], collections.Counter(), collections.defaultdict(collections.Counter)
    for it in items:
        code = search_form(it.barcode_raw)
        hits = list(by_code.get(code, {}).values())
        if searched is not None and code not in searched and not hits:
            out.append(dict(item_code=it.item_code, group=it.group_code, name_ar=it.name_ar, brand_ar=it.brand_ar,
                            basket_qty=it.qty_raw, barcode=code, status="not_searched", score="", reasons="search page not read",
                            title="", price="", regular_price="", in_stock="", url=""))
            counts["not_searched"] += 1
            groups[it.group_code]["not_searched"] += 1
            continue
        base = dict(item_code=it.item_code, group=it.group_code, name_ar=it.name_ar, brand_ar=it.brand_ar,
                    basket_qty=it.qty_raw, barcode=code)
        if not hits:
            row = dict(base, status="not_found", score="", reasons="no product for this barcode", title="", price="",
                       regular_price="", in_stock="", url="")
        else:
            best = None
            for h in hits:
                lst = Listing(retailer, h["title"], price=h["price"], regular_price=h["regular_price"],
                              searched_barcode=code, result_count=len(hits), in_stock=h.get("in_stock"), url=h["url"])
                res = match(it, lst)
                if best is None or (res.accepted, res.score) > (best[1].accepted, best[1].score):
                    best = (h, res)
            h, res = best
            row = dict(base, status=res.status, score=round(res.score, 2), reasons="; ".join(res.reasons),
                       title=h["title"], price=h["price"], regular_price=h["regular_price"], in_stock=h.get("in_stock"),
                       url=h["url"])
        out.append(row)
        counts[row["status"]] += 1
        groups[it.group_code][row["status"]] += 1

    dest = Path(raw_path).with_name(Path(raw_path).stem.replace("_raw", "") + "_matched.csv")
    with open(dest, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    n = len(out)
    found = sum(v for k, v in counts.items() if k not in ("not_found", "not_searched"))
    accepted = sum(v for k, v in counts.items() if k in ACCEPTED)
    print(f"{retailer}: {n} barcoded basket lines | found at retailer {found} ({found / n:.0%}) | "
          f"accepted by barcode+size {accepted} ({accepted / n:.0%})")
    for k, v in counts.most_common():
        print(f"  {k:32s} {v}")
    print("by COICOP group (accepted / lines):")
    for g in sorted(groups):
        tot = sum(groups[g].values())
        print(f"  {g}: {sum(v for k, v in groups[g].items() if k in ACCEPTED)}/{tot}")
    print("written", dest)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
