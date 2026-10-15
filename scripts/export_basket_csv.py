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
        "section", "size", "source", "unit_price", "price_spec"]
META = ["class_code", "class_name", "group_code", "group_name", "name_ar", "brand_ar", "barcode_raw", "gtin", "qty_raw", "qty_unit",
        "qty_total", "qty_count", "origin_iso", "match_mode", "fresh_type"]


MIN_PACK = 5.0             # g / ml: a 1 g saffron tube is a piece, not 1/1000 of a kilo


def fill_unit_price(rows):
    """Every priced row gets unit_price / price_basis on the same unit (per kg, per litre or per piece), from the line's pack size,
    so pack prices (barcode lines) and per-unit prices (product-set lines) can be compared. 'price' itself is left as found.
    Packs under 5 g / 5 ml count per piece. Nothing is rejected: a dear item is simply shown at its unit price."""
    n = 0
    for r in rows:
        try:
            price, total = float(r.get("price") or 0), float(r.get("qty_total") or 0)
        except ValueError:
            continue
        if price <= 0:
            continue
        have = r.get("unit_price") not in (None, "")
        per_unit = r.get("source") == "category" or "product set" in str(r.get("detail") or "")
        if per_unit and r.get("price_basis") in ("kg", "l", "pc", "bunch", "bag100"):   # product-set lines: 'price' is already per unit
            r["unit_price"] = round(price, 2)
            continue
        if not have:
            if total <= 0:
                continue
            k = {"g": ("kg", 1000.0), "ml": ("l", 1000.0), "pc": ("pc", 1.0)}.get(r.get("qty_unit"))
            if not k:
                continue
            if k[1] > 1 and total < MIN_PACK:
                r["unit_price"], r["price_basis"] = round(price, 2), "pc"
                n += 1
                continue
            r["unit_price"], r["price_basis"] = round(price / (total / k[1]), 2), k[0]
            n += 1
    return n


def fill_spec_price(rows):
    """price_spec: the price in the line's OWN unit, the one the official file uses ('102 g' croissant, '1 kg' rice, 'piece'):
    unit price x the line's quantity. A listing of another size is scaled by its unit price (CPI quantity adjustment)."""
    n = 0
    for r in rows:
        try:
            up, total = float(r.get("unit_price") or 0), float(r.get("qty_total") or 0)
        except ValueError:
            continue
        if up <= 0 or total <= 0:
            continue
        f = {"g": 1000.0, "ml": 1000.0, "pc": 1.0}.get(r.get("qty_unit"))
        if f and r.get("price_basis") in ("kg", "l", "pc"):
            r["price_spec"] = round(up * total / f, 2)
            n += 1
    return n


def build(rows, run_id, out_dir=ROOT / "data/exports/dataiku"):
    """rows = a day's panel rows (found / not found per item and store); adds the items no search covers, the basket columns and cpi_group."""
    import panel_run                                   # items no search covers (service / name / market): one 'not found' row each
    basket = {b["item_code"]: b for b in json.load(open(ROOT / "data/basket/basket.json", encoding="utf-8"))}
    date = str(rows[0].get("run_date") or "")
    have = {r["item_code"] for r in rows}
    rows = list(rows) + [p for p in panel_run.pending_rows(date) if p["item_code"] not in have]   # an item the catalogue priced has its own rows
    for r in rows:
        m = basket.get(r["item_code"], {})
        for k in META:
            if r.get(k) in (None, "") and m.get(k) not in (None, ""):
                r[k] = m[k]
        r.setdefault("run_id", run_id)
        r["cpi_group"] = re.sub(r"^\d+\s*-\s*", "", str(m.get("group_name", ""))).strip()
        r.pop("thumb", None)
    fill_unit_price(rows)
    fill_spec_price(rows)
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
