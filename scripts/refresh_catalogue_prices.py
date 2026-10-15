"""Re-read today's price of every catalogue-filled row from its product page (Carrefour, Lulu, Sharaf DG)
and rescale the stored (unit) price by live / catalogue pack price.

    python scripts/refresh_catalogue_prices.py <dataiku csv> <catalogue.json the rows came from>
"""
import csv
import json
import random
import re
import sys
import time

from scrapling.fetchers import FetcherSession


def live_price(s, url):
    p = s.get(url)
    h = p.body.decode("utf-8", "ignore") if isinstance(p.body, bytes) else str(p.body)
    if p.status != 200:
        return None
    m = re.search(r'"price"\s*:\s*"?([\d.]+)', h)
    return float(m.group(1)) if m else None


def main(csv_path, cat_path):
    d = json.load(open(cat_path, encoding="utf-8"))
    cols = d["cols"]
    old = {r[cols.index("url")]: float(r[cols.index("price")] or 0) for r in d["rows"]}
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
    fields = list(rows[0].keys())
    done = same = failed = 0
    cache = {}
    with FetcherSession(impersonate="chrome", timeout=30, retries=2) as s:
        for r in rows:
            if r["source"] != "catalogue" or r["retailer"] == "zara" or not r["price"]:
                continue
            u = r["url"]
            if u not in cache:
                try:
                    cache[u] = live_price(s, u)
                except Exception:
                    cache[u] = None
                time.sleep(0.7 + random.random() / 2)
            new, was = cache[u], old.get(u)
            if not new or not was:
                failed += 1
                continue
            k = new / was
            for c in ("price", "unit_price", "regular_price"):
                if r.get(c):
                    try:
                        r[c] = round(float(r[c]) * k, 2)
                    except ValueError:
                        pass
            if abs(k - 1) > 0.001:
                done += 1
            else:
                same += 1
            r["note"] = (r["note"] + " · price re-read from the product page today").strip(" ·")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"changed {done}, unchanged {same}, not readable {failed}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
