"""One long, stable table of every barcode run in data/runs/ - the file Dataiku reads.

    python scripts/export_for_dataiku.py                 # -> data/exports/cpi_prices_long.csv

One row per run x retailer x basket line, fixed columns (see COLUMNS), UTF-8 with BOM so Excel shows Arabic.
Reads every <run>/<retailer>_matched.csv (Apify and Scrapling runs alike); the run date is the folder's date.
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cpi.matcher import ACCEPTED  # noqa: E402

COLUMNS = ["run_date", "run_id", "source", "retailer", "item_code", "group_code", "name_ar", "brand_ar", "basket_qty",
           "barcode", "status", "accepted", "title", "price", "regular_price", "currency", "in_stock", "url"]


def rows():
    for f in sorted(ROOT.glob("data/runs/*/*_matched.csv")):
        run = f.parent.name
        m = re.match(r"(\d{4}-\d{2}-\d{2})", run)
        if not m or "test" in run or f.stem.count("_") != 1:   # carrefour/lulu_matched.csv of real runs only
            continue
        retailer = f.stem.split("_")[0]
        for r in csv.DictReader(open(f, encoding="utf-8-sig")):
            if r.get("status") == "not_searched":
                continue
            yield dict(run_date=m.group(1), run_id=run, source="scrapling" if "scrapling" in run else "apify",
                       retailer=retailer, item_code=r.get("item_code", ""), group_code=r.get("group", ""),
                       name_ar=r.get("name_ar", ""), brand_ar=r.get("brand_ar", ""), basket_qty=r.get("basket_qty", ""),
                       barcode=r.get("barcode", ""), status=r.get("status", ""),
                       accepted="yes" if r.get("status") in ACCEPTED else "no", title=r.get("title", ""),
                       price=r.get("price", ""), regular_price=r.get("regular_price", ""), currency="AED",
                       in_stock=r.get("in_stock", ""), url=r.get("url", ""))


def main(dest=ROOT / "data/exports/cpi_prices_long.csv"):
    dest.parent.mkdir(parents=True, exist_ok=True)
    out = list(rows())
    with open(dest, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(out)
    runs = sorted({r["run_id"] for r in out})
    print(f"{len(out)} rows from {len(runs)} runs ({', '.join(runs)}) -> {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
