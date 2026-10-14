"""Standard Dataiku file for a run already stored in the panel, with the gaps the catalogue can fill, filled.

    python scripts/fill_export_from_portal.py <dir with the run's c*.json row documents> <catalogue.json> <date> <run_id>

For a run made before panel_run.py filled from the catalogue itself (same rules, applied to the stored rows): barcoded
rows 'not found' get the best catalogue listing of that shop (brand, product words, exact pack size), then the named
goods and the Arabic-only goods are added (catalogue_fill.rows). Writes data/exports/dataiku/CPI_basket_<date>_cpi_group.csv.
"""
import glob
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


def load_rows(chunk_dir):
    rows = []
    for f in sorted(glob.glob(str(Path(chunk_dir) / "c*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        d = d.get("data", d)
        rows += d["rows"]
    return rows


def fill_barcode_rows(rows, catalogue_json):
    import csv
    from cpi.basket import load_basket_any
    from cpi.quantity import parse_quantity
    import catalogue_fill
    import name_fallback as nf
    ref, _ = catalogue_fill.prepare(tempfile.mkdtemp(), catalogue_json)
    cat = [r for r in csv.DictReader(open(ref / "catalog.csv", encoding="utf-8-sig")) if r["price"]]
    by_shop = {}
    for c in cat:
        by_shop.setdefault(c["store"], []).append(c)
    items = {i.item_code: i for i in load_basket_any(ROOT) if i.barcode_kind == "gtin"}
    specs = nf.load_specs()
    n = 0
    for r in rows:
        if r.get("source") != "barcode" or r.get("status") == "found" or r["item_code"] not in items:
            continue
        it = items[r["item_code"]]
        spec, want = specs.get(it.item_code, {}), parse_quantity(it.qty_raw)
        best = None
        for c in by_shop.get(r["retailer"], []):
            s = nf.accept(c["title"], spec, want)
            if s >= 0 and (best is None or (s, -float(c["price"])) > (best[0], -float(best[1]["price"]))):
                best = (s, c)
        if best:
            c = best[1]
            r.update(status="found", accepted="yes", detail="name_match (catalogue)", title=c["title"], price=float(c["price"]),
                     regular_price=c["regular_price"], url=c["url"], photo=c["photo_url"], retailer_id=c["retailer_id"],
                     note="from the day's catalogue")
            n += 1
    print(f"{n} barcoded rows filled from the catalogue")


def main(chunk_dir, catalogue_json, date, run_id):
    import catalogue_fill
    import export_basket_csv
    rows = load_rows(chunk_dir)
    fill_barcode_rows(rows, catalogue_json)
    rows += catalogue_fill.rows(tempfile.mkdtemp(), catalogue_json, date)
    return export_basket_csv.build(rows, run_id)


if __name__ == "__main__":
    main(*sys.argv[1:5])
