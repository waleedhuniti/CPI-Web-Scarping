# Item review brief: every official food item, how we cover it, and how to get closer to the official price

## Goal
The user (Digital Dubai, CPI price collection) wants, for EVERY item of the official food basket, a concrete answer to:
1. Why do we not price it, or why is our price far from the official one?
2. What exactly do we change so that it is priced (coverage) and lands within ±10% of the official price (accuracy)?

The output of this review becomes an item-level action list plus a plan. Be concrete: name products, URLs,
October prices, rules. Vague advice ("improve matching") is worthless here.

## Facts you must work with
- Official price = the monthly average the statistics office collects in person from 4 shops: Lulu, Carrefour,
  Union Coop (الجمعية التعاونية) and Spinneys. It looks like a REGULAR (pre-offer) shelf price and is sticky
  month to month (72-80 % of items unchanged).
- Ours = the online price at Lulu and Carrefour only (carrefouruae.com, luluhypermarket.com), collected daily.
  We compare the October mean of our price (12-31 Oct 2026) against the official SEPTEMBER price, in the official
  sale unit (e.g. "5 كغ", "400 غ", "حبة"), using the REGULAR price (offer kept alongside).
- Metric: an item "hits" when |our price / official − 1| ≤ 10 %. Today: 289 items have an exact product match
  (barcode or name) and 245 of them (85 %) hit; 247 items are only "product-set estimates" (a chained estimate over a
  keyword set, mostly fresh produce, meat, fish) and almost none hit; 101 items have no price at all.
- Known shop effect: because the official is a 4-shop mean and ours a 2-shop mean, a residual difference of a few
  percent is normal and NOT a defect. Do not try to "fix" items that already hit.
- Known bug: Lulu's parser records the struck-through regular price as the price on promotions, so Lulu shows 0
  promotions (its "price" is already the regular price). Carrefour's price is the offer price; regular_price holds the
  pre-offer price. Both are being fixed; assume "regular price for the index" is the rule from now on.
- Known bug: unit conversion in the comparison treated a per-piece price as per-gram (saffron 1 g at 0.03 AED).
  Being fixed; if an item's gap is a unit/pack artefact, say so (diagnosis `unit_or_pack`).

## Policy (hard limits on what you may propose)
- No CAPTCHA / human-check solving, no proxies, no IP rotation, no stealth tricks, no new challenge solving.
  Polite pacing only. A page a site refuses stays unread.
- Never carry a price forward; never invent a price; a missing relative is imputed in the INDEX (flagged), never
  as a price.
- Never pick "the cheapest" listing: a pinned product is chosen because it matches the official spec (type, size,
  brand where given, origin where given), not because its price is close to the official one. A fix that is only
  "the listing whose price happens to equal the official" is circular: label it `calibration_only` and say so.
- Official basket data (codes, weights, official prices) stays internal.
- OFFLINE ONLY in this review: no requests to any shop website. Everything you need is in the files below.

## Your input
A batch file (path given in your prompt) with 24-31 items. Each item record:
- `code`, `class_name`, `cpi_group`
- `official`: desc, unit, brand, barcode, origin, qty, price_aug/sep/oct (AED, official monthly averages)
- `basket`: match_mode (`barcode` | `spec` | `name`), fresh_type, qty_unit/qty_total (the line's own quantity)
- `spec_en`: our English spec (product_en, brand_en, size, must_have, must_not, query_en)
- `status`: `exact_match` | `product_set_estimate_only` | `no_price`
- `comparison`: for exact_match: ours_oct (offer-price mean), ours_regular, pct_vs_sep, pct_regular, shops_found,
  far (>3x), carrefour, lulu (per-shop Oct mean); for product sets: set_estimate, pct_vs_sep
- `checker_causes`: an earlier analyst's cause tags (may be empty)
- `our_october`: per shop (carrefour, lulu): status_counts over 12-29 Oct (e.g. "found/accepted": 15,
  "not_found": 2, "review": ...), details, notes, source, matched titles (what we actually matched), urls,
  avg_price, avg_regular
- `catalogue_candidates`: up to 16 listings from our own daily CATALOGUE crawl of Carrefour and Lulu (15 Oct-3 Nov,
  ~27,000 listings) that look like the same product type: outlet, title, url, category, size, oct_regular (mean
  regular price 15-31 Oct), oct_offer, last_price, listed_days, score (keyword score, not quality). These are the
  only products you may pin; a product not in the catalogue or in our_october does not exist for this review.
  Candidates are keyword hits and often include wrong products: judge each by title, size, brand, origin.

Deeper sources if you need them (read-only):
- `/home/user/CPI-Web-Scarping/data/exports/CPI_basket_12-29_Oct.csv`: every daily row (found / not found / review)
  with note, detail, title, url, price, regular_price, unit_price, qty.
- `/home/user/CPI-Web-Scarping/data/portal/cpi/catalogue/history.json.gz`: the catalogue history
  ({days:[...], p:{"Outlet|id": {t:title,o:outlet,c:category,u:url,h:[[dayIndex, offer, regular],...]}}});
  `catalogue.json.gz` = the 3 Nov snapshot (cols/rows).
- `/home/user/CPI-Web-Scarping/data/basket/basket_source.xlsx` (office basket: code, name, brand, barcode, origin,
  qty), `specs_en.json`, `basket.json`.
- `/home/user/CPI-Web-Scarping/docs/retailers.md` (what each shop site allows), and the agreed improvement plan
  `/tmp/claude-0/-home-user-CPI-Web-Scarping/60ceec26-2c73-59ee-8091-dd0a0c8d8ad5/scratchpad/agents/brainstorm/final_plan.md`
  (actions A1-A14: deploy fixes, regular price, two tiers, pin every pick, fixed sample, fixed shop set, imputation,
  administered prices, model codes, origin re-read, match-quality guard, unit fix, source health).

## Diagnosis categories (pick ONE per item)
- `ok`: exact match and within ±10 % (or within ±10 % on the regular price). Keep as is.
- `shop_effect`: exact, correct product, 10-20 % off, no better match exists: the 4-shop vs 2-shop difference.
- `promo_price`: the gap closes with the regular price (pct_regular within ±10 %).
- `unit_or_pack`: wrong pack size / unit (multipack vs single, 2 kg vs 5 kg, per piece vs per kg).
- `wrong_product`: a different product was matched (name search drift, model mismatch, premium variant).
- `one_shop_only`: correct at one shop, not found at the other although the catalogue shows the same or an
  equivalent product there.
- `out_of_stock_online`: the listing exists but was unavailable in the period.
- `brand_not_online`: the official brand/barcode is not sold online at Lulu or Carrefour at all.
- `no_barcode_loose`: fresh / loose / counter goods (meat by kg, loose cheese, nuts, olives, spices) with no
  barcode; today priced (if at all) by a keyword product set.
- `set_estimate_drift`: product-set estimate built from a keyword set that includes other products or premium
  variants.
- `spec_ambiguous`: the official spec itself is unclear or its barcode is not a real EAN (e.g. 0000006853914), so
  we cannot know which product the office prices.
- `other` (explain).

## Fix types (pick ONE primary per item)
- `keep`: no change.
- `regular_price`: use the regular (pre-offer) price (the global rule fixes it).
- `pin_product`: pin one specific listing per shop (give title + url + oct_regular for each shop). Use when the
  catalogue has the right product (same type, size, brand, origin). Also the fix for one_shop_only and for
  wrong_product when the right listing exists.
- `fix_unit_or_pack`: re-match to the listing with the official pack size / piece count, or correct the conversion.
- `fixed_sample`: for fresh / loose goods: 2-4 named listings per shop (same type, size basis, origin where
  given), priced as a fixed sample (mean of regular prices per shop, then across shops). Name them.
- `substitute_brand`: the official brand is not sold online; propose a listed alternative of the same type and
  size (name it) and flag `user_decision` = the office must accept brand substitution for this item.
- `other_source`: not available online at Lulu/Carrefour at all; needs Union Coop / Spinneys / the office.
- `ask_office`: the spec/barcode must be clarified by the office before anything else.
- `none`: nothing we can do within policy.

## What to return for each item
`code`, `diagnosis`, `explanation` (2-3 sentences, specific, with numbers), `fix_type`, `fix_products`
(list of {outlet, title, url, oct_regular} you would pin or sample; empty if not applicable), `rule_change`
(a one-line engineering/method rule if the fix is a rule rather than a product, else ""),
`expected_price_after` (our 2-shop mean of REGULAR prices after the fix, in the official unit; null if no price),
`expected_pct_after` (vs official September; null if no price), `within10_after` (bool),
`covered_after` (bool: would the item have a publishable exact/fixed-sample price), `confidence` (`high` |
`medium` | `low`), `user_decision` (what the user/office must decide, or ""), `calibration_only` (bool: true if
the products were chosen mainly because their price is close to the official one).

Arithmetic: expected_price_after = mean over shops of (mean of the chosen listings' oct_regular at that shop),
converted to the official unit if a listing's size differs (price × official qty / listing qty). Show your working in
`explanation` when you convert. Be honest: if the best available product is 25 % off, say within10_after=false.
