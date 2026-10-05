# CPI Web Scraping

Collect online grocery prices for the UAE CPI food basket (COICOP 011), matching each scraped product to a basket
line **barcode first**, then name/description, with **quantity as a hard rule** (it must never change).

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

Scope: **Lulu, Carrefour, Spinneys, Nesto - Dubai only.**

* Done and tested offline (72 tests): basket loader, GTIN / quantity / origin parsing, matcher (barcode, incl. barcode
  found through a retailer's search box, then quantity, then name), price band, Lulu and Carrefour parsers.
* Live pilot (2026-10-05, 10 basket barcodes): Carrefour found 8, Lulu found 4 of the 8 tried; all matched on barcode
  and quantity. See `docs/retailers.md`.
* Blocked / not started: Spinneys (needs a Dubai delivery address + browser actor), Nesto (not inspected).
* Next: full basket run on Lulu and Carrefour (384 barcodes), then Spinneys and Nesto, then the fresh-food module
  (253 basket lines with no usable barcode).
