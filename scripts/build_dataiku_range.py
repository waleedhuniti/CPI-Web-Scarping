"""One Dataiku workbook (and CSV) of the basket prices for a range of days: the days already delivered are taken as delivered
(their workbook's Data sheet), the later days are rebuilt from the portal's saved runs (rows documents downloaded with
ArtifactData into <db dir>/projects/cpi/runs/<run id>/rows/c*.json), through export_basket_csv.build like every daily file.

    python scripts/build_dataiku_range.py <earlier workbook.xlsx> <db dir> <out.xlsx> [first day YYYY-MM-DD] [last day]

One run per day (the latest that day). Same columns as the earlier workbook (new ones appended), plus a Summary sheet.
"""
import csv
import glob
import json
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_basket_csv  # noqa: E402

NUM = ("price", "unit_price", "regular_price", "price_spec")


def earlier(path):
    ws = openpyxl.load_workbook(path, read_only=True)["Data"]
    it = ws.iter_rows(values_only=True)
    head = list(next(it))
    return head, [dict(zip(head, r)) for r in it]


def portal_days(db, done, first, last):
    runs = {}
    for f in sorted(glob.glob(str(Path(db) / "projects/cpi/runs/*.json"))):
        d = json.load(open(f, encoding="utf-8")); d = d.get("data", d)
        day = str(d.get("startedAt", ""))[:10]
        if day in done or (first and day < first) or (last and day > last):
            continue
        rid = Path(f).stem
        if not glob.glob(str(Path(db) / f"projects/cpi/runs/{rid}/rows/c*.json")):
            continue
        if day not in runs or rid > runs[day]:
            runs[day] = rid
    return dict(sorted(runs.items()))


def main():
    prev, db, out = sys.argv[1:4]
    first = sys.argv[4] if len(sys.argv) > 4 else ""
    last = sys.argv[5] if len(sys.argv) > 5 else ""
    head, rows = earlier(prev)
    days = sorted({str(r["run_date"]) for r in rows})
    by_day = {d: [r for r in rows if str(r["run_date"]) == d] for d in days}
    for day, rid in portal_days(db, set(days), first, last).items():
        rr = []
        for f in sorted(glob.glob(str(Path(db) / f"projects/cpi/runs/{rid}/rows/c*.json"))):
            d = json.load(open(f, encoding="utf-8")); rr += d.get("data", d)["rows"]
        for r in rr:
            r["run_date"] = day                        # the run's Dubai day (rows of older runs may lack it)
        dest = export_basket_csv.build(rr, rid)
        by_day[day] = list(csv.DictReader(open(dest, encoding="utf-8")))
    cols = head + sorted({k for v in by_day.values() for r in v for k in r} - set(head))
    wb = openpyxl.Workbook()
    summary = wb.active; summary.title = "Summary"
    summary.append(["date", "run_id", "lines in basket", "lines priced", "% priced", "rows"])
    data = wb.create_sheet("Data"); data.append(cols)
    flat = []
    for day in sorted(by_day):
        for r in by_day[day]:
            vals = []
            for c in cols:
                v = r.get(c, "")
                if c in NUM and v not in (None, ""):
                    try: v = float(v)
                    except ValueError: pass
                vals.append(None if v == "" else v)
            data.append(vals); flat.append(vals)
        items = {r["item_code"] for r in by_day[day]}
        priced = {r["item_code"] for r in by_day[day] if r.get("price") not in (None, "") and float(r["price"] or 0) > 0}
        summary.append([day, by_day[day][0].get("run_id"), len(items), len(priced), round(100 * len(priced) / len(items), 1), len(by_day[day])])
    data.freeze_panes = "A2"; data.auto_filter.ref = data.dimensions
    wb.save(out)
    with open(Path(out).with_suffix(".csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(cols); w.writerows([["" if v is None else v for v in r] for r in flat])
    print(out, len(flat), "rows")
    for row in summary.iter_rows(values_only=True):
        print(row)


if __name__ == "__main__":
    main()
