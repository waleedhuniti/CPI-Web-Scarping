# SPPI H & J - price collection with Scrapling (all sample companies)

Prices for the Services Producer Price Index (ISIC Rev.4 sections H and J) for **every company and product of the
sample**: 73 companies, 446 products/services from `SPPI_HJ_Red_Companies.xlsx` (sheet `المنتجات والخدمات`).

```bash
pip install -r requirements.txt
python scripts/sppi_import_products.py SPPI_HJ_Red_Companies.xlsx   # -> data/sppi/sample/{companies,products}.csv
python scripts/sppi_run.py                                          # -> data/sppi/runs/<today>/
python scripts/sppi_run.py --only j1,dtc_taxi --out /tmp/try        # some companies (ser) or pages (id)
python -m pytest tests/test_sppi.py
```

Optional: `tesseract-ocr` (cross-check of image rate cards) and a Chromium for the two pages fetched with a browser
(`scrapling install`, or point `SPPI_CHROMIUM` at one).

## Every row carries the sample codes

| Column | From |
|---|---|
| `ser` (الرقم المتسلسل: h1, j2, n4433 ...) | the sample |
| `section` (H / J) | sheet `اطار المصادر` column E |
| `isic_registered` (رمز النشاط المسجّل, e.g. 5110) | the company's registered activity |
| `type` (منتج / خدمة), `product`, `isic_product` (رمز ISIC الفعلي للبند, e.g. 5223) | sheet `المنتجات والخدمات` |
| `product_id` (h1-08 ...) | ser + row number in the products sheet |

Example: `h1 | H | طيران الامارات (الموارد البشريه) | 5110 | خدمة | marhaba lounge | 5223 | from AED 195`.

## Availability of a price - `إمكانية الحصول على السعر`

On every product (sheet `المنتجات`), every page (`ملخص الصفحات`) and every request (`سجل الجلب`):

| Value | Meaning |
|---|---|
| **Scraping** | the price was collected automatically in this run (with URL, HTTP status, time, snapshot) |
| **Online فقط** | a person can see the price on the site/app, but it cannot be collected automatically: robots.txt forbids it (du, Shahid), a bot wall (Salik), a booking/sign-up step (air fares, VOX tickets, OSN+), or an in-app price (talabat). Column `تم التحقق` says whether the price was actually seen (yes) or is expected and needs a manual check (no) |
| **لا هذا ولا ذاك** | no public price: quote/contract (B2B), or no site - the reason is in `السبب / الملاحظة` |

`Online فقط` statuses and reasons are kept in `config/sppi_status.json`; products without a price and without a
status get the reason from sheet `تقييم Scraping`.

## How it works

1. `config/sppi_pages.json` lists the price pages (52) and, for each, rules that link its prices to `product_id`s
   (regex on the item text). A `+Name` target is a priced service that is not in the product list (shown with
   `ضمن قائمة المنتجات؟ = لا`). Every source URL in the products sheet is also probed (58 more pages), so each
   company has at least one logged request.
2. Parsers: dedicated ones for RTA nol / taxi, Mega Yachts, UPS tariff PDF (rates + 20 additional fees), Oracle price
   API (AED), Pinas image rate cards, HTML price matrices (`tables`); everything else uses `generic`, which finds the
   smallest element printing an amount and keeps its heading, card title, list labels ('Friday', 'All Weekdays'),
   table row/column and the text after it ('/Month 5% VAT Excluded'). Site banners repeated on many pages are dropped.
3. Rules: robots.txt first; 2 s between requests to a host; no challenge solving, no login; every fetched page / PDF /
   JSON / image is stored gzipped in `snapshots/` with its sha256.

## Run 2026-10-29 (from a US IP)

**446 products: 61 Scraping, 60 Online فقط, 325 لا هذا ولا ذاك** (H: 49 / 35 / 161, J: 12 / 25 / 164).
7,187 price rows; 113 requests.

| ser | Sec. | Company | Scraping | Online فقط | Neither | Price rows | Where |
|---|---|---|---:|---:|---:|---:|---|
| n4433 | H | Dutch Oriental Mega Yachts | 11 | 0 | 2 | 24 | 12 yachts "from AED/hr" |
| h196 | H | Dubai Metro (RTA nol) | 9 | 0 | 1 | 105 | fares by card x zone, Red Ticket, passes, concessions |
| j1 | J | e& (Etisalat) | 8 | 1 | 0 | 120 | eLife Lite 12/25/50/100, Ultra Sports, Business First Plus, Business Pro, Business Internet, Emirati out-of-bundle rates, + Business Xtreme / Data SIM / TV / landline / prepaid |
| h4 | H | Dubai Taxi | 8 | 0 | 6 | 94 | taxi (incl. per-km AED 2.45), limousine (3.90/km), Ameera, Safe Hands, airport, ladies & family, PoD, My Driver, + hourly taxi rental |
| m651 | H | UPS | 7 | 0 | 1 | 5,776 | tariff guide (effective 22 Dec 2024 - 676 days old) + COD AED 29, POD AED 27 ... |
| h10 | H | flydubai | 5 | 10 | 6 | 75 | excess baggage per kg by zone (63), seat from AED 16, fare-type fees, infant fare, parking T2, chauffeur |
| h4803 | H | Pinas Cargo | 4 | 0 | 4 | 68 | air / sea / TV rate cards (image readings, hash-locked) |
| j5 | J | Oracle | 3 | 0 | 6 | 871 | OCI price-list API in AED (Fusion SaaS: quote only) |
| h1 | H | Emirates | 2 | 7 | 7 | 6 | Wi-Fi USD 2.99-19.99; marhaba lounge from AED 195 |
| h20958 | H | Salik | 1 | 3 | 1 | 3 | toll AED 6 peak / 4 off-peak from dubai.ae (salik.ae behind Cloudflare) |
| h6 | H | Cars Taxi | 1 | 0 | 10 | 21 | Kabi = RTA regulated starting fares |
| h2 | H | dnata | 1 | 0 | 11 | 12 | marhaba (dnata) Meet & Greet, transfers, chauffeur, check-in |
| j10 | J | Cisco | 1 | 0 | 4 | 5 | Webex UAE price page (USD) |
| i56 | J | VOX Cinemas | 0 | 11 | 0 | 1 | tickets only in booking; + 3D glasses AED 3 |
| h22 | H | DHL Express | 0 | 9 | 0 | 0 | online quote only |
| j607 | H | talabat | 0 | 6 | 0 | 0 | in-app prices |
| j2 | J | du | 0 | 6 | 0 | 0 | robots.txt `Disallow: /` |
| n799 | J | VFS | 0 | 5 | 0 | 6 | country fee pages 403; + global VAYD travel fees (USD) |
| j3 | J | MBC | 0 | 1 | 5 | 0 | Shahid: robots.txt |
| j7 | J | OSN | 0 | 1 | 3 | 0 | OSN+ price only in sign-up; Home Plus page gone |

The other 53 companies (B2B logistics, shipping, media, IT services, ...) publish no prices - survey with a fixed
service specification. 13 of them have no verifiable website.

Findings worth knowing:
* RTA's taxi page prints a weekday band "6 am - 8 pm" followed by "8 am - 10 am"; Dubai Taxi's own page shows
  "6:00 AM - 8:00 AM" - a typo on RTA's page.
* e& business pages show a struck-through regular price next to a 20%-off offer price (first 5 months); the item
  column keeps both numbers.

## Files of a run (`data/sppi/runs/<date>/`)

| File / sheet | What |
|---|---|
| `products_availability.csv` / `المنتجات` | 446 rows: codes, availability, verified, n prices, price range, reason |
| `prices.csv` / `الأسعار` | one row per price x product: codes + item, price, currency, unit, price text, URL, HTTP status, time, method, snapshot, sha256 |
| `pages.csv` / `ملخص الصفحات` | one row per page: outcome, robots, counts, notes |
| `fetch_log.csv` / `سجل الجلب` | every request (incl. images) with `إمكانية الحصول على السعر` |
| `price_mentions.csv` / `إشارات الأسعار` | amounts on probed pages (evidence, not index prices) |
| `SPPI_HJ_prices_<date>.xlsx` | all of the above + methodology; RTL, Arial, header `#283593`, availability coloured |
| `snapshots/` | everything that was fetched |

## Adding or fixing a source

Add a page to `config/sppi_pages.json` (`parser: generic` first), run it with `--only <page id> --out /tmp/try`,
look at `prices.csv`, then tighten with `keep` / `drop` and `map` rules. Change availability reasons in
`config/sppi_status.json`.
