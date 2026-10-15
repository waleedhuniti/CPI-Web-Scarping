"""One day's basket file for Dataiku with every gap that the day's catalogue can fill, filled.

    python scripts/build_filled_export.py <run_dir> <catalogue_dir> <history.json> <date> [run_id]

run_dir: the basket run (barcode searches, category crawl catalog.csv); catalogue_dir: the same day's catalogue.
Steps: barcoded lines the searches missed (name tier, exact size) -> product-set prices of the no-barcode food lines ->
named goods (Latin model names, match_catalogue_items.py) -> Arabic-only goods (arabic_goods.py) -> the standard file
data/exports/dataiku/CPI_basket_<date>_cpi_group.csv (export_basket_csv.py).
"""
import csv
import glob
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def main(run_dir, cat_dir, hist, date, run_id=None):
    import arabic_goods
    import export_basket_csv
    import fill_from_catalogue
    import scrapling_category as sc
    work = Path(tempfile.mkdtemp())
    shutil.copytree(run_dir, work / "run")
    run = work / "run"
    fill_from_catalogue.fill_barcode(run, cat_dir)
    py = sys.executable
    subprocess.run([py, str(ROOT / "scripts/product_panel.py"), "series", str(hist), str(run)], check=True)
    sc.enrich_origins = lambda *a, **k: None
    sc.match(run, delay=0)
    flip = {b["item_code"] for b in json.load(open(ROOT / "data/basket/basket.json", encoding="utf-8")) if b.get("product_set_from_barcode")}
    for rt in ("carrefour", "lulu"):                      # barcoded lines moved to the product set are not searched any more
        p = run / f"{rt}_matched.csv"
        if p.exists():
            rows = [r for r in csv.DictReader(open(p, encoding="utf-8-sig")) if r["item_code"] not in flip]
            with open(p, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    subprocess.run([py, str(ROOT / "scripts/panel_run.py"), str(run), f"{date}T06:00:00+00:00"], check=True)
    rows = []
    for f in sorted(glob.glob(str(run / "panel/c*.json"))):
        rows += json.load(open(f, encoding="utf-8"))["rows"]
    named = work / "named.csv"
    subprocess.run([py, str(ROOT / "scripts/match_catalogue_items.py"), str(cat_dir), str(named)], check=True)
    named_rows = [r for r in csv.DictReader(open(named, encoding="utf-8-sig")) if r["status"] == "found"]
    arabic = arabic_goods.match(cat_dir, str(work / "arabic.csv"))
    have = {r["item_code"] for r in rows if r.get("status") == "found"}
    for src, label, detail in ((named_rows, "catalogue", "catalogue name match"), (arabic, "catalogue", "catalogue product set (Arabic name)")):
        for r in src:
            if r["item_code"] in have and r["item_code"] not in {x["item_code"] for x in src}:
                continue
            rows.append(dict(run_date=date, source="catalogue", retailer=r["retailer"], actor=f"{r['retailer']} (catalogue)", item_code=r["item_code"],
                             group_code="", name="", brand="", basket_qty="", barcode="", status="found", detail=detail, accepted="yes",
                             title=r["title"], price=r["price"], regular_price=r.get("regular_price", ""), currency="AED", url=r["url"],
                             photo=r.get("photo", ""), retailer_id=r.get("retailer_id", ""), note=r.get("note", ""),
                             n_products=r.get("n_products", ""), price_basis=r.get("price_basis", "")))
    return export_basket_csv.build(rows, run_id or f"{date}-filled")


if __name__ == "__main__":
    main(*sys.argv[1:])
