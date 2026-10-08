# Scraper vs field researcher (Ayesha), 8 Oct 2026 - her basket, her day

Her sheet `8-10-2026` (123 items; Lulu, Carrefour, Spinneys columns) was scraped on the same day on Carrefour and Lulu:
by barcode for the 76 barcoded items, by name + kind + origin for fresh items. Rent and fuel are not sold in supermarkets.
Detail per item and retailer: `comparison.csv`. Script: `scripts/compare_ayesha.py`.

| | Carrefour | Lulu |
|---|---:|---:|
| Items she priced | 59 | 30 |
| Items the scraper priced | 52 | 43 |
| Priced by both | 46 | 27 |
| **Same price** | **46 of 46** | **26 of 27** |
| Only she has a price | 13 | 3 |
| Only the scraper has a price (she wrote "not available online") | 6 | 16 |

* Barcoded items: every price both of us have is identical (72 of 72).
* The one difference: red apple USA (011630102) at Lulu - she has 10.95, the scraper 18.95 for "Red Apple USA 1 kg";
  10.95 is Lulu's "Prince Red Apple Germany". Origin to be checked with her.
* Where only she has a price, it is mostly Carrefour fresh produce (the search page does not show the origin, so the
  scraper does not accept it) and Al Rawdah fresh chicken (Carrefour's search does not find that barcode).
* Her sheet: 011130301 (Modern Bakery toast 500 g) carries the Al Arz bread barcode of 011130204, so both lines price the
  same 200 g Al Arz bread; four bread lines are counted in pieces in the basket but sold by weight.
