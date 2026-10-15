"""Fill the basket lines a run could not price from the same day's catalogue, with the same rules as the live searches.

    python scripts/fill_from_catalogue.py data/runs/<run> data/catalogue/<date>

  - barcoded lines still 'not_found' in <run>/<retailer>_matched.csv: the catalogue listings of that retailer are tested with
    name_fallback.accept (brand, product words, exact pack size; a different size is never taken) -> status name_match
  - the product-set prices of the no-barcode lines come from product_panel.py (run it on the same catalogue first)
  - 'name' items (electronics, clothing...) come from match_catalogue_items.py (run separately; its csv is passed as 3rd arg)
The best listing of a line is the one with the highest accept() score, then the lowest price.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from cpi.basket import load_basket_any  # noqa: E402
from cpi.decision import NAME_MATCH  # noqa: E402
from cpi.quantity import parse_quantity  # noqa: E402
import match_run  # noqa: E402
import name_fallback as nf  # noqa: E402


def fill_barcode(run_dir, cat_dir):
    cat = list(csv.DictReader(open(Path(cat_dir) / "catalog.csv", encoding="utf-8-sig")))
    items = {match_run.search_form(i.barcode_raw): i for i in load_basket_any(ROOT) if i.barcode_kind == "gtin"}
    specs = nf.load_specs()
    total = 0
    for retailer in ("carrefour", "lulu"):
        path = Path(run_dir) / f"{retailer}_matched.csv"
        if not path.exists():
            continue
        rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
        listings = [c for c in cat if c["store"] == retailer and c["price"]]
        found = 0
        for r in rows:
            if r["status"] != "not_found" or r["barcode"] not in items:
                continue
            it = items[r["barcode"]]
            spec, want_q = specs.get(it.item_code, {}), parse_quantity(it.qty_raw)
            best = None
            for c in listings:
                s = nf.accept(c["title"], spec, want_q)
                if s >= 0 and (best is None or (s, -float(c["price"])) > (best[0], -float(best[1]["price"]))):
                    best = (s, c)
            if best:
                c = best[1]
                r.update(status=NAME_MATCH, score="", reasons="from the day's catalogue", title=c["title"], price=c["price"],
                         regular_price=c["regular_price"], in_stock="", url=c["url"])
                found += 1
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"{retailer}: {found} barcoded lines filled from the catalogue")
        total += found
    return total


if __name__ == "__main__":
    fill_barcode(sys.argv[1], sys.argv[2])
