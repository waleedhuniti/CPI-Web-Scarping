"""Price history of the daily catalogue, stored as changes only (one small file that grows a little each day).

    python scripts/catalogue_history.py update <catalogue day dir> <previous history.json | -> <new history.json>
    python scripts/catalogue_history.py csv <history.json> <out.csv>      # change log: one row per price change

history.json: {"v":1, "days":[date,...], "skipped":{date:[outlet,...]},
               "p": {"<outlet>|<retailer id or url>": {"t":title,"o":outlet,"g":group,"c":category,"u":url,
                                                         "h":[[day index, price|null, regular price|null], ...]}}}
A new entry is added only when the price or the was-price changes; [day, null, null] means the product was not listed that
day. A store that came back with less than half of its usual products that day (a failed crawl) does not mark its
products as gone. Offers can later be found as price drops that come back (a sale filter over h).
"""
import csv
import json
import sys
from pathlib import Path


def num(v):
    try:
        return float(v) if v not in ("", None) else None
    except ValueError:
        return None


def key(r):
    return f"{r['outlet']}|{r.get('retailer_id') or r['url']}"


def update(cat_dir, prev, out):
    rows = list(csv.DictReader(open(Path(cat_dir) / "catalog.csv", encoding="utf-8-sig")))
    date = Path(cat_dir).name[:10]
    hist = json.load(open(prev, encoding="utf-8")) if prev not in ("-", "") and Path(prev).exists() else {"v": 1, "days": [], "skipped": {}, "p": {}}
    days, P = hist["days"], hist["p"]
    if date in days:                                   # same day run again: replace that day
        i = days.index(date)
        for p in P.values():
            p["h"] = [e for e in p["h"] if e[0] != i]
        days.pop(i)
        hist["skipped"].pop(date, None)
        for p in P.values():                           # later days (if any) keep their index; re-runs are normally the last day
            p["h"] = [[e[0] - 1 if e[0] > i else e[0], *e[1:]] for e in p["h"]]
    idx = len(days)
    days.append(date)
    today = {}
    for r in rows:
        if num(r["price"]):
            today[key(r)] = r
    for k, r in today.items():
        cur = [num(r["price"]), num(r.get("regular_price"))]
        p = P.get(k)
        if not p:
            p = P[k] = {"t": r["title"], "o": r["outlet"], "g": r["group"], "c": r["category"], "u": r["url"], "h": []}
        if not p["h"] or p["h"][-1][1:] != cur:
            p["h"].append([idx, *cur])
    # products that were listed before but are not today (only for stores whose crawl looks complete)
    live = {}
    for k, p in P.items():
        if p["h"] and p["h"][-1][1] is not None:
            live.setdefault(p["o"], set()).add(k)
    skipped = []
    for outlet, ks in live.items():
        if sum(1 for k in ks if k in today) < 0.5 * len(ks):
            skipped.append(outlet)
            continue
        for k in ks:
            if k not in today:
                P[k]["h"].append([idx, None, None])
    if skipped:
        hist["skipped"][date] = skipped
    json.dump(hist, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    changes = sum(1 for p in P.values() for e in p["h"] if e[0] == idx)
    print(f"{date}: day {idx + 1}, {len(today)} priced today, {changes} new history entries, {len(P)} products tracked"
          + (f", skipped (incomplete crawl): {skipped}" if skipped else "") + f" -> {out} ({Path(out).stat().st_size / 1e6:.2f} MB)")


def to_csv(history, out):
    h = json.load(open(history, encoding="utf-8"))
    cols = ["date", "outlet", "product_id", "title", "price", "regular_price", "group", "category", "url"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for k, p in h["p"].items():
            for d, price, reg in p["h"]:
                w.writerow([h["days"][d], p["o"], k.split("|", 1)[1], p["t"], price, reg, p["g"], p["c"], p["u"]])


if __name__ == "__main__":
    if sys.argv[1] == "update":
        update(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        to_csv(sys.argv[2], sys.argv[3])
