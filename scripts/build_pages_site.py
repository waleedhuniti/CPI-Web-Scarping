"""Data files of the public price site (site/, served by GitHub Pages): one day's shop prices and the TrendX commodities.

    python scripts/build_pages_site.py <catalogue.json of the day> <TrendX days dir> [site/data]

Public data only: the shops' own listings (store, product name, price, price per unit, link, picture) and the commodity
closing prices. Nothing of the official CPI basket (item codes, groups, weights, official prices) goes into the site.

catalogue.json is the panel's catalogue asset (scripts/catalogue_assets.py); the TrendX days dir holds one
<date>.json per day as the Commodity Price Log stores them (data/portal/te/days). The commodity index is a chained
Jevons index (geometric mean of the price relatives of the commodities quoted on both days, equal weights), first day = 100,
over every commodity except the published indices.
"""
import glob
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

CAT_KEYS = {"outlet": "s", "group": "g", "category": "c", "title": "t", "price": "p", "regular_price": "r", "size": "z",
            "unit_price": "u", "price_basis": "b", "availability": "a", "url": "l", "photo_url": "f"}


def num(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def catalogue(path):
    d = json.load(open(path, encoding="utf-8"))
    rows = []
    for r in d["rows"]:
        x = dict(zip(d["cols"], r))
        if not num(x.get("price")):
            continue
        row = {k: x.get(c, "") for c, k in CAT_KEYS.items()}
        for k in ("p", "r", "u"):
            row[k] = num(row[k])
        rows.append({k: v for k, v in row.items() if v not in ("", None)})
    return {"date": d["date"], "groups": d["groups"], "rows": rows}


def day_rows(path):
    d = json.load(open(path, encoding="utf-8"))
    d = d.get("data", d)
    rows = [dict(zip(d["cols"], r)) for r in d["rows"]] if "cols" in d else d.get("rows", [])
    return d.get("run_date", Path(path).stem), rows


def trendx(days_dir):
    days = dict(day_rows(f) for f in sorted(glob.glob(str(Path(days_dir) / "*.json"))))
    dates = sorted(days)
    price = defaultdict(dict)                         # (category, commodity) -> date -> price
    for day, rows in days.items():
        for r in rows:
            p = num(r.get("price"))
            if p and p > 0 and r.get("category") != "Index":
                price[(r["category"], r["commodity"])][day] = p
    cats = sorted({c for c, _ in price})
    series = {c: [] for c in ["all"] + cats}
    level = {c: 100.0 for c in series}
    for i, day in enumerate(dates):
        if i:
            prev = dates[i - 1]
            for c in series:
                rel = [math.log(v[day] / v[prev]) for (cc, _), v in price.items()
                       if (c == "all" or cc == c) and day in v and prev in v]
                if rel:
                    level[c] *= math.exp(sum(rel) / len(rel))
        for c in series:
            series[c].append(round(level[c], 2))
    today = dates[-1]
    keep = ("category", "commodity", "unit", "price", "change", "pct", "weekly", "monthly", "ytd", "yoy", "price_date")
    return {"date": today, "first": dates[0], "dates": dates, "index": series,
            "counts": {c: sum(1 for (cc, _), v in price.items() if cc == c and today in v) for c in cats},
            "rows": [{k: r.get(k) for k in keep} for r in days[today]]}


def main(cat_path, days_dir, out="site/data"):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cat = catalogue(cat_path)
    (out / "catalogue.json").write_text(json.dumps(cat, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tx = trendx(days_dir)
    (out / "trendx.json").write_text(json.dumps(tx, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"catalogue {cat['date']}: {len(cat['rows'])} priced products; trendx {tx['first']}..{tx['date']}: "
          f"{len(tx['rows'])} series, index {tx['index']['all'][-1]} -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
