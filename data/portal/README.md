# Copy of the Scraping Projects panel (2 Nov 2026)

Made with `python scripts/portal_backup.py <download> data/portal` from the panel's database and assets
(https://claude.ai/artifact/FSURninVx3TmNCeFYDyxUn) and the Commodity Price Log (TrendX). See the script for how to download.

- `cpi/runs/<run id>/rows.csv`: every daily CPI run, all rows (same columns as the panel's Dataiku download); `run.json` its summary.
  Runs 12 Oct - 2 Nov 2026 (no run on 25 Oct). Carrefour was blocked from 30 Oct: its barcode rows are errors, and its
  no-barcode "found" prices of 30 Oct - 2 Nov are the last prices carried forward, not prices seen that day (fixed from 3 Nov).
- `cpi/prices_all_runs.csv.gz`: all runs in one file (`run_id` first).
- `cpi/basket.json` (1,301 lines as edited in the panel), `cpi/pins.json` (reference listings of the product-set lines).
- `cpi/products/`: product-set price history (`history.json`, `scripts/product_panel.py`) and `product_panel.csv.gz`.
- `cpi/catalogue/`: the latest catalogue (`catalogue.json.gz`, 3 Nov, Carrefour re-crawled by hand: 5,833 products) and the catalogue price history (`history.json.gz`).
- `te/`: TrendX commodity prices per day and `commodity_prices.csv` (2 Oct - 2 Nov).
- `projects/`, `system/`: the panel's project and code documents. The code itself is the repository; `system_bundle_files.txt`
  lists the files the routines load.
