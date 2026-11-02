"""Product panel for the basket lines that have no barcode (meat, fish, fruit, vegetables, deli, bakery ...).

    python scripts/product_panel.py update <history.json | -> <catalog.csv> <date> <new history.json>
    python scripts/product_panel.py series <history.json> <out dir>

Method (matched-model, chained - how price statisticians handle products that come and go):
  * Every product of the day's crawl (data/runs/<day>/catalog.csv) that fits a basket line - product words, none of the
    excluded words, right section, price convertible to the line's unit - belongs to that line. ORIGIN AND BRAND DO NOT
    MATTER: 'mortadella' is every mortadella in the shop, not only the Jordanian one.
  * Each product is tracked on its own, every day, by its shop id: the history keeps its unit price (AED per kg / piece /
    bunch) as a change log (a day is added only when the price changed, [day, null] when the product is not listed).
  * A line's price change from one day to the next is the geometric mean of the price changes of the products listed on both
    days (Jevons). A product going out of stock, or a new one appearing, adds no jump: the mortadella that costs 10 today and
    is replaced by one that costs 18 tomorrow does not make the line rise 80%. The index is chained from day to day.
  * The line's price level is the first day's median unit price moved by that index (a constant-quality price), per shop.
A day whose crawl of a shop came back mostly empty (update() records it under "skipped") gives that shop's lines no price that day
(observed = no, price empty): the last price is not carried forward as if it had been seen.
Outputs of `series`: line_prices.csv (one row per line, shop and day: price, index, number of products and pairs, observed) and
product_panel.csv (every product of every line and day, for the Dataiku team to recompute with their own method).
"""
import csv
import json
import math
import re
import statistics
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import scrapling_category as sc  # noqa: E402

SHOPS = ("carrefour", "lulu")


def product_id(row):
    m = re.search(r"/p/([^/?]+)", row["url"])
    return f"{row['retailer']}|{m.group(1).strip('/') if m else row['url']}"


def section_groups():
    """(shop, section name) -> the CPI groups that section feeds (config/categories.json): a raisin line looks in nuts and
    dried fruit, not in breakfast cereals that mention raisins."""
    cfg = json.load(open(sc.CONFIG, encoding="utf-8"))
    return {(r, c["name"]): set(str(c["group"]).split(",")) for r in SHOPS for c in cfg[r]}


SECTIONS = section_groups()


def lines():
    from cpi.basket import load_basket_any
    specs = {x["c"]: x for x in json.load(open(sc.SPECS, encoding="utf-8"))}
    raw = {b["item_code"]: b for b in json.load(open(ROOT / "data/basket/basket.json", encoding="utf-8"))}
    out = []
    for it in (asdict(i) for i in load_basket_any(ROOT)):
        if it["match_mode"] != "spec" or raw.get(it["item_code"], {}).get("match_mode", "spec") != "spec":
            continue
        if it["group_code"] not in ("0111", "0112", "0113", "0114", "0115", "0116", "0117", "0118", "0119"):
            continue
        want, base_ok = sc.make_filter(it, specs.get(it["item_code"], {}))
        gcode = it["group_code"]

        def ok(row, base_ok=base_ok, gcode=gcode):
            return gcode in SECTIONS.get((row["retailer"], row["category"]), {gcode}) and base_ok(row)
        out.append((it, want, ok))
    return out


MAX_UNIT_PRICE = 600.0       # AED per kg / litre: above this a fresh-food listing is a whole animal, a hamper or a parse error (a lamb carcass priced 1,619 'per kg')


def plausible(r):
    try:
        up = float(r["unit_price"])
    except ValueError:
        return False
    return 0 < up <= MAX_UNIT_PRICE or str(r.get("group", "")).split(",")[0] in ("0119", "0118")     # spices, saffron, chocolates can be dear


def update(hist_in, catalog_csv, date, hist_out):
    hist = json.load(open(hist_in, encoding="utf-8")) if hist_in not in ("-", "") and Path(hist_in).exists() else {"v": 1, "days": [], "skipped": {}, "p": {}}
    days, P = hist["days"], hist["p"]
    if date in days:                                   # the same day again: replace it
        i = days.index(date)
        for p in P.values():
            p["h"] = [e for e in p["h"] if e[0] != i]
        days.pop(i)
    idx = len(days)
    days.append(date)
    rows = [r for r in csv.DictReader(open(catalog_csv, encoding="utf-8-sig")) if r["retailer"] in SHOPS and r.get("unit_price") and plausible(r)]
    fits = lines()
    today = {}
    for r in rows:
        k = product_id(r)
        if k in P or any(ok(r) for _, _, ok in fits):
            today[k] = r
    for k, r in today.items():
        p = P.setdefault(k, {"r": r["retailer"], "t": r["title"], "c": r["category"], "b": r["price_basis"], "u": r["url"], "h": []})
        p["f"] = r.get("photo_url") or p.get("f", "")
        cur = [float(r["unit_price"]), float(r["price"])]
        if not p["h"] or p["h"][-1][1:] != cur:
            p["h"].append([idx, *cur])
    live = {}
    for k, p in P.items():
        if p["h"] and p["h"][-1][1] is not None:
            live.setdefault(p["r"], set()).add(k)
    skipped = []
    for shop, ks in live.items():
        if sum(1 for k in ks if k in today) < 0.5 * len(ks):       # a crawl that came back mostly empty is not a market change
            skipped.append(shop)
            continue
        for k in ks:
            if k not in today:
                P[k]["h"].append([idx, None, None])
    if skipped:
        hist["skipped"][date] = skipped
    json.dump(hist, open(hist_out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{date}: day {idx + 1}, {len(today)} products today, {len(P)} tracked" + (f", incomplete crawl, no absences for {skipped}" if skipped else "")
          + f" -> {hist_out} ({Path(hist_out).stat().st_size / 1e6:.2f} MB)")


def price_on(p, day):
    """Unit price of product p on day index `day` (None if not listed)."""
    last = None
    for d, up, _ in p["h"]:
        if d > day:
            break
        last = up
    return last


def series(hist_path, out_dir):
    hist = json.load(open(hist_path, encoding="utf-8"))
    days, P = hist["days"], hist["p"]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows, panel = [], []
    covered = {}
    skipped = hist.get("skipped", {})                  # day -> shops whose crawl came back mostly empty (see update())
    raw = {b["item_code"]: b for b in json.load(open(ROOT / "data/basket/basket.json", encoding="utf-8"))}
    grp = lambda ic: re.sub(r"^\d+\s*-\s*", "", str(raw.get(ic, {}).get("group_name", ""))).strip()
    for it, want, ok in lines():
        for shop in SHOPS:
            prods = [(k, p) for k, p in P.items() if p["r"] == shop and ok({"retailer": shop, "title": p["t"], "category": p["c"], "price_basis": p["b"], "unit_price": "1"})]
            if not prods:
                continue
            idx, base, prev = 100.0, None, None
            for d, day in enumerate(days):
                if shop in skipped.get(day, []):        # nothing seen in that shop that day: the line has no price (not the last one
                    if base is not None:               # carried forward); the chain goes on from the last day it was seen
                        rows.append(dict(date=day, item_code=it["item_code"], cpi_group=grp(it["item_code"]), retailer=shop, unit=want,
                                         price="", index="", n_products=0, n_pairs=0, cheapest="", dearest="", rep_title="", rep_url="",
                                         rep_photo="", rep_unit_price="", observed="no"))
                    continue
                cur = {k: price_on(p, d) for k, p in prods}
                cur = {k: v for k, v in cur.items() if v}
                if not cur:
                    prev = None
                    continue
                pairs = 0
                if prev:
                    ls = [math.log(cur[k] / prev[k]) for k in cur if k in prev]
                    pairs = len(ls)
                    if ls:
                        idx *= math.exp(sum(ls) / len(ls))
                if base is None:
                    base = statistics.median(cur.values())
                med = statistics.median(cur.values())
                rep_k = min(cur, key=lambda k: abs(cur[k] - med))             # the listing nearest the median stands for the line (title, link, photo)
                rows.append(dict(date=day, item_code=it["item_code"], cpi_group=grp(it["item_code"]), retailer=shop, unit=want, price=round(base * idx / 100, 2),
                                 index=round(idx, 3), n_products=len(cur), n_pairs=pairs, cheapest=round(min(cur.values()), 2),
                                 dearest=round(max(cur.values()), 2), rep_title=P[rep_k]["t"], rep_url=P[rep_k]["u"],
                                 rep_photo=P[rep_k].get("f", ""), rep_unit_price=round(cur[rep_k], 2), observed="yes"))
                for k, v in cur.items():
                    panel.append(dict(date=day, item_code=it["item_code"], cpi_group=grp(it["item_code"]), retailer=shop, product_id=k.split("|", 1)[1],
                                      title=P[k]["t"], unit_price=v, price_basis=want, url=P[k]["u"]))
                prev = cur
            covered.setdefault(it["item_code"], set()).add(shop)
    for name, data in (("line_prices.csv", rows), ("product_panel.csv", panel)):
        if data:
            with open(out_dir / name, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(data[0]))
                w.writeheader()
                w.writerows(data)
    n = len(lines())
    print(f"{n} lines; with at least one product on some day: {len(covered)}; in both shops: {sum(len(v) == 2 for v in covered.values())}; "
          f"{len(rows)} line-days, {len(panel)} product-days -> {out_dir}")
    return rows, covered


if __name__ == "__main__":
    if sys.argv[1] == "update":
        update(*sys.argv[2:6])
    else:
        series(*sys.argv[2:4])
