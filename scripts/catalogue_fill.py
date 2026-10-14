"""Fill the day's basket run from the day's catalogue (the catalogue routine's catalogue.json asset).

    CPI_CATALOGUE_JSON=<catalogue.json> python scripts/panel_run.py <run> <started>      # panel_run calls rows()

rows(run_dir, catalogue_json, date) does, in this order, with the same rules as the live searches:
  1. barcoded lines the barcode / name searches did not find: name tier with exact pack size (fill_from_catalogue.py)
  2. named goods with a Latin model name (match_catalogue_items.py)
  3. goods with an Arabic-only name: English specs, product set or brand + exact size (arabic_goods.py)
and returns panel rows (source 'catalogue') for 2 and 3; step 1 rewrites <run>/<retailer>_matched.csv.
The result is cached in <run>/catalogue_rows.json, so a second call (panel_run runs twice) costs nothing.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

SLUG = {"Carrefour": "carrefour", "Lulu": "lulu", "Sharaf DG": "sharafdg", "Zara": "zara", "Centrepoint": "centrepoint", "Max": "max"}
LABEL = {"carrefour": "Carrefour", "lulu": "Lulu", "sharafdg": "Sharaf DG", "zara": "Zara", "centrepoint": "Centrepoint", "max": "Max"}
COLS = ["outlet", "store", "group", "division", "category", "title", "price", "regular_price", "size", "unit_price", "price_basis",
        "brand", "retailer_id", "availability", "url", "photo_url", "collected", "notes"]


def prepare(run_dir, catalogue_json):
    d = json.load(open(catalogue_json, encoding="utf-8"))
    cols = d["cols"]
    ref = Path(run_dir) / "catalogue_ref"
    ref.mkdir(exist_ok=True)
    with open(ref / "catalog.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in d["rows"]:
            row = dict(zip(cols, r))
            o = row["outlet"]
            row["store"] = "centrepoint" if "(Centrepoint)" in o else SLUG.get(o, o.lower().replace(" ", ""))   # Splash, Babyshop, Shoe Mart ... are Centrepoint
            w.writerow({c: row.get(c, "") for c in COLS})
    return ref, d["date"]


def rows(run_dir, catalogue_json, date):
    import arabic_goods
    import fill_from_catalogue
    import match_catalogue_items
    run_dir = Path(run_dir)
    cache = run_dir / "catalogue_rows.json"
    if cache.exists():
        return json.load(open(cache, encoding="utf-8"))
    ref, cat_date = prepare(run_dir, catalogue_json)
    fill_from_catalogue.fill_barcode(run_dir, ref)
    named = run_dir / "catalogue_named.csv"
    match_catalogue_items.main(ref, str(named))
    named_rows = [r for r in csv.DictReader(open(named, encoding="utf-8-sig")) if r["status"] == "found"]
    for r in named_rows:
        r["retailer"] = SLUG.get(r["retailer"], r["retailer"].lower().replace(" ", ""))
    arabic = arabic_goods.match(ref, str(run_dir / "catalogue_arabic.csv"))
    out = []
    for src, detail in ((named_rows, "catalogue name match"), (arabic, "catalogue product set (Arabic name)")):
        for r in src:
            out.append(dict(run_date=date, source="catalogue", retailer=r["retailer"], actor=f"{LABEL.get(r['retailer'], r['retailer'])} (catalogue)",
                            item_code=r["item_code"], group_code="", name="", brand="", basket_qty="", barcode="", status="found",
                            detail=detail, accepted="yes", title=r["title"], price=float(r["price"]),
                            regular_price=r.get("regular_price", ""), currency="AED", url=r["url"], photo=r.get("photo", ""),
                            retailer_id=r.get("retailer_id", ""), size="", in_stock="", price_basis=r.get("price_basis", ""),
                            n_products=r.get("n_products", ""),
                            note=(r.get("note", "") + f" · catalogue of {cat_date}").strip(" ·")))
    json.dump(out, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"catalogue {cat_date}: {len(out)} rows for {len({r['item_code'] for r in out})} lines")
    return out
