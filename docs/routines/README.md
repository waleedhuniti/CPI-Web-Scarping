# Scheduled routines behind the Scraping Projects panel

The panel (https://claude.ai/artifact/FSURninVx3TmNCeFYDyxUn) is filled by three scheduled cloud tasks. Each run starts a fresh
session that reads its code from the panel's `system_bundle` documents (the files of this branch) and writes its results back
into the panel's database. A copy of that database, with the whole price history, is in `data/portal/` (`scripts/portal_backup.py`).

| Routine | Schedule (Dubai) | Prompt |
|---|---|---|
| Daily CPI scrape: barcode search, bulk categories, product set, catalogue fill | 06:47 | [cpi_daily_scrape.md](cpi_daily_scrape.md) |
| Daily catalogue crawl: all CPI divisions, six stores, catalogue price history | 06:52 | [catalogue_daily_crawl.md](catalogue_daily_crawl.md) |
| Daily TrendX commodity prices: Commodity Price Log artifact and the panel | 03:00 | below |
| The panel's own scrapers (Scrapling engine, collection `scrapers`): the ones with a "Run now" request | on demand only (started by the Run now button, no schedule) | [custom_scrapers.md](custom_scrapers.md) |

TrendX (`trig_01FWxfp4cQQtbe3CJxqw9EH4`): reads `collect_te.py`, `build_xlsx.py` and `to_panel.py` from the panel document
`system/te_daily` (copies in `panel_artifact/routines/`), captures the closing prices on tradingeconomics.com/commodities
(direct fetch, Apify web-fetch as fallback), stores the day in the Commodity Price Log artifact
(https://claude.ai/artifact/XuUGyJcKQEZntxSELCaELE, collection `days`) and as a `projects/te` run in the panel, and sends an
Excel file of the whole log.

When a script changes, the panel's `system_bundle` has to be updated too, or the routines keep running the old file.
