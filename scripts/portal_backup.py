"""Copy of the Scraping Projects panel (https://claude.ai/artifact/FSURninVx3TmNCeFYDyxUn) into the repository, from a download of
its database and assets, so the price history does not live only in the panel.

    python scripts/portal_backup.py <dump dir> [data/portal]

The dump dir is what ArtifactData list/get with out_dir writes (projects/..., system/..., system_bundle/...), plus:
  te_log/days/*.json                        the Commodity Price Log artifact (TrendX), collection "days"
  assets/<history_asset>.json               products history (projects/cpi/products latest)
  assets/<panel_asset>.csv                  product panel (same doc)
  assets/<rows_asset>.json                  catalogue (projects/cpi/catalogue latest)
  assets/<catalogue history_asset>.json     catalogue price history (same doc)

Writes into data/portal/:
  cpi/runs/<run id>/run.json, rows.csv      every daily CPI run: its summary and all its rows (the panel and Dataiku download columns)
  cpi/prices_all_runs.csv.gz                every row of every run in one file
  cpi/basket.json, cpi/pins.json            the basket as edited in the panel, the reference listings of the product-set lines
  cpi/products/history.json, product_panel.csv.gz, latest.json    the product-set price history (scripts/product_panel.py)
  cpi/catalogue/catalogue.json.gz, history.json.gz, latest.json   the latest catalogue and the catalogue price history
  projects/<id>.json                        the panel's project documents (last run, settings)
  te/days/<date>.json, te/commodity_prices.csv                    TrendX daily commodity prices
  system/<doc>.json, system_bundle_files.txt                      the code documents the routines read (the code itself is in git)
Files over 2 MB are gzipped. Re-running replaces the copy with the new download (runs are only ever added in the panel).
"""
import csv
import glob
import gzip
import json
import os
import shutil
import sys
from pathlib import Path


def data(path):
    d = json.load(open(path, encoding="utf-8"))
    return d.get("data", d) if isinstance(d, dict) and "data" in d and isinstance(d["data"], dict) else d


def dump_json(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, indent=1)
    if len(text.encode()) > 2_000_000:
        path = path.with_suffix(path.suffix + ".gz")
        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write(text)
    else:
        path.write_text(text, encoding="utf-8")
    return path


def write_rows(rows, path, gz=False):
    cols = []
    for r in rows:
        cols += [k for k in r if k not in cols]
    path.parent.mkdir(parents=True, exist_ok=True)
    f = gzip.open(path, "wt", encoding="utf-8", newline="") if gz else open(path, "w", encoding="utf-8", newline="")
    with f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def main():
    src = Path(sys.argv[1])
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "data/portal")
    if out.exists():
        shutil.rmtree(out)
    every = []
    for f in sorted(glob.glob(str(src / "projects/cpi/runs/*.json"))):
        rid = Path(f).stem
        rows = []
        for c in sorted(glob.glob(str(src / f"projects/cpi/runs/{rid}/rows/c*.json"))):
            rows += data(c)["rows"]
        dump_json(data(f), out / f"cpi/runs/{rid}/run.json")
        write_rows(rows, out / f"cpi/runs/{rid}/rows.csv")
        every += [dict(run_id=rid, **r) for r in rows]
        print(rid, len(rows), "rows")
    write_rows(every, out / "cpi/prices_all_runs.csv.gz", gz=True)
    items = []
    for f in sorted(glob.glob(str(src / "projects/cpi/basket/*.json"))):
        items += data(f)["items"]
    dump_json(items, out / "cpi/basket.json")
    if (src / "projects/cpi/pins/current.json").exists():
        dump_json(data(src / "projects/cpi/pins/current.json"), out / "cpi/pins.json")
    assets = src / "assets"
    for kind, keys in (("products", {"history_asset": "history.json", "panel_asset": "product_panel.csv"}),
                       ("catalogue", {"rows_asset": "catalogue.json", "history_asset": "history.json"})):
        p = src / f"projects/cpi/{kind}/latest.json"
        if not p.exists():
            continue
        doc = data(p)
        dump_json(doc, out / f"cpi/{kind}/latest.json")
        for key, name in keys.items():
            hit = glob.glob(str(assets / f"{doc.get(key, '-')}.*"))
            if not hit:
                print("missing asset", kind, key)
                continue
            dest = out / f"cpi/{kind}/{name}"
            if Path(hit[0]).stat().st_size > 2_000_000:
                with open(hit[0], "rb") as a, gzip.open(str(dest) + ".gz", "wb") as b:
                    shutil.copyfileobj(a, b)
            else:
                shutil.copy(hit[0], dest)
    for f in sorted(glob.glob(str(src / "projects/*.json"))):
        dump_json(data(f), out / f"projects/{Path(f).name}")
    te_rows = []
    for f in sorted(glob.glob(str(src / "te_log/days/*.json"))):
        d = data(f)
        dump_json(d, out / f"te/days/{Path(f).name}")
        rows = [dict(zip(d["cols"], r)) for r in d["rows"]] if "cols" in d else d.get("rows", [])
        te_rows += [dict(run_date=d.get("run_date", Path(f).stem), **r) for r in rows]
    if te_rows:
        write_rows(te_rows, out / "te/commodity_prices.csv")
    for f in sorted(glob.glob(str(src / "system/*.json"))):
        dump_json(data(f), out / f"system/{Path(f).name}")
    names = []
    for f in sorted(glob.glob(str(src / "system_bundle/*.json"))):
        names += sorted(data(f)["files"])
    if names:
        (out / "system").mkdir(parents=True, exist_ok=True)
        (out / "system/system_bundle_files.txt").write_text("\n".join(names) + "\n", encoding="utf-8")
    print(len(every), "run rows,", len(items), "basket lines,", len(te_rows), "commodity rows ->", out)


if __name__ == "__main__":
    main()
