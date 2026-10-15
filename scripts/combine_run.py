"""Add more category listings of the same day to a run, then price the basket again from everything.

    python scripts/combine_run.py data/runs/2026-10-12_full data/runs/2026-10-12_extra [more run folders ...]

1. <run>/catalog.csv gets the listings of the other folders' catalog.csv (one row per product URL).
2. Lines without a barcode are matched again on the whole catalogue (scripts/scrapling_category.match).
3. Barcoded lines still not found get a last chance in the listings: same brand, product words and exact basket size
   (scripts/name_fallback.accept) -> status name_match, "found in the category listings".
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
import scrapling_category as sc  # noqa: E402


def read(path):
    return list(csv.DictReader(open(path, encoding="utf-8-sig"))) if Path(path).exists() else []


def merge_catalogs(run_dir, extra_dirs):
    rows = read(run_dir / "catalog.csv")
    seen = {r["url"] for r in rows}
    for d in extra_dirs:
        for r in read(Path(d) / "catalog.csv"):
            if r["url"] not in seen:
                seen.add(r["url"])
                rows.append(r)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(run_dir / "catalog.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, restval="")
        w.writeheader()
        w.writerows(rows)
    log = run_dir / "crawl_log.txt"
    extra_log = "".join(Path(d, "crawl_log.txt").read_text(encoding="utf-8") for d in extra_dirs if Path(d, "crawl_log.txt").exists())
    log.write_text((log.read_text(encoding="utf-8") if log.exists() else "") + extra_log, encoding="utf-8")
    print(f"{len(rows)} listings in {run_dir / 'catalog.csv'}")
    return rows


def barcoded_from_listings(run_dir, catalog):
    specs = nf.load_specs()
    items = {match_run.search_form(i.barcode_raw): i for i in load_basket_any(ROOT) if i.barcode_kind == "gtin"}
    for retailer in ("carrefour", "lulu"):
        path = run_dir / f"{retailer}_matched.csv"
        rows = read(path)
        listings = [r for r in catalog if r["retailer"] == retailer and r["price"] not in ("", None)]
        found = 0
        for r in rows:
            it = items.get(r["barcode"])
            if r["status"] != "not_found" or not it:
                continue
            spec, want_q = specs.get(it.item_code, {}), parse_quantity(it.qty_raw)
            best = None
            for lst in listings:
                score = nf.accept(lst["title"], spec, want_q)
                if score >= 0 and (best is None or (score, -float(lst["price"])) > (best[0], -float(best[1]["price"]))):
                    best = (score, lst)
            if best:
                lst = best[1]
                r.update(status=NAME_MATCH, score="", reasons=f"found in the category listings ({lst['category']})",
                         title=lst["title"], price=lst["price"], regular_price=lst["regular_price"], in_stock="",
                         url=lst["url"])
                found += 1
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"{retailer}: {found} more barcoded lines found in the category listings")


def main(run_dir, extra_dirs):
    run_dir = Path(run_dir)
    catalog = merge_catalogs(run_dir, extra_dirs)
    sc.match(run_dir, catalog)
    barcoded_from_listings(run_dir, catalog)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
