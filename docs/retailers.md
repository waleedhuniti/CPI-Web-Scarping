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


## Full barcode runs (2026-10-05) - how they were run and what went wrong

### Carrefour UAE (actor `blackfalcondata/carrefour-maf-scraper`)
* **Run it in batches of 10 barcodes, never in one big run.** A single run over 384 barcodes (and runs of 33-39) silently
  returned nothing for most later barcodes: the same 10 barcodes gave 6 hits alone and 1 hit inside a 39-barcode run. The
  first full run also stalled after ~20 queries. Re-running every missed barcode in batches of 10 gave the real numbers.
* The free Apify plan allows **5 concurrent runs**; at ~40 s per batch the whole basket takes ~15-20 minutes.
* Result: **190 of 384 barcodes found (49%)**, 173 accepted on barcode + size. Raw rows: `data/runs/2026-10-05/carrefour_raw.jsonl`,
  matched: `carrefour_matched.csv` (`python scripts/match_run.py carrefour <raw>`).
* Searching the 13-digit form of 12-digit UPC codes found nothing extra.
* Data quirks seen: a title that disagrees with the product URL (mozzarella "1.1kg" vs URL `900gr`; luncheon meat titled
  "Halawa 1kg" with a luncheon-meat URL; "Green Beans" titled product whose URL says green-peas). The matcher compares the size in
  the title with the size in the URL and sends conflicts to review (`qty_title_url_conflict`).
* Real size changes found (not matched on purpose): Lay's 170 g -> 165 g, vinegar 473 -> 453 ml, custard powder 450 -> 400 g.

### Lulu UAE (`apify/website-content-crawler`, no extra Apify permission needed)
* Search URL per barcode: `https://gcc.luluhypermarket.com/en-ae/list/?search_text=<EAN>`. Use `crawlerType: playwright:firefox`,
  `maxCrawlDepth: 0`, **`ignoreCanonicalUrl: true`** (without it, the crawler treats all search pages as one page and keeps only the first).
* It is slow (~10 pages/minute at 4 GB memory, concurrency stuck near 1-3), so 384 pages take about an hour.
* Ingest with `python scripts/ingest_lulu.py <dataset.json> data/runs/2026-10-05/lulu`; pages that say "No results found" are
  recorded as searched-and-not-carried, never as errors.
* **Delivery area:** Lulu's page header showed "Tomorrow - Al Nahyan" (an Abu Dhabi area), not Dubai. We have not tested whether
  Lulu's prices differ by emirate. Confirm before using Lulu prices as Dubai prices.

### Nesto
No online grocery shop found: `nestoonline.com` times out, `nestogroup.com` is a corporate site, `nestooffers.com` serves an empty
page (flyers). Matajar, which was once "Matajar by Nesto", has operated independently since 2022 (per a web search; not verified).
Needs the real shop address from the user.

## Second-source check on every matched price (2026-10-05)

Every accepted barcode match is re-opened on the retailer's own product page (`scripts/verify_pages.py`, cheap cheerio
crawl, ~$0.03 for 300 pages). A row only goes into the index when the page agrees.

| | Carrefour | Lulu |
|---|---|---|
| Product pages read | 190/190 | 109/110 |
| Search price = page price | 188/190 | 107/109 |
| Basket barcode printed on the page | (Carrefour pages show no barcode) | 107/109 |
| Accepted rows whose page size = basket size | 175/178 | 100/102 |
| Sent back to the officer | 3 | 3 |
| **Final: accepted, priced, in stock on the page** | **174** | **100** |

What the check caught:
* **Lulu 'each' vs 'pack' variants.** Lulu sells the same product as a pack (`/p/943568-ch1/`) and as a single unit
  (`/p/943568-ea/`), with different barcodes. The barcode search card for Almarai milk 4 x 1 L showed 16.50 but linked
  to the single 1 L (4.95, another barcode); Maggi 24-cube box showed 26.20 but linked to one cube (1.25). Both go to
  review instead of into the index.
* **Carrefour page fields that contradict the title.** Del Monte luncheon titled 200 g but page 'Pack Size' 340 g;
  Emborg green beans titled 900 g but page 450 g (and its URL says green peas); Al Kabeer fries page says '2.5g'.
* **The Carrefour Store actor's stock flag is unreliable.** It said out-of-stock for 30 products that the product page
  (Dubai Festival City delivery area) shows in stock. Use the page's JSON-LD `availability`, never the actor's flag.
* **Price moved between runs** for 1 Carrefour product (Al Ain fresh milk 6.69 -> 6.89 within the morning) and one went
  out of stock (Almarai laban). Collect all prices for a period within one short window and keep the timestamp.

Lulu product pages embed the product record with its real barcodes (`"ean":"0000000109628,5011157030920,8901144311002"`,
`"main_ean"`, `"content":"1 kg"`, `"country_of_origin"`), so a Lulu match is now proven by the barcode printed on the
page, not only by the search. The Lulu Store actor cannot be used for this: it returns nothing for product URLs.
Crawl settings for those pages: `crawlerType: cheerio`, `saveHtml: true`, `htmlTransformer: none`, and
`removeElementsCssSelector` must NOT include `script` (the record sits in a script tag). Fetch the dataset 4 items per
call - each page is ~450 KB of HTML and larger reads drop the Apify connection.

## Crawler settings for search pages (learned the hard way, 2026-10-05)
`apify/website-content-crawler` must run with `htmlTransformer: "none"` and `readableTextCharThreshold: 0` on Carrefour and
Lulu search pages. With the default 'readable text' transformer the product grid is removed: most Lulu pages and about one
Carrefour page in five came back as an empty page shell, which would look like "not sold" when the product is there.
`scripts/ingest_lulu.py` and `scripts/name_search.py candidates` report such pages as unreadable instead of "not found".

## Spinneys - test of 2026-10-11 (Scrapling)
* From the cloud environment every request (plain HTTP with a Chrome fingerprint, and Scrapling's stealth browser) gets
  **HTTP 403 from Spinneys' Azure Application Gateway**: an IP block, not a bot challenge.
* Through Apify's unblocker the search page `https://www.spinneys.com/en-ae/search/?q=<text>` loads (`region-id: AE`)
  but contains **no products**: only the page shell and the "Changing Delivery Address" dialog. Products are loaded by
  the browser after a delivery address (store) is chosen; no product API URL is visible in the HTML.
* To add Spinneys: (1) open the site once in a browser **from the UAE**, set a Dubai address and record the product
  search request it makes (DevTools > Network); (2) call that request with Scrapling from a UAE machine / the Dataiku
  server, or with a UAE residential proxy (`FetcherSession(proxy=...)`); (3) check whether search accepts a barcode.
