"""The daily catalogue as two JSON files for the panel (uploaded as artifact assets; the panel builds the Excel files).

    python scripts/catalogue_assets.py data/catalogue/2026-10-12

-> <dir>/catalogue.json  {"date", "groups": {key: label}, "cols": [...], "rows": [[...], ...]}
   <dir>/thumbs.json     {"date", "thumbs": {photo url: base64 jpeg}}   (64 px pictures from data/thumbs)
   <dir>/latest.json     the panel's pointer document (filled in with the asset ids after the upload)
"""
import base64
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLS = ["outlet", "group", "division", "category", "title", "price", "regular_price", "size", "unit_price", "price_basis",
        "brand", "retailer_id", "availability", "url", "photo_url", "collected", "notes"]


def small(url, px=64):
    from PIL import Image
    f = ROOT / "data/thumbs" / (hashlib.sha1(url.encode()).hexdigest() + ".jpg")
    if not url or not f.exists():
        return None
    im = Image.open(f).convert("RGB")
    im.thumbnail((px, px))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=62, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def main(cat_dir):
    cat_dir = Path(cat_dir)
    cfg = json.load(open(ROOT / "config/catalogue.json", encoding="utf-8"))
    rows = list(csv.DictReader(open(cat_dir / "catalog.csv", encoding="utf-8-sig")))
    date = cat_dir.name[:10]
    (cat_dir / "catalogue.json").write_text(json.dumps(dict(date=date, groups=cfg["groups"], cols=COLS,
                                                            rows=[[r.get(c, "") for c in COLS] for r in rows]),
                                                       ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    thumbs = {}
    for r in rows:
        u = r.get("photo_url")
        if u and u not in thumbs:
            b = small(u)
            if b:
                thumbs[u] = b
    (cat_dir / "thumbs.json").write_text(json.dumps(dict(date=date, thumbs=thumbs), separators=(",", ":")), encoding="utf-8")
    counts = {}
    for r in rows:
        counts[r["group"]] = counts.get(r["group"], 0) + 1
    stores = {}
    for r in rows:
        stores[r["outlet"]] = stores.get(r["outlet"], 0) + 1
    (cat_dir / "latest.json").write_text(json.dumps(dict(date=date, rows=len(rows), photos=len(thumbs), groups=cfg["groups"],
                                                         counts=counts, stores=stores), ensure_ascii=False), encoding="utf-8")
    for f in ("catalogue.json", "thumbs.json"):
        print(f, f"{(cat_dir / f).stat().st_size / 1e6:.1f} MB")
    print(f"{len(rows)} rows, {len(thumbs)} photos, groups {counts}")


if __name__ == "__main__":
    main(sys.argv[1])
