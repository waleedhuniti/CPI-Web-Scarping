"""Excel files of the daily catalogue in the layout of Dubai_Bulk_Product_Catalogue.xlsx, one per download group.

    python scripts/catalogue_xlsx.py data/catalogue/2026-10-12 data/exports/catalogue

-> <out>/Dubai_Catalogue_<date>_all.xlsx and Dubai_Catalogue_<date>_<group>.xlsx (food, household, personal,
   electronics, clothing, other) + <out>/files.json (group, label, file, rows).
Sheets: Catalogue (Select, Outlet, Product name, Photo, Price (AED), Pack / size, Brand, Retailer ID, Availability,
Category, CPI division, Product URL, Photo URL, Collected (Dubai), Notes) and Collection notes. Photos are embedded
(data/thumbs, scripts/fetch_thumbs.py), as in the original file.
"""
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAVY, TITLE, GREY = "FF223F62", "FF173653", "FF627184"
HEAD = ["Select", "Outlet", "Product name", "Photo", "Price (AED)", "Pack / size", "Brand", "Retailer ID", "Availability",
        "Category", "CPI division", "Product URL", "Photo URL", "Collected (Dubai)", "Notes"]
WIDTHS = [7.8, 10.6, 44, 12, 10.2, 13, 14, 13, 12, 22, 26, 46.7, 30, 16, 50]
PX = 64


def thumb_bytes(url, cache={}):
    if url in cache:
        return cache[url]
    from PIL import Image
    f = ROOT / "data/thumbs" / (hashlib.sha1(url.encode()).hexdigest() + ".jpg")
    data = None
    if url and f.exists():
        im = Image.open(f).convert("RGB")
        im.thumbnail((PX, PX))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=62, optimize=True)
        data = buf.getvalue()
    cache[url] = data
    return data


def style(ws, title, subtitle, headers, widths):
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


def workbook(rows, dest, date, label, stores):
    import openpyxl
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.styles import Alignment, Font
    from openpyxl.worksheet.datavalidation import DataValidation
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Catalogue"
    style(ws, "Dubai bulk product catalogue" + ("" if label == "All groups" else f" · {label}"),
          f"{len(rows):,} listings • {date} • {', '.join(stores)} • Choose Yes in the first column, then filter • "
          "See Collection notes for scope", HEAD, WIDTHS)
    pics = 0
    for i, r in enumerate(rows, 6):
        ws.append(["No", r["outlet"], r["title"], None, float(r["price"]) if r["price"] else None, r["size"] or None,
                   r["brand"] or None, r["retailer_id"] or None, r["availability"], r["category"], r["division"],
                   r["url"], r["photo_url"] or None, r["collected"], r["notes"]])
        ws.cell(row=i, column=5).number_format = "#,##0.00"
        ws.row_dimensions[i].height = 52
        data = thumb_bytes(r["photo_url"])
        if data:
            img = XLImage(io.BytesIO(data))
            ws.add_image(img, f"D{i}")
            pics += 1
    for row in ws.iter_rows(min_row=6, max_col=3):
        row[2].alignment = Alignment(wrap_text=True, vertical="center")
    dv = DataValidation(type="list", formula1='"No,Yes"', allow_blank=False)
    ws.add_data_validation(dv)
    dv.add(f"A6:A{ws.max_row}")
    ws.auto_filter.ref = f"A5:{ws.cell(row=5, column=len(HEAD)).column_letter}{ws.max_row}"

    ws3 = wb.create_sheet("Collection notes")
    style(ws3, "Collection scope and reading guide", "Read before using prices for like-for-like comparisons",
          ["Topic", "Details"], [24, 110])
    counts = {}
    for r in rows:
        counts[r["outlet"]] = counts.get(r["outlet"], 0) + 1
    notes = [("How to choose", "Set Select to Yes on Catalogue, then use the column filter to show your basket.")]
    notes += [(o, f"{n:,} listings from public search / category results.") for o, n in counts.items()]
    notes += [
        ("Scope", "Every CPI division sold in UAE stores: food and drinks, household and cleaning, personal care and "
                  "health, electronics, phones and accessories, clothing and shoes, transport, recreation and education. "
                  "Stores selling their own goods only (no marketplaces or resellers)."),
        ("Price", "The price shown on the store's listing on the collection date, in AED, including VAT."),
        ("Pack / size", "What the price buys. Carrefour sells meat, fish, fruit and vegetables by weight: its card "
                        "price is for one weight step (e.g. 500 g), not per kg; Notes gives the per-kg price."),
        ("Photo", "Each product's picture is embedded; 'Photo URL' links to the full-size picture."),
        ("Availability", "As shown online; Dubai branch availability is not confirmed."),
        ("Method", "Collected automatically every day with Scrapling (Python)."),
    ]
    for t, d in notes:
        ws3.append([t, d])
    for row in ws3.iter_rows(min_row=6):
        row[0].font = Font(bold=True)
        row[1].alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(dest)
    return pics


def main(cat_dir, out_dir):
    cat_dir, out_dir = Path(cat_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = json.load(open(ROOT / "config/catalogue.json", encoding="utf-8"))
    rows = list(csv.DictReader(open(cat_dir / "catalog.csv", encoding="utf-8-sig")))
    date = cat_dir.name[:10]
    order = list(cfg["groups"])
    rows.sort(key=lambda r: (order.index(r["group"]) if r["group"] in order else 99, r["division"], r["category"], r["outlet"]))
    files = []
    for group, label in [("all", "All groups")] + list(cfg["groups"].items()):
        mine = rows if group == "all" else [r for r in rows if r["group"] == group]
        if not mine:
            continue
        dest = out_dir / f"Dubai_Catalogue_{date}_{group}.xlsx"
        stores = sorted({r["outlet"] for r in mine})
        pics = workbook(mine, dest, date, label, stores)
        files.append(dict(group=group, label=label, file=dest.name, rows=len(mine), photos=pics,
                          stores=stores, bytes=dest.stat().st_size))
        print(f"{dest.name}: {len(mine):,} rows, {pics:,} photos, {dest.stat().st_size / 1e6:.1f} MB", flush=True)
    (out_dir / "files.json").write_text(json.dumps(dict(date=date, files=files), indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
