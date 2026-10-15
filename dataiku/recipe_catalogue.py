# Dataiku Python recipe: collect the all-divisions product catalogue with Scrapling and write it straight into a
# Dataiku dataset (no file download / upload).
#
# Setup (once, see docs/dataiku.md):
#   - Code environment (Python 3.10+): scrapling[fetchers], pandas  (+ run `scrapling install` once if you also want
#     Centrepoint / Max, which need a browser to pass Cloudflare)
#   - Project library: import this repository from Git so `scripts` and `config` are importable
#   - Output dataset "cpi_catalogue" (SQL or filesystem), "append instead of overwrite", or partitioned by day
#   - Scenario: time trigger 08:00 Asia/Dubai -> build cpi_catalogue
#
# The Dataiku server needs outbound HTTPS to carrefouruae.com, luluhypermarket.com, sharafdg.com / algolia.net and
# zara.com (and centrepointstores.com / maxfashion.com when those stores are on).
import datetime as dt
import sys
import tempfile
from pathlib import Path

import dataiku
import pandas as pd

import catalogue_crawl as cc                           # scripts/catalogue_crawl.py (project library)

STORES = ["carrefour", "lulu", "sharafdg", "zara"]     # add "centrepoint", "max" once `scrapling install` was run
GROUPS = None                                          # e.g. ["electronics", "clothing"] to collect only some groups

run_date = dt.datetime.now(dt.timezone(dt.timedelta(hours=4))).date().isoformat()   # Dubai date
out_dir = Path(tempfile.mkdtemp()) / run_date

cc.main(out_dir, only=STORES, part_only=False)         # writes <out_dir>/catalog.csv
df = pd.read_csv(out_dir / "catalog.csv", dtype=str, encoding="utf-8-sig")
if GROUPS:
    df = df[df["group"].isin(GROUPS)]

for c in ("price", "regular_price", "unit_price"):
    df[c] = pd.to_numeric(df[c], errors="coerce")
df.insert(0, "run_date", run_date)

dataiku.Dataset("cpi_catalogue").write_with_schema(df)
print(len(df), "products written for", run_date, df.groupby("group").size().to_dict())
