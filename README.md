# CPI Web Scraping

Collect online grocery prices for the UAE CPI food basket (COICOP 011), matching each scraped product to a basket
line **barcode first**, then name/description, with **quantity as a hard rule** (it must never change).

## How a price gets into the index (run 2026-10-05)

Every accepted price has to pass all of these; anything that fails one goes to `review_queue.csv` for the officer.

1. **Barcode first.** The basket barcode is searched on Carrefour and Lulu. A hit counts only if the search returned exactly one
   product and the pack size equals the basket size (`cpi/matcher.py`). Carrefour: 190 of 384 barcodes found, Lulu: 110.
2. **Second source: the retailer's own product page.** Every match is re-opened (`scripts/verify_pages.py`): the page price must
   be within 20% of the search price (a larger gap means the card links to another variant, e.g. Lulu's single bottle under a
   4-pack card), the page pack size must equal the basket size, and on Lulu the basket barcode must be printed on the page.
   Stock and price are taken from the page (the Carrefour actor's stock flag was wrong for 30 of 190 products).
3. **No barcode hit -> name + brand + size** (`scripts/name_search.py`). Queries written from the Arabic basket and checked by
   a second agent; 1,240 search pages crawled; each item x retailer judged against written rules (`docs/name_matching_rules.md`:
   brand, product, variant, exact size; fresh: kind, grade, per-kg price, origin), every accepted match challenged by a
   second agent (26 of 311 refuted), then the product page check of step 2, then an independent audit (177 of 183 passed;
   the rest went to review).
4. **Fresh produce, meat and fish** are compared per kg. A listing counts for the basket line of its **own** origin (read
   from the product page). Other origin lines are `substitute_origin`: under the office's rule they may take that price
   only when it is inside +/-30% of the line's own last price - that anchor is not available yet, so they wait for the
   officer (63 rows). Lines whose origin the site does not show go to review (35).

### Result of the 2026-10-05 run (`data/runs/2026-10-05/coverage.md`)

| | Items | Priced | by barcode | by name | fresh by spec |
|---|---:|---:|---:|---:|---:|
| All 637 basket items | 637 | **315** | 216 | 55 | 44 |

451 accepted retailer prices are in `prices.csv` (`use_in_index = yes`); 366 rows are in `review_queue.csv`. Nesto has no
online shop we could find; Spinneys needs a delivery address and a browser actor (not in this run).

## Portal (بوابة التشغيل)

A local web page to run the barcode scrape with one click, edit the basket and edit the Apify actors.

```bash
pip install -r requirements.txt
python portal/app.py          # open http://127.0.0.1:5000
```

| Tab | What it does |
|---|---|
| **تشغيل السكراب** | Pick retailers, COICOP groups or item codes, press *ابدأ السكراب*. Runs each retailer's Apify actor in batches, matches every listing against the basket (`cpi/matcher.py`) and writes `data/runs/<date>_<time>_portal/` (`results.csv`, `<retailer>_raw.jsonl`, `<retailer>_dataset.json`, `summary.json`). Previous runs can be opened, filtered and downloaded. |
| **السلة** | Search, edit, add and delete basket lines; GTIN, quantity and origin are re-derived on save (`data/basket/basket.json` + `.csv`). Upload a new workbook in the office's layout to replace the basket. |
| **الـ Actors** | Per retailer: actor id, mode (`barcodes` or `search_urls`), batch size, parallel runs, input JSON with placeholders (`"{barcodes}"`, `"{barcodes_json}"`, `"{barcodes_text}"`, `"{start_urls}"`, `"{urls}"`), and the parser for its dataset (`carrefour_actor`, `lulu_search_markdown`, `lulu_page_function`, or `generic` with a field map). Saved to `config/actors.json`. Also edits the Lulu page function. |
| **الإعدادات و GitHub** | Apify token (kept in `.env`, never committed) and a button that commits the basket, actor settings and portal runs and pushes the current branch. |

The portal searches basket lines that carry a barcode; the name / fresh-produce search stays in `scripts/name_search.py`.

## Layout

| Path | What |
|---|---|
| `data/basket/basket_source.xlsx` | The basket as supplied (637 priced items, Arabic) |
| `data/basket/basket.csv` / `.json` | Normalised basket: GTIN, parsed quantity, ISO origin, match mode (generated) |
| `data/basket/quality_report.md` | Data-quality findings from the basket (generated) |
| `cpi/gtin.py` | EAN/UPC validation; restores leading zeros Excel dropped |
| `cpi/quantity.py` | Parses `1 كغ`, `280غ`, `4*1لتر`, `30gx18`, `30بيضة`, `حزمة` ... into g / ml / pc |
| `cpi/origin.py` | 78 Arabic spellings of origin -> ISO country |
| `cpi/matcher.py` | Barcode -> quantity -> name matching of a scraped listing against a basket item |
| `cpi/pricing.py` | Unit price (AED/kg) and the "same price range" rule for substitute origins |
| `cpi/retailers/` | Lulu and Carrefour adapters: barcode search URL / actor input, parsers for what comes back |
| `config/retailers.json` | Scope: Lulu, Carrefour, Spinneys, Nesto - **Dubai only** - and each one's status |
| `docs/retailers.md` | What works per retailer, pilot findings, what Spinneys and Nesto need |
| `data/pilot/` | Live pilot results (10 basket barcodes at Carrefour and Lulu) |
| `actors/lulu_search/` | Page function for Apify's web-scraper (bulk Lulu barcode search) - written, not yet run |
| `scripts/match_run.py`, `scripts/ingest_lulu.py` | Barcode results -> matched CSV per retailer |
| `scripts/verify_pages.py` | Second-source check on the product page (price, stock, size, Lulu barcode, origin) |
| `scripts/name_search.py` | Name + brand + size search: URLs, candidates, judge batches, apply, finalize, audit |
| `scripts/build_price_table.py` | `prices.csv`, `coverage.md`, `review_queue.csv` for a run |
| `data/runs/<date>/` | Everything a run produced; `evidence/` keeps the crawled pages and the judges' verdicts |
| `docs/june_comparison.md` | June manual-vs-scraped comparison and the class-by-class recommendation |
| `portal/` | The web portal (Flask app + page); `config/actors.json` holds its actor settings |
| `tests/` | `python -m pytest` |

## Use

```bash
pip install -r requirements.txt
python scripts/build_basket.py        # rebuild basket.csv / basket.json / quality_report.md
python -m pytest
```

## Matching rules

1. **Barcode** (canonical 14-digit GTIN) must be equal. A changed product name never rejects a barcode match.
2. **Quantity** is converted to g / ml / pieces and must be equal (0.5% tolerance for rounding only). Different
   quantity with the same barcode is `qty_mismatch`, never accepted.
3. **No barcode** (fresh items, bread, loose goods - 253 of 637): name + brand + exact quantity; weak matches go to
   a review queue instead of being auto-accepted.
4. **Fresh items from another origin** (e.g. South Africa when the basket line is Egypt) count as the basket line
   only when the unit price is inside a band around the anchor price (`cpi/pricing.py`, default +/-30%, to be
   confirmed). 30 AED/kg against a 3 AED/kg anchor is rejected.

## Status

* 87 offline tests (`python -m pytest`).
* Run 2026-10-05 done for Carrefour and Lulu (Dubai delivery area for Carrefour; Lulu showed no area in cheap mode and an
  Abu Dhabi area in browser mode - prices were the same in the cases compared).
* Next: supply last month's price per basket line (the anchor for the +/-30% origin rule and for a month-on-month
  plausibility check), let an officer clear `review_queue.csv` once, then repeat monthly in one short collection window.
* Spinneys and Nesto: not covered (see `docs/retailers.md`).
