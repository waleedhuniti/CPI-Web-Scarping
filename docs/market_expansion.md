# Adding grocery markets while retaining bulk category collection

Assessment date: 2026-11-02. Research validates the existence of shopping channels, not scraper feasibility or complete Dubai coverage. No new retailer is enabled by this change.

## Candidate order

1. **Union Coop**: first pilot. Its official food-category page exposes category and brand navigation. Validate pagination and product details for a fixed Dubai delivery area. Separate public prices from Tamayaz/member promotions. Prefer a permitted retailer feed if available.
   Sources: https://www.unioncoop.ae/food-category.html and https://corporate.unioncoop.ae/en/online-shopping/frequently-asked-questions/
2. **Spinneys**: next pilot for fresh-food discovery. Official FAQs advertise Dubai delivery. Existing repository probes report an address-dependent catalogue and 403 responses; those are historical observations, not proof that collection is impossible today. Re-test with an explicitly selected Dubai store/location, preserving that context per observation.
   Source: https://www.spinneys.com/en-ae/frequently-asked-questions/
3. **Nesto**: investigate the current online channel. The official developer's Google Play listing advertises Nesto Collect, Nesto Quick, and fresh groceries (listing updated 2026-10-28). This supersedes the assumption that there is no online offering, but does not prove a usable public category endpoint. Establish branch coverage and a permitted web/feed integration before estimating development effort.
   Source: https://play.google.com/store/apps/details?id=com.nesto.customer.customer_app

## Integration design

Preserve: retailer category crawl -> shared catalogue -> basket filters -> review/acceptance -> product continuity -> exports.

Introduce an adapter registry rather than adding more `if retailer == carrefour else lulu` branches. Each adapter should declare supported operations (categories, product detail, optional barcode search), pagination, location requirements, retries and rate limits. Optional barcode lookup must not block adding a category-only market.

Normalize every observation to retailer, store/location, retailer product ID, observed timestamp, title, brand, GTIN if actually exposed, pack quantity/count, unit price and basis, origin, current/regular price, promotion eligibility, availability, URL and raw evidence reference. Never invent a GTIN from a retailer's internal ID. Deduplicate by retailer + location + product ID while retaining category membership.

Refactor the hard-coded shop sets in `scrapling_category.py`, `product_panel.py`, `panel_run.py`, catalogue-fill label mappings, portal settings and routine orchestration together. The common matcher and exports must consume the registry; adding only a category URL is insufficient.

Track page-request failure separately from a confirmed empty category. Persist a crawl manifest, compare expected and observed page/product counts, and checkpoint observations. Revalidate mappings each run; review rows remain unapproved across all exporters.

## Pilot acceptance

Start Union Coop with fruit, vegetables, meat/fish, and a packaged-goods category. Manually verify a stratified sample of candidate matches and rejected candidates against the product pages. Repeat collection over several days and verify unchanged products, pack changes, promotions, stock transitions, and location consistency. Report precision, additional unique basket coverage, category coverage, overlap, review burden and collection failures. Rank later markets by their incremental verified coverage, not their catalogue size.

Do not promise a target coverage percentage before this pilot. Online catalogue coverage alone does not establish representativeness of Dubai purchases or outlet weights.
