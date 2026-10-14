"""The one format for every basket file given to Dataiku: UTF-8 CSV, no BOM, fixed columns, plus cpi_group.

    python scripts/export_basket_csv.py data/runs/2026-10-12_full [data/exports/dataiku]
    -> <out>/CPI_basket_<date>_cpi_group.csv

Reads the run's panel documents (<run>/panel/c*.json, written by scripts/panel_run.py), adds the basket columns of each
item (class, group, quantity, barcode, origin) and cpi_group = the office's Arabic CPI group name (the basket's group name
without its code). Same columns and order as the panel's "all runs" download (DK_COLS in panel_artifact/scraping-panel.html).
"""
import csv
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
COLS = ["run_date", "run_id", "retailer", "actor", "item_code", "cpi_group", "barcode", "name", "brand", "basket_qty", "title",
        "price", "regular_price", "currency", "status", "accepted", "url", "barcode_raw", "basket_origin", "brand_ar", "class_code",
        "class_name", "detail", "fresh_type", "group_code", "group_name", "gtin", "in_stock", "match_mode", "name_ar", "note",
        "origin_iso", "origin_seen", "photo", "price_basis", "qty_count", "qty_raw", "qty_total", "qty_unit", "retailer_id",
        "section", "size", "source", "unit_price"]
META = ["class_code", "class_name", "group_code", "group_name", "name_ar", "brand_ar", "barcode_raw", "gtin", "qty_raw", "qty_unit",
        "qty_total", "qty_count", "origin_iso", "match_mode", "fresh_type"]


def build(rows, run_id, out_dir=ROOT / "data/exports/dataiku"):
    """rows = a day's panel rows (found / not found per item and store); adds the items no search covers, the basket columns and cpi_group."""
    import panel_run                                   # items no search covers (service / name / market): one 'not found' row each
    basket = {b["item_code"]: b for b in json.load(open(ROOT / "data/basket/basket.json", encoding="utf-8"))}
    date = str(rows[0].get("run_date") or "")
    rows = list(rows) + panel_run.pending_rows(date)
    for r in rows:
        m = basket.get(r["item_code"], {})
        for k in META:
            if r.get(k) in (None, "") and m.get(k) not in (None, ""):
                r[k] = m[k]
        r.setdefault("run_id", run_id)
        r["cpi_group"] = re.sub(r"^\d+\s*-\s*", "", str(m.get("group_name", ""))).strip()
        r.pop("thumb", None)
    cols = COLS + sorted({k for r in rows for k in r} - set(COLS))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"CPI_basket_{date}_cpi_group.csv"
    with open(dest, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, restval="")
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows -> {dest}")
    return dest


def main(run_dir, out_dir=ROOT / "data/exports/dataiku"):
    run_dir = Path(run_dir)
    run = json.load(open(run_dir / "panel/run.json", encoding="utf-8")) if (run_dir / "panel/run.json").exists() else {}
    rows = []
    for f in sorted(glob.glob(str(run_dir / "panel/c*.json"))):
        rows += json.load(open(f, encoding="utf-8"))["rows"]
    if not rows:
        sys.exit(f"no rows in {run_dir}/panel")
    build(rows, run.get("id") or run_dir.name, out_dir)


if __name__ == "__main__":
    main(*sys.argv[1:3])
