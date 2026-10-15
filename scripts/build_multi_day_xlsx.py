"""One Excel workbook with the Dataiku rows of several days (data/exports/dataiku/CPI_basket_<date>_cpi_group.csv).

    python scripts/build_multi_day_xlsx.py out.xlsx 2026-10-12 2026-10-13 ...  [--rematch 2026-10-12=<category_matches.csv>]

--rematch re-fills the category (fresh food) rows of that day that were 'not_found' with the matches of the current rules
(scrapling_category.match on that day's saved catalog), unit price taken as the price of the line's unit.
"""
import csv
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent


def load(day):
    return list(csv.DictReader(open(ROOT / f"data/exports/dataiku/CPI_basket_{day}_cpi_group.csv", encoding="utf-8-sig")))


def rematch(rows, matches):
    new = {(m["item_code"], m["retailer"]): m for m in csv.DictReader(open(matches, encoding="utf-8-sig")) if m["status"] == "match"}
    n = 0
    for r in rows:
        m = new.get((r["item_code"], r["retailer"]))
        if r["source"] == "category" and r["status"] != "found" and m:
            price = m["price"] if m["price_basis"] == "pc" else m["unit_price"]
            r.update(status="found", accepted="yes", detail="spec_match", title=m["title"], price=price, url=m["url"],
                     unit_price=m["unit_price"], price_basis=m["price_basis"], n_products=m["n_candidates"],
                     note="re-matched with the current rules")
            n += 1
    return n


def main():
    out, args = sys.argv[1], sys.argv[2:]
    re_ = {}
    days = []
    i = 0
    while i < len(args):
        if args[i] == "--rematch":
            d, p = args[i + 1].split("=")
            re_[d] = p
            i += 2
        else:
            days.append(args[i])
            i += 1
    wb = openpyxl.Workbook()
    summary = wb.active
    summary.title = "Summary"
    summary.append(["date", "lines in basket", "lines priced", "% priced", "rows re-filled"])
    data = wb.create_sheet("Data")
    header = None
    for d in days:
        rows = load(d)
        added = rematch(rows, re_[d]) if d in re_ else 0
        header = header or list(rows[0].keys())
        if d == days[0]:
            data.append(header)
        for r in rows:
            data.append([float(r[c]) if c in ("price", "unit_price", "regular_price") and r.get(c) else r.get(c, "") for c in header])
        items = {r["item_code"] for r in rows}
        priced = {r["item_code"] for r in rows if r["price"] and float(r["price"]) > 0}
        summary.append([d, len(items), len(priced), round(100 * len(priced) / len(items), 1), added])
    data.freeze_panes = "A2"
    data.auto_filter.ref = data.dimensions
    wb.save(out)
    print(out)
    for row in summary.iter_rows(values_only=True):
        print(row)


if __name__ == "__main__":
    main()
