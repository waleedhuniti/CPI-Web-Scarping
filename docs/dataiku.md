# Getting the scraped prices into Dataiku

All three routes deliver the same table, one row per run x retailer x basket line, with fixed columns:

`run_date, run_id, source, retailer, item_code, group_code, name_ar, brand_ar, basket_qty, barcode, status, accepted,
title, price, regular_price, currency, in_stock, url`

`accepted = yes` rows are the prices that go into the index; the rest are the review queue (`status` says why).

## 1. Today, no setup: download from the panel

Panel (https://claude.ai/artifact/FSURninVx3TmNCeFYDyxUn), project CPI, tab **Results**, button
**Download all data (Dataiku)**: every saved run in one CSV. In Dataiku: *+ Dataset -> Upload your files*, then
*Add more files* for the next download, or a Stack recipe over the uploads.
Good for a monthly index. Manual: someone downloads and uploads.

## 2. From the repository (semi-automatic)

`python scripts/export_for_dataiku.py` writes `data/exports/cpi_prices_long.csv` from every run under `data/runs/`.
In Dataiku: *+ Dataset -> Network -> HTTP* (or *Download* visual recipe) pointing at the raw GitHub URL of that file,
with a GitHub token header if the repository stays private; a scenario rebuilds it daily after 08:30.
Needs the CSV to be committed after each run (a GitHub Actions job or the daily routine).

## 3. Recommended for production: run the scraper inside Dataiku

`dataiku/recipe_cpi_scrape.py` is a Python recipe that runs the same Scrapling search and matching and writes the
`cpi_prices` dataset directly. Steps for the Dataiku admin:

1. **Network**: the Dataiku server needs outbound HTTPS to `www.carrefouruae.com` and `gcc.luluhypermarket.com`
   (`tradingeconomics.com` for TrendX).
2. **Code environment** (Python 3.10+): `scrapling[fetchers]`, `openpyxl`, `pandas`. No browser is needed.
3. **Project library**: *Libraries -> Import from Git* this repository, so `cpi/` and `scripts/` are importable
   (add `scripts` to the Python path in the library's `external-libraries.json`).
4. **Output dataset** `cpi_prices` on a SQL connection, partitioned by day on `run_date` (or the recipe set to
   *Append instead of overwrite*), so every run adds rows and history is kept.
5. **Scenario**: time trigger daily 08:00 Asia/Dubai -> *Build cpi_prices*; add a reporter (mail) on failure.
6. Downstream: a filter recipe on `accepted = yes`, a join with the previous month's prices for the +/-30%
   plausibility check, and the index computation.

Then the claude.ai routine and the panel become optional (useful for edits and quick checks); Dataiku owns the
schedule, the history and the governance.

## Basket and actor changes

The basket lives in `data/basket/basket_source.xlsx` (and the panel's copy). If the basket is maintained in Dataiku,
export it as a dataset and have the recipe read it instead of the workbook (`cpi.basket.load_basket` -> a DataFrame
with the same columns).
