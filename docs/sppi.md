# SPPI H & J - price collection with Scrapling

Prices for the Services Producer Price Index (ISIC Rev.4 sections H and J) from the public sites of the sampled
companies. `ser` (h196, j2, n4433 ...) is the join key with `SPPI_HJ_Red_Companies.xlsx` and
`SPPI_Scraping_Feasibility.xlsx`.

```bash
pip install -r requirements.txt
python scripts/sppi_run.py                        # all sources -> data/sppi/runs/<today>/
python scripts/sppi_run.py --only rta_nol,ups_tariff --date 2026-10-29-test   # --only rewrites that folder's tables
python -m pytest tests/test_sppi.py
```

Optional: `tesseract-ocr` (OCR cross-check of image rate cards) and, only for sources set to `"fetch": "browser"`, a
Chromium for Scrapling (`scrapling install`, or point `SPPI_CHROMIUM` at one). No current source needs the browser.

## Rules the collector follows

1. **robots.txt first** (protego, Google rules): 2xx -> obeyed; 4xx -> no rules; 5xx or unreachable -> not fetched.
   Checked again on every host a redirect leads to.
2. **One request per host every 2 s** (or the robots `Crawl-delay` if larger).
3. **No bypassing.** A Cloudflare/CAPTCHA page is logged as `blocked_bot_protection`. `solve_cloudflare` is never
   switched on; `StealthyFetcher` is only used to render JavaScript.
4. **Evidence for every value**: the fetched page/PDF/JSON/image is kept gzipped in `snapshots/` with its sha256;
   each price row carries the URL, HTTP status, fetch time (UTC) and the price string as printed.
5. **No guessing**: a UPS row with the wrong number of zone values is reported, not filled; a taxi time band that
   overlaps the previous one is recorded as published with a note; an image rate card is used only while the image
   is byte-identical to the one that was read.

## Output (`data/sppi/runs/<date>/`)

| File | What |
|---|---|
| `prices.csv` | One row per price: `ser, company, item, spec, price, currency, unit, price_type, vat, effective_date, price_text, source_url, fetched_at, http_status, status, snapshot, sha256, note` |
| `sources.csv` | One row per source: outcome (`ok`, `robots_disallowed`, `blocked_bot_protection`, `parsed_zero`, ...), robots state, counts, notes |
| `price_mentions.csv` | Every money amount on pages without a dedicated parser (feasibility evidence, **not** index prices) |
| `fetch_log.csv` | Every HTTP request, in order (incl. redirects and images) |
| `SPPI_HJ_prices_<date>.xlsx` | The four tables above + methodology sheet; RTL, Arial, header `#283593` |
| `snapshots/` | Everything that was fetched |

`status` says how a price was read: `parsed_page` (HTML table/card), `parsed_pdf`, `api` (official price API),
`image_reading` (reading of an image rate card, see `config/sppi_image_transcriptions.json`).

## Run 2026-10-29 (from a US IP)

| Source | ser | Outcome | Prices | Notes |
|---|---|---|---:|---|
| RTA nol fares | h196 | ok | 66 | Single journey by card x zone, Red Ticket, 7/30/90/365-day passes |
| RTA taxi fares | h4; h6 | ok | 21 | Starting fare only - per-km and waiting rates are **not on the page**. Weekday table has an overlapping band (6 am-8 pm then 8 am-10 am) as published |
| Mega Yachts | n4433 | ok | 12 | "from X AED/hr" per yacht (same 12 values as the handoff) |
| UPS tariff guide PDF | m651 | ok | 3,774 | 5 services x 2 directions, all zones/weights; 0 unparsed lines. **Effective 22 Dec 2024 (676 days old)** - look for a newer guide; fuel surcharge separate |
| Oracle OCI | j5 | ok | 727 | Oracle's public price-list API **in AED** (668 products, last updated 2026-10-08). List prices, not UAE contract prices |
| Pinas Cargo | h4803 | ok | 52 | Air (31 kg AED 465 / 15 per kg, confirmed by the site's alt text), sea (4 box sizes x 4 regions), TV (7 sizes x 4). OCR agreed on 6/6, 14/16, 28/28 values |
| du Ultimate | j2 | robots_disallowed | 0 | du's robots.txt: `User-Agent: * / Disallow: /`. The URL now also redirects to the myaccount.du.ae SME app. Survey or ask du |
| Salik catalogue | h20958 | blocked_bot_protection | 0 | Cloudflare challenge (403). Use an official tariff document |
| e& SMB | j1 | ok, no plan prices | 0 | Only "roaming add-ons from AED 25" |
| OSN Home Plus | j7 | redirected | 0 | -> osnplus.com/en-sa (Saudi) from a US IP; rerun from a UAE network |
| VOX FAQ | i56 | ok | 0 | 3D glasses AED 3; ticket prices only in the booking step |
| VFS doorstep | n799 | ok | 0 | Only USD travel fees, no UAE fee table |
| Cool Freights | h11915 | ok | 0 | No prices (quote based) |

## Changes from the handoff

* **Oracle**: use `apexapps.oracle.com/.../products/?currencyCode=AED` - the price-list page's cells are filled by
  JavaScript, the API returns the same list directly in AED.
* **du**: not "check robots before automating" any more - robots.txt forbids it.
* **Pinas Cargo**: the earlier "31 kg = AED 465" is reconfirmed (image + alt text), and the full sea/TV/air cards are
  now read.
* The run was made from a US IP: geo-dependent pages (OSN) must be rerun from a UAE network.

## Adding a source

Add an entry to `config/sppi_sources.json`. Use `"parser": "probe"` first: `price_mentions.csv` shows whether the page
prints prices at all. When it does, write a parser in `sppi/sources/` that returns rows with
`item, spec, price, currency, unit, price_type, price_text, vat, effective_date, note`, add a fixture cut from the
real page to `tests/fixtures/`, and wire it in `sppi/run.py`.
