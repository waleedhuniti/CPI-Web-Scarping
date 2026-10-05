# Retailers - what works today (Dubai only)

Scope: **Lulu, Carrefour, Spinneys, Nesto**. Findings from a live pilot on 2026-10-05; raw rows in
`data/pilot/pilot_2026-10-05.csv`.

| Retailer | Barcode lookup | Status | Pilot hit rate (10 basket barcodes) |
|---|---|---|---|
| Carrefour | Keyword search accepts the EAN. Bulk: one actor run with a JSON array of EANs. | Ready | 8 of 10 |
| Lulu | Search page `list/?search_text=<EAN>`. Exact: one product or "No results found". | Ready | 4 of 8 tried |
| Spinneys | Not reachable yet - needs a delivery address and a browser. | Blocked | - |
| Nesto | No actor; site not inspected. | Not started | - |

## Things the pilot taught us

* **Carrefour's `gtin` field is not a barcode.** The Store actor fills `gtin`, `sku` and `productId` with Carrefour's own
  id (Tilda 1 kg = `79241`) and leaves `barcode` empty. The page shows no EAN either. The evidence is that
  *searching the EAN returned exactly this product*, so a Carrefour hit is recorded as `barcode_search_match`, and
  only when the search returned exactly one product (several -> review queue).
* **Quantity still has the last word.** Barcode hits are accepted only if the size in the title equals the basket size:
  `1kg`, `4 Litres`, `75g Pack of 5` are all read (`cpi/quantity.find_quantity`).
* **Offers are real.** Lulu showed an olive oil at 105.00 against a regular 238.95 (56% off) while Carrefour had it at
  289.00 (out of stock). The listing keeps `price` and `regular_price` apart so the statisticians can choose.
* **Out-of-stock rows exist** (Carrefour olive oil and moong dal). Identity matching does not look at stock; the
  collection step must keep `in_stock` and the index step must skip unavailable items.
* **Coverage differs by retailer.** Lulu did not carry 4 of the 8 barcodes we tried (Al Rawdah chicken, Al Ain milk,
  Almarai milk, Indomie); it may sell the same product under a different barcode. Those become "not found at this
  retailer" - a normal outcome, not an error.
* **Prices agree across retailers** where both match (Tilda 1 kg 17.79 / 16.75; sugar 2 kg 9.89 / 10.05; moong dal
  16.79 / 17.25), which is a useful sanity check.

## Running it without deploying anything

The Store actors and `apify/web-fetch` run on Apify from the console or API. `apify/web-scraper` (a generic browser
scraper that would let us run a custom page function) asks for **full account access** the first time it is used; that
approval is yours to give at https://console.apify.com/actors/moJRLRc85AitArpNN?approvePermissions=true.
`actors/lulu_search/page_function.js` is a ready page function for it that would fetch many Lulu barcodes in one run
(written but **not yet run**, because that approval has not been given).

## Spinneys - what is needed

The category tree is plain HTML (`/en-ae/catalogue/category/<slug>_<id>/`), but product cards are not in the page
Apify's fetcher receives, and the page text asks for a delivery address ("Changing Delivery Address ... may change the
Spinneys store that delivers your items"). Prices are therefore per delivering store. To scrape it we need to:

1. choose the Dubai address/store to price against, and
2. build a Playwright actor that sets it, then walks the category tree and reads product cards.

## Nesto

Nothing exists on the Apify Store. Needs the same inspection as Spinneys (does the site have a barcode search? does it
need a store/area?) before a plan can be made.
