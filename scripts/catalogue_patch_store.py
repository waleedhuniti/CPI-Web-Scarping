"""Replace one store's rows in the panel's catalogue of a day with a crawl made elsewhere (when the catalogue routine was blocked
by that store), keeping every other store as the routine left it.

    python scripts/catalogue_patch_store.py build <panel catalogue.json> <part_<store>.csv> <day dir, e.g. .../2026-11-02>
    python scripts/fetch_thumbs.py <dir holding the part as catalog.csv>      # pictures of the new rows only
    python scripts/catalogue_assets.py <day dir>
    python scripts/catalogue_patch_store.py thumbs <day dir> <panel thumbs_<group>.json ...>
    python scripts/catalogue_history.py update <day dir> <panel history.json> <day dir>/history.json   (replaces that day)

build: <day dir>/catalog.csv = the panel catalogue without the part's store + the part's rows.
thumbs: catalogue_assets.py only embeds pictures found in the local data/thumbs cache, so the other stores' pictures are
taken back from the panel's thumbs files (only for photo links still in the catalogue); latest.json gets the new count.
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue_crawl import FIELDS  # noqa: E402


def store_of(outlet):
    o = outlet.lower()
    return "centrepoint" if "(centrepoint)" in o else o.replace(" ", "")


def build(panel_json, part_csv, day_dir):
    day_dir = Path(day_dir)
    day_dir.mkdir(parents=True, exist_ok=True)
    cat = json.load(open(panel_json, encoding="utf-8"))
    part = list(csv.DictReader(open(part_csv, encoding="utf-8-sig")))
    stores = {r.get("store") or store_of(r["outlet"]) for r in part}
    old = [dict(zip(cat["cols"], r)) for r in cat["rows"]]
    keep = [dict(r, store=store_of(r["outlet"])) for r in old if store_of(r["outlet"]) not in stores]
    rows = keep + part
    with open(day_dir / "catalog.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"{len(old) - len(keep)} old rows of {sorted(stores)} replaced by {len(part)}; {len(rows)} rows -> {day_dir / 'catalog.csv'}")


def thumbs(day_dir, panel_files):
    day_dir = Path(day_dir)
    rows = list(csv.DictReader(open(day_dir / "catalog.csv", encoding="utf-8-sig")))
    want = {}
    for r in rows:
        if r.get("photo_url"):
            want.setdefault(r["group"], set()).add(r["photo_url"])
    old = {}
    for f in panel_files:
        old.update(json.load(open(f, encoding="utf-8"))["thumbs"])
    total, added = 0, 0
    for g, urls in want.items():
        p = day_dir / f"thumbs_{g}.json"
        d = json.load(open(p, encoding="utf-8")) if p.exists() else {"date": day_dir.name[:10], "thumbs": {}}
        for u in urls:
            if u not in d["thumbs"] and u in old:
                d["thumbs"][u] = old[u]
                added += 1
        p.write_text(json.dumps(d, separators=(",", ":")), encoding="utf-8")
        total += len(d["thumbs"])
    latest = json.load(open(day_dir / "latest.json", encoding="utf-8"))
    latest["photos"] = total
    (day_dir / "latest.json").write_text(json.dumps(latest, ensure_ascii=False), encoding="utf-8")
    print(f"{added} pictures taken back from the panel; {total} pictures for {len(rows)} rows")


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build(*sys.argv[2:5])
    else:
        thumbs(sys.argv[2], sys.argv[3:])
