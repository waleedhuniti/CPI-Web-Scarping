# Dataiku Python recipe: scrape the CPI basket with Scrapling and append the result to a Dataiku dataset.
#
# Setup (once, see docs/dataiku.md):
#   - Code environment (Python 3.10+): scrapling[fetchers], openpyxl
#   - Project library: import this repository from Git (Libraries -> Import from Git), path "python" -> repo root,
#     so `cpi` and `scripts` can be imported
#   - Recipe output: dataset "cpi_prices" (SQL or filesystem), partitioned by day on "run_date" or appended
#   - Scenario: time trigger 08:00 Asia/Dubai, step "Build cpi_prices"
#
# The Dataiku server needs outbound HTTPS to www.carrefouruae.com and gcc.luluhypermarket.com.
import datetime as dt
import sys
import tempfile
from pathlib import Path

import dataiku
import pandas as pd

sys.argv = ["scrapling_search"]                       # the script parses argv; we call its pieces directly
import scrapling_search as ss                          # from the repo's scripts/ folder (project library)
import export_for_dataiku as ex

RETAILERS = ["carrefour", "lulu"]
LIMIT = 0                                              # >0 for a quick test run

run_date = dt.datetime.now(dt.timezone(dt.timedelta(hours=4))).date().isoformat()   # Dubai date
run_dir = Path(tempfile.mkdtemp()) / f"{run_date}_scrapling"

for retailer in RETAILERS:
    sys.argv = ["scrapling_search", retailer, str(run_dir)] + (["--limit", str(LIMIT)] if LIMIT else [])
    ss.main()                                          # writes <retailer>_matched.csv into run_dir

rows = []
for f in run_dir.glob("*_matched.csv"):
    df = pd.read_csv(f, dtype=str, encoding="utf-8-sig")
    df = df[df["status"] != "not_searched"]
    rows.append(pd.DataFrame({
        "run_date": run_date, "run_id": run_dir.name, "source": "scrapling", "retailer": f.stem.split("_")[0],
        "item_code": df["item_code"], "group_code": df["group"], "name_ar": df["name_ar"], "brand_ar": df["brand_ar"],
        "basket_qty": df["basket_qty"], "barcode": df["barcode"], "status": df["status"],
        "accepted": df["status"].isin(ex.ACCEPTED).map({True: "yes", False: "no"}), "title": df["title"],
        "price": pd.to_numeric(df["price"], errors="coerce"), "regular_price": pd.to_numeric(df["regular_price"], errors="coerce"),
        "currency": "AED", "in_stock": df["in_stock"], "url": df["url"]}))

out = pd.concat(rows, ignore_index=True)[ex.COLUMNS]
dataiku.Dataset("cpi_prices").write_with_schema(out)
print(len(out), "rows written for", run_date)
