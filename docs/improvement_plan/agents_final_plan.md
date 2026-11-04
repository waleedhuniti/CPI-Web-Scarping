# Final plan: better CPI scraping (coverage, accurate prices, smaller gap to the official CPI)

Chair: the CPI MANAGER, 3 Nov 2026.

**Inputs:**
- round1_manager.md, round1_writer.md
- checker_summary.json and checker_items.csv (CHECKER round 1)
- board.md (round 2)
- scripts in `brainstorm/scripts/` (mgr_official, mgr_ours, mgr_weights, mgr_gapmetric, mgr_change; the WRITER's coverage, coverage_causes, barcode_misses, lulu_strike)

**Status:** final, issued before the CHECKER answered the round-2 questions CQ1-CQ4. Their answers are listed under "Open checks", and they can change two rankings (A3, A6). Everything here was done offline and read-only on the repository.

## 1. What we learned (the evidence behind the plan)

1. **The reported gap mostly measures the formula and the wrong matches, not the scraping.**
   - The same 655 October items give +3.7 % (today's "ratio of group means"), +8.1 % (unweighted geometric mean), +6.6 % (CPI-weighted geometric mean; the CHECKER's figure is also +6.59 %), and **+1.5 % for the median item**.
   - Only 51 % of the items are within ±10 % (`mgr_gapmetric.py`).
2. **Exact-product prices already agree with the official prices.**
   - barcode_search_match: median gap −0.08 %, mean |log| 4.3 % (206 items).
   - name_match: +0.2 % / 6.7 %.
   - product set: +19.2 % / 39 % (233 items).
   - catalogue product set: +2.7 % / 35 % (108 items). (Source: checker_summary.json `by_source`.)
3. **Change (what a CPI measures): exact sources track the official figures.** Ours is 23-29 Oct vs 12-18 Oct, Jevons, on the same items (`mgr_change.py`):

   | source | ours | official Oct/Sep | items changed (ours / official) |
   |---|---|---|---|
   | barcode | +0.95 % | +0.41 % | 26 % / 30 % |
   | product set | −0.87 % | +2.07 % | |
   | catalogue fill | **−4.05 %** | +0.27 % | 75 % / 16 % |

   The CHECKER's overall figure is ours −4.13 % vs official +0.71 %. That gap comes from the catalogue fill (clothing sales) and the product sets.
4. **Official prices are monthly, sticky and look like regular prices.**
   - 72-80 % of items are unchanged each month.
   - The monthly all-items move is −0.7 % to +1.2 %.
   - The fils pattern suggests means of 1-6 outlet quotes (a guess).
5. **Price-type bugs and bias.**
   - Lulu's parser records the struck-through **regular** price as the price on promotions: 10 of 10 on the saved pages. Lulu shows 0 promos in about 14k rows, against 1,706 of 5,833 at Carrefour (WRITER WQ1).
   - Catalogue-fill rows are 37 % on promotion, with a median discount of 39 % (`mgr_ours.py`).
   - Several paths pick the **cheapest** listing (name_live, name_fallback, fill_from_catalogue).
6. **The pick changes from day to day.** Over 16-27 Oct the catalogue product set switched URL on 157/219 pairs (653 switches), name_match on 10/177, catalogue name match on 6/40, and barcode on 0/308 (WRITER WQ2).
7. **Coverage by CPI weight is small.**
   - Our accepted prices cover elementary aggregates worth **13.5 %** of CPI weight, and only **4.9 %** from exact-product sources (`mgr_weights.py`).
   - Food is 97 % covered, but it is only 9.6 % of the CPI.
   - Rent is 33.1 %. Administered or published prices: fuel 3.9 %, electricity and water 2.9 %, Salik/parking 1.6 %, taxi 0.7 %, telecom 4.4 %, school fees 8.0 %, air and holiday packages about 3.1 %.
8. **Line coverage** (WRITER, 27 Oct):
   - 653 of 1,301 lines are priced as stored, but only **410 once the GPT fix is deployed**: the 243 product-set lines go to review.
   - On 2 Nov Carrefour was blocked: 157 lines were lost, and lines priced at 2 shops fell from 147 to 1.
   - 95 barcode lines are missed: 51 have the brand sold but the item not found, 22 have a brand not seen, 15 are out of stock, 7 are another pack size.
   - 179 strict spec rows are blocked on origin evidence. 519 of 1,015 cached origins are "" (the old cache bug).
9. **The live panel still runs the old bundle.** On 2 Nov, 440 product-set rows were accepted, 217 of them carried-forward Carrefour rows. Every comparison must exclude 30 Oct - 2 Nov Carrefour category rows until the bundle is refreshed.

## 2. Ranked actions

Owners:
- W = WRITER (code)
- C = CHECKER (measurement)
- M = MANAGER (method)
- U = the user decides

| # | Action | Expected effect (evidence) | Effort | Risk | Owner | How we measure it |
|---|---|---|---|---|---|---|
| A1 | **Deploy what is already fixed.** Merge the fetch-layer branch, refresh system_bundle with it and with the GPT fix, and move the catalogue routine after the CPI scrape (D2). | Blocked days: +68 barcode lines (200 → 268); 2-shop lines from 1 back to about 147. Removes about 217 carried prices a day on bad days (§1.8-9). | S | low | W, U | Daily: lines priced per shop; zero carried rows; panel run status. |
| A2 | **New yardstick.** Report a CPI-weighted monthly change gap per EA (Jevons of item relatives, weighted by Book1), with level only as a match check (median ratio, share within ±10 %, IQR). Retire "ratio of group means". | Our +3.7 % / −18 % / +20 % group "gaps" become a change gap. Barcode change gap is +0.5 pt today (§1.3). Removes misleading headlines. | S | low | M, C | Monthly report (Oct vs Nov, once the official November figures are out). |
| A3 | **Two tiers.** Tier A (index) = exact product: barcode, name_match, pinned name_live, pinned catalogue name match. Tier B (product set, catalogue product set) is shown but kept out of the index until a 2-month back-test against the official monthly change passes (change gap within ±1 pt per group, and level median within ±10 %). | Index noise drops: Tier A mean \|log\| is 4-7 % vs 35-39 % for Tier B. The change gap goes from −4.8 pt to about +0.5 pt (§1.2-3). **Cost:** index weight coverage drops from 13.5 % to 4.9 % until Tier B passes. | M | medium (coverage) | M, C | Back-test on Oct-Dec. |
| A4 | **Fix the Lulu promo parser** (offer to `price`, struck price to `regular_price`), **and use the REGULAR price for the index**, keeping the offer price alongside. | Correct Lulu offer data (2-6 % of rows change). The index series does not jump on the fix day. Matches the official prices, which look regular and sticky (§1.4-5). | S | low | W, M | Lulu promo share > 0; Lulu index continuity on the fix day. |
| A5 | **Pin every pick and drop "cheapest"** (name_fallback, name_live, catalogue name match), using the category pin store: stay on the URL while it is listed and passes accept(); repick only after N missing days, with an overlap link. | Removes 34 switching pairs out of 226 and the downward level bias of "cheapest" (§1.5-6). | S-M (about 1 day) | low | W | URL switches per month → about 0 for pinned paths. |
| A6 | **Fixed sample instead of a product set for Tier B.** Per line and shop, freeze 3-5 listings (respecting basket origin and spec), take the monthly mean of regular price per listing and Jevons across them, and replace by overlap. | Expected to cut product-set noise (sd 15.9 %, 77 % changed per week) towards barcode-like behaviour. **Coverage effect to be measured** (WRITER count requested, §4). | M | medium | W, M | Back-test as in A3. |
| A7 | **Fixed shop set per item.** The item relative is computed only over shops seen in both periods, then the geomean across shops. Never average a changing shop mix. | Removes the composition effect: Carrefour 479 → 219 rows/day on 30 Oct (§1.8). The CHECKER sees Carrefour +10.1 % vs Lulu +1.7 % in level. | S | low | C, M | Index unchanged when one shop is missing for a day. |
| A8 | **Imputation in the index, never in prices.** A missing item relative inside an EA is imputed by the EA's mean relative (class-mean imputation), and flagged `imputed`. No price is ever written. | Standard CPI practice. Stops EA composition noise on blocked or out-of-stock days. | S | policy wording | M, U | Share of imputed relatives per EA per month (target < 20 %). |
| A9 | **Administered / published prices** (outside the shops): petrol (3 grades + diesel), Salik, a gold rate per gram first; then DEWA electricity and water, and the RTA taxi tariff. About 50 requests a month. | CPI weight priced: fuel 3.9 + Salik 1.6 + gold 0.2 = **+5.7 pts**; then DEWA + taxi = **+3.6 pts**. Weight coverage goes from 13.5 % to about 23 %, with exact prices. | S then M | low (parse); one live verification needed later | W, U | Weight coverage by division; the price equals the official item where the official file has it. |
| A10 | **Durable goods by model code** (Carrefour, Lulu, the Sharaf DG Algolia query); accept only an exact model-code hit. Weekly. | 47 unpriced model-code lines; guess +20-30 (WRITER W2; 4 already match in the catalogue sample). | M | low | W | Lines priced; exact-code audit. |
| A11 | **Origin evidence re-read** (one-off, 519 product pages, outside the routine window, under the new fetch layer), with a cross-day origin cache by URL. | Unknown until measured. Up to 76 review_origin rows could become exact. | M | low | W, C | Matches per spec line before and after. |
| A12 | **Match-quality guard.** The official unit must match: "واحدة" (one piece) ≠ a multipack; 1.5 L ≠ a value pack. Clothing and electronics matches only with a spec or model check. Auto-flag items whose level ratio is outside 0.67-1.5 for review (not just 3×). | Removes the top weighted level errors: Zara shirt 2.80×, dress 0.55×, water multipack 0.69-0.72×, Gillette refills vs one razor (`mgr_gapmetric.py`). | S | low | W, C | Share of items within ±10 % in level (51 % → target 70 %). |

### Added after review by the WRITER and CHECKER (both agreed; they rank next to A1/A4)

| # | Action | Expected effect (evidence) | Effort | Risk | Owner | How we measure it |
|---|---|---|---|---|---|---|
| A13 | **Unit-family fix for price_spec** (CHECKER C1 = WRITER W12). `scripts/export_basket_csv.py:75-77` `fill_spec_price` converts a "pc" basis with the line's g/ml factor (saffron 1 g: 25.70 → 0.03), and per-kg prices are compared as per piece or per bunch (paratha, spinach). Convert only within a unit family (kg↔g, l↔ml, pc↔pc); otherwise leave price_spec empty and send the row to review. | **3.3 of the 13.95** weighted log points of the level gap (CHECKER, board). It also fixes every price_spec in the Dataiku export. | S | low | W, C | Re-run the October comparison offline; no item compared across unit families. |
| A14 | **Source-health line per source and shop** in run.json: pages read/failed, parsed rows, promo share (Lulu must be > 0 after A4), the fetch-report verdict. | It would have shown the Lulu promo bug, which stayed invisible for weeks because "0 promos" looked plausible. Faults become visible the next day. | S | low | W | Daily check of the run summary. |

**Engineering order (agreed):** A1 deploy → A4 Lulu parser → A13 units → A5 pins → A14 source health → A12 match guard → A10 model codes → A9 administered prices. Method work in parallel: A2/A3/A7/A8 (MANAGER + CHECKER).

**Timing of the first fair test (CHECKER):** our October covers only 12-29 Oct. The first clean change back-test is therefore our Nov/Oct against official Nov/Oct, in early December, followed by Dec/Nov. The A3 two-month back-test ends in early January.

## 3. Rejected or parked ideas, and why

| idea | decision | why |
|---|---|---|
| Scrape more clothing (Centrepoint/Max/Zara product sets) | parked | The official items are generic specs (fabric %); matches are weak (0.36-2.8×); sales cause the −30 % noise. Use Tier B only after A6. |
| Delivery-app restaurant menus | parked | Aggregator mark-ups, method risk; needs a user decision on outlet type. |
| Telecom plans (du/e&) | parked | High parse risk: JS pages, bundles, possible bot protection. Plain fetch only. |
| Rent from listings | not now | 33 % of the weight, but it is a stock-of-tenancies measure; listings are asking prices for new contracts. Use the official rental index if the user can obtain it (decision U4). |
| Taking the cheapest listing as the shop price | rejected | It biases levels down and changes product day to day (§1.5-6). |
| Carrying a price forward over missing days | rejected | Policy. Use A8 (imputation of the relative, flagged) instead. |
| More shops through stronger anti-blocking | rejected | Policy: no proxies, no stealth, no new challenge solving. |
| Re-accepting product sets as they are today | rejected | Level median +19 % and noise 39 % (checker by_source). They come back only through A6 plus the back-test. |

## 4. Round-2 answers received after the first draft (they confirm the ranking)

- **CHECKER, level decomposition.** CPI-weighted level gap +15.0 % with all items, +6.6 % without the 43 items more than 3× off. Of 13.95 log points:
  - +8.60 from wrong product/size/unit;
  - +6.05 from food product sets;
  - −0.15 from barcode;
  - +0.05 from name matches.

  → A12 and A3 are confirmed as the biggest levers.
- **CQ1.** Exact sources with a fixed shop set: ours +0.92 % vs official +0.36 %. The −4.13 % is clothing catalogue sets (−33 %, listing churn). → A3 is confirmed.
- **CQ2.** The +23.6 % "regular" level is an artifact of the catalogue product-set regular_price field. On exact sources, shelf −0.68 % and regular +0.09 %. → A4 (regular price) is supported.
- **CQ3.** Fixed shop set (geomean): −1.8 %. Carrefour −2.0 % and Lulu −1.6 % on the same 179 products. Carrefour's +10 % came from premium members of its product sets, not from its shelf prices. → A7 is confirmed, and A6 must exclude premium tiers.
- **CQ4.** The weekly item-relative sd on exact sources is 3.0 %, so the standard error of a monthly mean over about 280 items is about 0.25 %. **A ±1 % official move is resolvable by Tier A.**
- **WRITER, fixed sample (A6).** With the first 3 URLs, 179/219 lines are still covered after 11 days (82 %), with 85 % of line-days having at least one URL. With the day-1 URL only: 68 % / 72 %.
  - The 3-URL figure is flattered by look-ahead; a true day-1 sample needs catalogue_fill to save its candidate list (S).
  - Expect 15-30 % missing line-days, so A6 requires A8 (imputation).

- **CHECKER, final round:**
  - CQ3 on regular prices: Carrefour −0.16 %, Lulu −1.57 %, fixed-shop geomean −0.84 % (179 exact products). Only 7 % of Carrefour exact rows are on offer.
  - A4 confirmed on change: 267 items, regular +0.69 % (mean item error 1.56 %) vs offer +0.92 % (1.89 %), official +0.36 %.
  - CQ4: sd 3.0 % (2.2 % trimmed) holds **only with A7** (fixed shop set); my 13.8 % included shop-mix switches.
  - **A12 refined:** the 0.67-1.5× flag is applied to Tier A only. It catches 4 of 291 barcode/name items, against 177 product-set items. Keep the 3× gate for all items. The flag uses official prices, so it stays internal (never on the public site).

## 4b. Open checks as first asked (now answered above)

- **CHECKER CQ1:** the change gap on exact sources only. My `mgr_change.py` gives barcode +0.95 % vs +0.41 %; the CHECKER should confirm it with the same item set.
- **CHECKER CQ2/CQ3:** the regular-price level (+23.6 %) and Carrefour vs Lulu.
  - The Lulu bug (A4) means Lulu "price" is already regular, while Carrefour's is the offer price.
  - So the shop comparison must be redone on regular prices at both shops before A4/A7 are tuned.
- **CHECKER CQ4:** the std of weekly item relatives on exact sources: barcode sd is 13.8 %, with outliers (`mgr_change.py`). A trimmed estimate is needed to state the resolution of the monthly index.
- **WRITER:** fixed-sample survival for the 219 catalogue product-set lines (the A6 coverage effect).

## 5. Decisions the user must take

- **U1. Index price.** Regular price for the index (offer kept alongside), as proposed in A4. *Recommended.*
- **U2. Two tiers.** The product sets go out of the index until back-tested (A3). The index weight then covers 4.9 % plus A9, instead of 13.5 %, for a few months. *Recommended: accuracy before coverage.*
- **U3. Class-mean imputation of missing relatives** in the index, flagged, never shown as a price (A8). *Recommended.* It is the standard CPI method, and consistent with "never carry a price forward".
- **U4. Scope beyond shops.**
  - Administered prices (A9). *Recommended.*
  - Rent and school fees: is there access to the official rental index and to KHDA fee data? These are 41 % of the weight.
- **U5. Origin substitution policy** for fresh food (103 genuine other-origin rows, e.g. EG→ZA): does the official practice accept the origin the outlet stocks?
- **U6. Deployment:** merge the fetch-layer branch, refresh system_bundle, move the catalogue routine (A1/D2).
- **U7. robots.txt check** for the new administered-price pages (D4), before the one-off live verification.
