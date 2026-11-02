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

from cpi.decision import barcode_found, category_found  # noqa: E402

COLUMNS = ["run_date", "run_id", "source", "retailer", "item_code", "group_code", "name_ar", "brand_ar", "basket_qty",
           "barcode", "status", "detail", "accepted", "title", "price", "regular_price", "unit_price", "price_basis",
           "basket_origin", "origin_seen", "currency", "in_stock", "url"]


def source_of(run, default):
    return "catalogue" if "catalogue" in run else default


def superseded(run):
    """A partial run of a day that also has a combined *_full run (the full run already carries its rows)."""
    day = run[:10]
    return not run.endswith("_full") and (ROOT / "data/runs" / f"{day}_full").exists()


def rows():
    for f in sorted(ROOT.glob("data/runs/*/*_matched.csv")):
        run = f.parent.name
        m = re.match(r"(\d{4}-\d{2}-\d{2})", run)
        if not m or "test" in run or superseded(run) or f.stem.count("_") != 1:   # carrefour/lulu_matched.csv of real runs only
            continue
        retailer = f.stem.split("_")[0]
        for r in csv.DictReader(open(f, encoding="utf-8-sig")):
            if r.get("status") == "not_searched":
                continue
            yield dict(run_date=m.group(1), run_id=run, source=source_of(run, "scrapling" if "scrapling" in run or run.endswith("_full") else "apify"),
                       retailer=retailer, item_code=r.get("item_code", ""), group_code=r.get("group", ""),
                       name_ar=r.get("name_ar", ""), brand_ar=r.get("brand_ar", ""), basket_qty=r.get("basket_qty", ""),
                       barcode=r.get("barcode", ""), status="found" if barcode_found(r.get("status", "")) else "not_found",
                       detail=r.get("status", ""), accepted="yes" if barcode_found(r.get("status", "")) else "no",
                       title=r.get("title", "") if barcode_found(r.get("status", "")) else "",
                       price=r.get("price", "") if barcode_found(r.get("status", "")) else "",
                       regular_price=r.get("regular_price", "") if barcode_found(r.get("status", "")) else "",
                       currency="AED", unit_price="", price_basis="", basket_origin="", origin_seen="",
                       in_stock=r.get("in_stock", ""), url=r.get("url", "") if barcode_found(r.get("status", "")) else "")


def category_rows():
    """Non-barcode lines (meat, fish, fruit, vegetables) from the bulk category runs: one row per line x retailer."""
    for f in sorted(ROOT.glob("data/runs/*/category_matches.csv")):
        run = f.parent.name
        m = re.match(r"(\d{4}-\d{2}-\d{2})", run)
        if not m or "test" in run or superseded(run):
            continue
        crows = list(csv.DictReader(open(f, encoding="utf-8-sig")))
        lines = {}
        for r in crows:
            lines.setdefault((r["retailer"], r["name_ar"]), set()).add(r["item_code"])
        for r in crows:
            ok = category_found(r["status"], len(lines[(r["retailer"], r["name_ar"])]) == 1)
            keep = lambda v: v  # preserve candidate evidence even when not accepted
            yield dict(run_date=m.group(1), run_id=run, source=source_of(run, "scrapling-category"), retailer=r["retailer"],
                       item_code=r["item_code"], group_code=r["group"], name_ar=r["name_ar"], brand_ar="",
                       basket_qty=r["basket_qty"], barcode="", status="found" if ok else "not_found",
                       detail=r["status"], accepted="yes" if ok else "no", title=keep(r["title"]),
                       price=keep(r["price"]), regular_price=keep(r["regular_price"]), unit_price=keep(r["unit_price"]),
                       price_basis=r["price_basis"], basket_origin=r["basket_origin"], origin_seen=keep(r["origin_seen"]),
                       currency="AED", in_stock="", url=keep(r["url"]))


def main(dest=ROOT / "data/exports/cpi_prices_long.csv"):
    dest.parent.mkdir(parents=True, exist_ok=True)
    out = list(rows()) + list(category_rows())
    with open(dest, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(out)
    runs = sorted({r["run_id"] for r in out})
    print(f"{len(out)} rows from {len(runs)} runs ({', '.join(runs)}) -> {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

