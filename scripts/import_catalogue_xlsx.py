"""Bring a product-catalogue workbook (sheet 'Catalogue', header on row 5: Select, Outlet, Product name, Photo,
Price (AED), Pack / size, Brand, Barcode, Retailer ID, Availability, Category, Product URL, Photo URL,
Collected (Dubai), Notes) into a run folder, and price the basket from it.

    python scripts/import_catalogue_xlsx.py Dubai_Bulk_Product_Catalogue.xlsx data/runs/2026-10-08_catalogue

1. catalog.csv in the bulk-crawl schema, with the price basis corrected: Carrefour sells fresh produce, meat and fish
   by weight and its card price is for one weight step (500 g, 300 g, 1.2 kg ...), not per kg. Rows with pack 'kilo'
   are converted with that product's step, taken from our latest crawl of the same product, else from the product
   page ("weights":[0.5,...]). price_note says which.
2. Basket matching on that catalogue, with the same yes/no rules as the live runs:
   - lines without a barcode: scripts/scrapling_category.match (product words, unit, origin)
   - barcoded lines: the catalogue has no barcodes, so a listing counts only with the same brand, the product words
     and the exact basket size (scripts/name_fallback.accept) -> <retailer>_matched.csv with status name_match.
"""
import csv
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from cpi.basket import load_basket_any  # noqa: E402
from cpi.quantity import find_quantity, parse_quantity  # noqa: E402
import match_run  # noqa: E402
import name_fallback as nf  # noqa: E402
import scrapling_category as sc  # noqa: E402

GROUPS = [  # catalogue category words -> COICOP group(s); first hit wins
    (r"beef|lamb|mutton|chicken|poultry|meat", "0112"), (r"fish|seafood|shrimp|prawn", "0113"),
    (r"fruits? vegetables|fruits?.*veg", "0116,0117"), (r"fruit", "0116"), (r"vegetable|herb", "0117,0119"),
    (r"milk|yoghurt|yogurt|egg|cheese|dairy|labneh", "0114"), (r"rice|flour|bread|bak|pasta|noodle|cereal|oat", "0111"),
    (r"\boil\b|ghee|butter", "0115"), (r"sugar|sweet|honey|jam|chocolate|biscuit|confection", "0118"),
    (r"salt|spice|cooking|ingredient|sauce", "0119"), (r"frozen|cupboard|grocery", "0111,0112,0113,0114,0115,0116,0117,0118,0119"),
]
NON_FOOD = r"detergent|soap|shampoo|toothpaste|household|cleaning|laundry|dishwash|tissue|diaper"


def group_of(category):
    c = str(category or "").lower().replace("/?page_size=50", "")
    if re.search(NON_FOOD, c):
        return ""
    for pat, g in GROUPS:
        if re.search(pat, c):
            return g
    return "0111,0112,0113,0114,0115,0116,0117,0118,0119"


def pid(url):
    m = re.search(r"/p/([^/?]+)", url or "")
    return m.group(1).lower() if m else None


def known_steps():
    """Carrefour product id -> weight step in kg, from our own crawls ('500g - Approx 19 pieces')."""
    steps = {}
    for f in sorted(glob.glob(str(ROOT / "data/runs/*/catalog.csv"))):
        for r in csv.DictReader(open(f, encoding="utf-8-sig")):
            if r["retailer"] == "carrefour" and r.get("price_basis") == "kg":
                q = find_quantity((r.get("size") or "").split(" - ")[0])
                if q.unit == "g" and q.total:
                    steps[pid(r["url"])] = q.total / 1000
    return steps


def page_step(url):
    from scrapling.fetchers import Fetcher
    try:
        p = Fetcher.get(url, impersonate="chrome", timeout=30)
        html = p.body.decode("utf-8", "ignore") if isinstance(p.body, bytes) else str(p.body)
        m = re.search(r'\\?"weights\\?"\s*:\s*\[\s*([\d.]+)', html)
        return float(m.group(1)) if m else None
    except Exception:
        return None


def read_catalogue(xlsx):
    import openpyxl
    ws = openpyxl.load_workbook(xlsx, read_only=True)["Catalogue"]
    head = [str(c or "").strip() for c in next(ws.iter_rows(min_row=5, max_row=5, values_only=True))]
    for row in ws.iter_rows(min_row=6, values_only=True):
        r = dict(zip(head, row))
        if r.get("Product name"):
            yield r


def build_catalog(xlsx, run_dir):
    steps, out = known_steps(), []
    for r in read_catalogue(xlsx):
        retailer = str(r["Outlet"]).strip().lower()
        price = r.get("Price (AED)")
        pack = str(r.get("Pack / size") or "").strip()
        url = r.get("Product URL") or ""
        row = dict(retailer=retailer, group=group_of(r.get("Category")), category=r.get("Category") or "",
                   title=str(r["Product name"]).strip(), price=price if price not in (None, "") else "",
                   regular_price=price if price not in (None, "") else "", size=pack, unit_price="", price_basis="",
                   origin_seen=sc.origin_of(str(r["Product name"])), url=url, retailer_id=r.get("Retailer ID") or "",
                   availability=r.get("Availability") or "", photo_url=r.get("Photo URL") or "",
                   collected=str(r.get("Collected (Dubai)") or ""), price_note="")
        if row["price"] == "":
            row["price_note"] = "no price in the source"
        elif retailer == "carrefour" and pack.lower() == "kilo":
            step = steps.get(pid(url))
            src = "step from our crawl"
            if step is None:
                step, src = page_step(url), "step from the product page"
            if step:
                row.update(size=f"{step * 1000:g}g", unit_price=round(float(price) / step, 2), price_basis="kg",
                           price_note=f"source said 'kilo'; the price is for {step * 1000:g} g ({src})")
            else:
                row["price_note"] = "source said 'kilo'; weight step unknown - per-kg price not computed"
        else:
            per, basis = sc.price_basis(dict(title=row["title"], price=float(price), size_text=pack))
            row.update(unit_price=per if per is not None else "", price_basis=basis)
        out.append(row)
    run_dir.mkdir(parents=True, exist_ok=True)
    with open(run_dir / "catalog.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    fixed = sum(1 for r in out if r["price_note"].startswith("source said 'kilo'; the price"))
    print(f"{len(out)} listings -> {run_dir / 'catalog.csv'} ({fixed} 'kilo' prices converted to per kg)")
    return out


def match_barcoded(run_dir, catalog):
    """Barcoded basket lines against the catalogue by brand + product words + exact size (no barcodes in the source)."""
    specs = nf.load_specs()
    items = [i for i in load_basket_any(ROOT) if i.barcode_kind == "gtin"]
    for retailer in ("carrefour", "lulu"):
        listings = [r for r in catalog if r["retailer"] == retailer and r["price"] != ""]
        rows, found = [], 0
        for it in items:
            spec, want_q = specs.get(it.item_code, {}), parse_quantity(it.qty_raw)
            best = None
            for lst in listings:
                score = nf.accept(lst["title"], spec, want_q)
                if score >= 0 and (best is None or (score, -float(lst["price"])) > (best[0], -float(best[1]["price"]))):
                    best = (score, lst)
            base = dict(item_code=it.item_code, group=it.group_code, name_ar=it.name_ar, brand_ar=it.brand_ar,
                        basket_qty=it.qty_raw, barcode=match_run.search_form(it.barcode_raw), score="")
            if best:
                lst = best[1]
                found += 1
                rows.append(dict(base, status="name_match", reasons="catalogue listing: same brand, product and size",
                                 title=lst["title"], price=lst["price"], regular_price=lst["regular_price"],
                                 in_stock=lst["availability"], url=lst["url"]))
            else:
                rows.append(dict(base, status="not_found", reasons="no listing with the same brand and size",
                                 title="", price="", regular_price="", in_stock="", url=""))
        with open(run_dir / f"{retailer}_matched.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"{retailer}: {found} of {len(items)} barcoded lines found in the catalogue (by brand + size)")


def main(xlsx, run_dir):
    run_dir = Path(run_dir)
    catalog = build_catalog(xlsx, run_dir)
    match_barcoded(run_dir, catalog)
    food = [dict(r, price=str(r["price"]), unit_price=str(r["unit_price"])) for r in catalog
            if r["group"] and r["retailer"] in ("carrefour", "lulu")]
    sc.match(run_dir, food)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
