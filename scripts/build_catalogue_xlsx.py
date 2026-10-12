"""Product catalogue and basket prices as one workbook, in the layout of 'Dubai_Bulk_Product_Catalogue.xlsx'.

    python scripts/build_catalogue_xlsx.py data/exports/Dubai_Bulk_Product_Catalogue.xlsx \
        data/runs/2026-10-08_catalogue data/runs/2026-10-12_full

Sheets
  Catalogue        every product listing of the given runs (bulk category listings and the products found by barcode or
                   name search), one row per listing and date: the price as shown, what quantity that price is for, and
                   the price per kg / litre / piece / bunch. 'Select' (No/Yes) to filter, as in the original.
  Basket prices    the 637 basket lines: found or not found at each retailer on each date, the price, the unit price and
                   the change between the first and the last date.
  Collection notes how the data was collected and how to read the prices.
"""
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cpi.basket import load_basket_any  # noqa: E402
from cpi.decision import barcode_found, category_found  # noqa: E402

NAVY, TITLE, GREY = "FF223F62", "FF173653", "FF627184"
PHOTOS = ROOT / "data/photos.json"
STOPW = {"fresh", "the", "and", "with", "of", "a", "per", "kg", "g", "loose", "pack", "local", "imported"}


def photo_cache():
    import json
    return json.loads(PHOTOS.read_text()) if PHOTOS.exists() else {}


def image_formula(url):
    """The Photo cell itself stays empty: the picture is embedded over it (see embed_photo)."""
    return None


def embed_photo(ws, url, cell, px=56):
    """Embed the product picture (data/thumbs, scripts/fetch_thumbs.py) over the cell, like the original catalogue."""
    import hashlib
    from openpyxl.drawing.image import Image as XLImage
    if not url:
        return False
    f = ROOT / "data/thumbs" / (hashlib.sha1(url.encode()).hexdigest() + ".jpg")
    if not f.exists():
        return False
    import io
    from PIL import Image
    im = Image.open(f).convert("RGB")
    im.thumbnail((px, px))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=55, optimize=True)      # small enough to keep the workbook under ~25 MB
    ws.add_image(XLImage(io.BytesIO(buf.getvalue())), cell)
    return True


def toks(text):
    return {w for w in re.findall(r"[a-z]+", str(text).lower()) if len(w) > 2 and w not in STOPW}
RETAILERS = {"carrefour": "Carrefour", "lulu": "Lulu", "spinneys": "Spinneys"}
BASIS = {"kg": "per kg", "l": "per litre", "pc": "per piece", "bunch": "per bunch"}


def run_date(run_dir):
    m = re.match(r"(\d{4}-\d{2}-\d{2})", Path(run_dir).name)
    return m.group(1) if m else Path(run_dir).name


def read(path):
    return list(csv.DictReader(open(path, encoding="utf-8-sig"))) if Path(path).exists() else []


def catalogue_rows(run_dirs, cache=None):
    cache = cache or {}
    out = []
    for d in run_dirs:
        date = run_date(d)
        for r in read(Path(d) / "catalog.csv"):
            out.append(dict(outlet=RETAILERS.get(r["retailer"], r["retailer"]), name=r["title"], price=r["price"],
                            price_for=r.get("size", ""), unit_price=r.get("unit_price", ""),
                            unit=BASIS.get(r.get("price_basis", ""), ""), origin=r.get("origin_seen", ""), barcode="",
                            retailer_id=r.get("retailer_id", "") or (re.search(r"/p/([^/?]+)", r["url"]) or [None, ""])[1],
                            availability=r.get("availability", ""), category=r.get("category", ""), url=r["url"],
                            photo_url=r.get("photo_url") or cache.get(r["url"], ""), collected=r.get("collected") or date,
                            source="bulk category listing", note=r.get("price_note", "")))
        for retailer in ("carrefour", "lulu"):
            for r in read(Path(d) / f"{retailer}_matched.csv"):
                if barcode_found(r["status"]) and r.get("url") and "catalogue" not in Path(d).name:
                    out.append(dict(outlet=RETAILERS[retailer], name=r["title"], price=r["price"], price_for="pack",
                                    unit_price="", unit="", origin="", barcode=r["barcode"],
                                    retailer_id=(re.search(r"/p/([^/?]+)", r["url"]) or [None, ""])[1],
                                    availability=r.get("in_stock", ""), category="barcode / name search", url=r["url"],
                                    photo_url=cache.get(r["url"], ""), collected=date,
                                    source="barcode search" if r["status"] != "name_match" else "name search",
                                    note=r.get("reasons", "")))
    return out


def basket_rows(run_dirs, catalogue=(), cache=None):
    import json
    cache = cache or {}
    specs = {x["c"]: x for x in json.loads((ROOT / "data/basket/specs_en.json").read_text(encoding="utf-8"))}
    pics = [(toks(c["name"]), c["photo_url"]) for c in catalogue if c.get("photo_url")]
    items = load_basket_any(ROOT)
    dates = [run_date(d) for d in run_dirs]
    res = {}   # (item_code, retailer, date) -> dict(price, unit_price, unit, title)
    for d, date in zip(run_dirs, dates):
        for retailer in ("carrefour", "lulu"):
            for r in read(Path(d) / f"{retailer}_matched.csv"):
                if barcode_found(r["status"]):
                    res[(r["item_code"], retailer, date)] = dict(price=r["price"], unit_price=r["price"], unit="per pack",
                                                                 title=r["title"], url=r.get("url", ""))
        crows = read(Path(d) / "category_matches.csv")
        lines = {}
        for r in crows:
            lines.setdefault((r["retailer"], r["name_ar"]), set()).add(r["item_code"])
        for r in crows:
            if category_found(r["status"], len(lines[(r["retailer"], r["name_ar"])]) == 1):
                res[(r["item_code"], r["retailer"], date)] = dict(price=r["price"], unit_price=r["unit_price"],
                                                                  unit=BASIS.get(r["price_basis"], ""), title=r["title"],
                                                                  url=r.get("url", ""))
    out = []
    for it in items:
        row = dict(item_code=it.item_code, group=it.group_name or it.group_code, name_ar=it.name_ar, brand_ar=it.brand_ar,
                   qty=it.qty_raw, origin=it.origin_raw, method="barcode" if it.barcode_kind == "gtin" else "bulk listing",
                   barcode=it.barcode_raw if it.barcode_kind == "gtin" else "")
        for retailer in ("carrefour", "lulu"):
            vals = []
            for date in dates:
                x = res.get((it.item_code, retailer, date))
                row[f"{retailer}|{date}"] = float(x["unit_price"]) if x and x["unit_price"] not in ("", None) else None
                row[f"{retailer}|{date}|t"] = x["title"] if x else ""
                row[f"{retailer}|unit"] = row.get(f"{retailer}|unit") or (x["unit"] if x else "")
                vals.append(row[f"{retailer}|{date}"])
            first, last = vals[0], vals[-1]
            row[f"{retailer}|chg"] = (last - first) / first if first and last else None
        # latest price: the most recent date with a price, Carrefour first on the same date
        row["latest"], row["latest_from"] = None, ""
        for date in reversed(dates):
            for retailer in ("carrefour", "lulu"):
                v = row[f"{retailer}|{date}"]
                if v is not None and row["latest"] is None:
                    row["latest"] = v
                    row["latest_from"] = f"{RETAILERS[retailer]} {datetime.fromisoformat(date).strftime('%-d %b')} ({row[f'{retailer}|unit']})"
        # photo: the matched product (latest date first), else the most similar listing in the catalogue
        row["photo"], row["photo_is"] = "", ""
        for date in reversed(dates):
            for retailer in ("carrefour", "lulu"):
                x = res.get((it.item_code, retailer, date))
                if x and not row["photo"] and cache.get(x.get("url", "")):
                    row["photo"], row["photo_is"] = cache[x["url"]], "the matched product"
        if not row["photo"] and pics:
            sp = specs.get(it.item_code, {})
            want = toks(" ".join([sp.get("query_en", ""), sp.get("product_en", ""), sp.get("brand_en", "")]))
            if want:
                score, url = max(((len(want & t) / len(want), u) for t, u in pics), key=lambda p: p[0])
                if score > 0:
                    row["photo"], row["photo_is"] = url, "similar product (illustration)"
        out.append(row)
    return out, dates


def style_sheet(ws, title, subtitle, headers, widths):
    from openpyxl.styles import Alignment, Font, PatternFill
    ws["A2"] = title
    ws["A2"].font = Font(size=16, bold=True, color=TITLE)
    ws["A3"] = subtitle
    ws["A3"].font = Font(size=10, color=GREY)
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=5, column=i, value=h)
        c.font = Font(bold=True, color="FFFFFFFF")
        c.fill = PatternFill("solid", fgColor=NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[5].height = 32
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(row=5, column=i).column_letter].width = w
    ws.freeze_panes = "A6"


def main(dest, run_dirs):
    import openpyxl
    from openpyxl.styles import Alignment, Font
    from openpyxl.worksheet.datavalidation import DataValidation
    wb = openpyxl.Workbook()

    # ---------------- Catalogue
    ws = wb.active
    ws.title = "Catalogue"
    cache = photo_cache()
    rows = catalogue_rows(run_dirs, cache)
    heads = ["Select", "Outlet", "Product name", "Photo", "Price (AED)", "Price is for", "Unit price (AED)", "Unit",
             "Origin", "Barcode", "Retailer ID", "Availability", "Category", "Product URL", "Photo URL",
             "Collected (Dubai)", "Source", "Notes"]
    dates = ", ".join(datetime.fromisoformat(run_date(d)).strftime("%-d %b %Y") for d in run_dirs)
    style_sheet(ws, "Dubai bulk product catalogue",
                f"{len(rows):,} listings • {dates} • Choose Yes in the first column, then filter • "
                "'Price is for' is the quantity the shown price buys; 'Unit price' converts it to per kg / litre / piece",
                heads, [7.8, 10.6, 40, 12, 10.2, 14, 11.5, 9, 7, 15, 11.7, 12, 24, 46.7, 30, 16, 18, 40])
    for r in rows:
        ws.append(["No", r["outlet"], r["name"], None,
                   float(r["price"]) if r["price"] not in ("", None) else None,
                   r["price_for"], float(r["unit_price"]) if r["unit_price"] not in ("", None) else None, r["unit"],
                   r["origin"], r["barcode"], r["retailer_id"], r["availability"], r["category"], r["url"],
                   r["photo_url"], r["collected"], r["source"], r["note"]])
    pics = sum(embed_photo(ws, r["photo_url"], f"D{i}") for i, r in enumerate(rows, 6))
    print(f"Catalogue: {pics:,} of {len(rows):,} photos embedded")
    for row in ws.iter_rows(min_row=6, min_col=5, max_col=7):
        for c in row:
            if c.column in (5, 7):
                c.number_format = "#,##0.00"
    for i in range(6, ws.max_row + 1):
        ws.row_dimensions[i].height = 60
    dv = DataValidation(type="list", formula1='"No,Yes"', allow_blank=False)
    ws.add_data_validation(dv)
    dv.add(f"A6:A{ws.max_row}")
    ws.auto_filter.ref = f"A5:{ws.cell(row=5, column=len(heads)).column_letter}{ws.max_row}"

    # ---------------- Basket prices
    ws2 = wb.create_sheet("Basket prices")
    brows, ds = basket_rows(run_dirs, rows, cache)
    heads2 = ["Item code", "Photo", "Photo is", "Group", "Arabic item name", "Brand", "Basket size", "Origin", "Method", "Barcode",
              "Latest price (AED)", "Latest from"]
    for retailer in ("carrefour", "lulu"):
        heads2 += [f"{RETAILERS[retailer]} {datetime.fromisoformat(d).strftime('%-d %b')}" for d in ds]
        heads2 += [f"{RETAILERS[retailer]} unit", f"{RETAILERS[retailer]} change", f"{RETAILERS[retailer]} product (latest)"]
    found = sum(1 for r in brows if r.get(f"carrefour|{ds[-1]}") is not None or r.get(f"lulu|{ds[-1]}") is not None)
    anyd = sum(1 for r in brows if r["latest"] is not None)
    style_sheet(ws2, "Basket prices",
                f"{len(brows)} basket lines • {anyd} with a price ({found} on {ds[-1]}) • blank = not found (no review states) • "
                "barcoded lines priced per pack, lines without a barcode per kg / piece / bunch",
                heads2, [12, 12, 16, 22, 30, 14, 10, 10, 12, 15, 11, 22] + [11] * len(ds) + [10, 10, 40] + [11] * len(ds) + [10, 10, 40])
    for r in brows:
        vals = [r["item_code"], None, r["photo_is"], r["group"], r["name_ar"], r["brand_ar"], r["qty"],
                r["origin"], r["method"], r["barcode"], r["latest"], r["latest_from"]]
        for retailer in ("carrefour", "lulu"):
            vals += [r[f"{retailer}|{d}"] for d in ds]
            vals += [r[f"{retailer}|unit"], r[f"{retailer}|chg"], r[f"{retailer}|{ds[-1]}|t"]]
        ws2.append(vals)
    pics = sum(embed_photo(ws2, r["photo"], f"B{i}") for i, r in enumerate(brows, 6))
    print(f"Basket prices: {pics} of {len(brows)} photos embedded")
    n = len(ds)
    for row in ws2.iter_rows(min_row=6):
        for c in row:
            k = c.column - 13
            if c.column == 11:
                c.number_format = "#,##0.00"
            elif 0 <= k < n or n + 3 <= k < 2 * n + 3:
                c.number_format = "#,##0.00"
            elif k in (n + 1, 2 * n + 4):
                c.number_format = "+0.0%;-0.0%;0.0%"
    for i in range(6, ws2.max_row + 1):
        ws2.row_dimensions[i].height = 60
    ws2.auto_filter.ref = f"A5:{ws2.cell(row=5, column=len(heads2)).column_letter}{ws2.max_row}"

    # ---------------- Collection notes
    ws3 = wb.create_sheet("Collection notes")
    style_sheet(ws3, "Collection scope and reading guide", "Read before using prices for like-for-like comparisons",
                ["Topic", "Details"], [24, 110])
    notes = [
        ("How to choose", "Set Select to Yes on Catalogue, then use the column filter to show your basket."),
        ("Dates", "Each run folder is one collection date: " + ", ".join(Path(d).name for d in run_dirs) + "."),
        ("Price basis", "Carrefour sells meat, fish, fruit and vegetables by weight; the price on its card is for one "
                        "weight step (usually 500 g, 300 g for steaks), not per kg. 'Price is for' shows that step and "
                        "'Unit price' is the per-kg price. In the 8 Oct 2026 source these rows said 'kilo'; they were "
                        "converted with the product's step (Notes column)."),
        ("Found / not found", "A basket line is found when the retailer sells the same product: same barcode, or the "
                              "same brand, product and exact size; for lines without a barcode the same product from "
                              "the basket origin. Anything else is not found. There are no review states."),
        ("Barcoded lines", "Barcode search on each retailer's site, then a name search (brand + exact size) for barcodes "
                           "the retailer does not list. The 8 Oct source has no barcodes, so that date uses the name rule only."),
        ("Lines without a barcode", "Whole category listings are collected (meat, fish, fruit, vegetables, bakery, dairy "
                                    "and eggs, rice and pasta, baking and sugar, nuts and dates, spreads, tins, frozen, "
                                    "sauces, cereals, biscuits, cooking ingredients ...) and matched by product words, "
                                    "unit and origin. Barcoded lines the searches miss also get a last chance in these "
                                    "listings (same brand, product and exact size)."),
        ("Latest price", "Basket prices shows each line's most recent price from any date and retailer (Carrefour "
                         "first on the same date) and where it came from, so a line priced only on 8 Oct still has a price."),
        ("Change", "Change is (latest - first) / first for the same retailer and the same unit; blank when the line "
                   "was not found on one of the dates."),
        ("Photos", "Each product's picture is embedded in the Photo column; 'Photo URL' links to the full-size picture. "
                   "In Basket prices a line without a found product shows the most "
                   "similar product's photo, marked 'similar product (illustration)'."),
        ("Scope", "Public UAE retailer websites (Carrefour, Lulu); no delivery address selected. Spinneys blocks "
                  "automated access and is only present in the 8 Oct source where it supplied prices."),
    ]
    for t, d in notes:
        ws3.append([t, d])
    for row in ws3.iter_rows(min_row=6):
        row[0].font = Font(bold=True)
        row[1].alignment = Alignment(wrap_text=True, vertical="top")
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    wb.save(dest)
    print(f"{dest}: {len(rows):,} catalogue rows, {len(brows)} basket lines ({anyd} with a price, {found} priced on {ds[-1]})")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
