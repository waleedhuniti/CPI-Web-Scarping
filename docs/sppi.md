# SPPI H & J - price collection with Scrapling

Collects published prices for the products/services of the SPPI sample (ISIC Rev.4 sections H and J) and says, for
every product, whether its price can be had by **Scraping**, **Online فقط** or **لا هذا ولا ذاك**.

## Nothing about the sample is in this repository

The sample (companies, products, serials, ISIC codes), the page configuration that links prices to products, the
availability reasons and every run output live in **`data/sppi/`**, which is git-ignored:

```
data/sppi/
  sample/companies.csv, products.csv     <- scripts/sppi_import_products.py <sample workbook>.xlsx
  config/sppi_pages.json                 <- price pages and the rules that link their prices to product_ids
  config/sppi_status.json                <- 'Online فقط' / 'لا هذا ولا ذاك' reasons for products without a price
  config/sppi_image_transcriptions.json  <- readings of image rate cards (sha256-locked)
  runs/<date>/                           <- outputs (CSV, workbook, snapshots)
```

Keep that folder on the officer's machine / the DDA share. Do not add it to git.

## Use

```bash
pip install -r requirements.txt
python scripts/sppi_import_products.py <sample workbook>.xlsx   # -> data/sppi/sample/
python scripts/sppi_run.py                                     # -> data/sppi/runs/<today>/
python scripts/sppi_run.py --only <ser or page id>,... --out /tmp/try
python -m pytest tests/test_sppi.py
```

Optional: `tesseract-ocr` (cross-check of image rate cards) and a Chromium for pages set to `"fetch": "browser"`
(`scrapling install`, or point `SPPI_CHROMIUM` at one).

## Every output row carries the sample codes

`ser` (الرقم المتسلسل), `section` (H / J), `isic_registered` (رمز النشاط المسجّل), `type` (منتج / خدمة), `product`,
`isic_product` (رمز ISIC الفعلي للبند) and `product_id` (ser + row number in the products sheet).

## Availability - `إمكانية الحصول على السعر`

On every product (sheet `المنتجات`), page (`ملخص الصفحات`) and request (`سجل الجلب`):

| Value | Meaning |
|---|---|
| **Scraping** | collected automatically in this run, with URL, HTTP status, time and a stored snapshot |
| **Online فقط** | a person can see the price, but it cannot be collected automatically (robots.txt forbids it, a bot wall, a booking / sign-up step, an in-app price). `تم التحقق` = yes if the price was actually seen, no if it still needs a manual check |
| **لا هذا ولا ذاك** | no public price (quote / contract, B2B, no website); the reason is in `السبب / الملاحظة` |

## How it works

1. `sppi_pages.json` lists price pages; each has `map` rules (regex on the item text -> `product_id`, or `+Name` for a
   priced service that is not in the product list). Every source URL of the products sheet is also probed, so each
   company has at least one logged request.
2. Parsers: `rta`, `megayachts`, `ups` (tariff PDF: rate tables + additional fees), `oracle` (price-list API in AED),
   `pinas` (image rate cards), `tables` (HTML price matrices) and `generic`, which finds the smallest element that
   prints an amount and keeps its heading, card title, list labels ('Friday'), table row/column and the text after it
   ('/Month 5% VAT Excluded'). Banners repeated on most pages of a site are dropped.
3. Rules: robots.txt first; at least 2 s between requests to a host; no challenge solving, no login; every fetched
   page / PDF / JSON / image is stored gzipped in `snapshots/` with its sha256.

## Output files (`data/sppi/runs/<date>/`)

| File / sheet | What |
|---|---|
| `products_availability.csv` / `المنتجات` | one row per product: codes, availability, verified, number of prices, price range, reason |
| `prices.csv` / `الأسعار` | one row per price x product: codes, item, price, currency, unit, price text, URL, HTTP status, time, method, snapshot, sha256 |
| `pages.csv` / `ملخص الصفحات` | one row per page: outcome, robots, counts, notes |
| `fetch_log.csv` / `سجل الجلب` | every request with `إمكانية الحصول على السعر` |
| `price_mentions.csv` / `إشارات الأسعار` | amounts on probed pages (evidence, not index prices) |
| `SPPI_HJ_prices_<date>.xlsx` | all of the above + methodology; RTL, Arial, header `#283593` |

## Adding or fixing a page

Add it to `data/sppi/config/sppi_pages.json` (`parser: generic` first), run it with `--only <page id> --out /tmp/try`,
read `prices.csv`, then tighten with `keep` (regex on item | spec | price text) / `drop` (regex on item | spec) and
`map` rules.
