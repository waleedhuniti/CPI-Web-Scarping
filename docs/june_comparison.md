# June 2026: manual CPI vs the scraped index - what it says and what to do

Input: `data/june_comparison_step8.csv` (11 classes, March-June 2026, April = 100 for both series). The scraped series
was built by someone else, so we cannot audit it item by item; this note reads only the class-level numbers.

## What the numbers say

Index level in June (April = 100), percentage change since April:

| Class | Official | Scraped | Gap (pp) | Reading |
|---|---:|---:|---:|---|
| 1312 personal care | +0.24 | +0.17 | -0.07 | agrees |
| 0115 oils & fats | +0.39 | +0.12 | -0.27 | close |
| 0561 household non-durables | -0.18 | +0.15 | +0.33 | close, but the class barely moves |
| 0118 sugar, jam, sweets | +0.22 | -0.48 | -0.70 | scraped invents movement |
| 0119 other food | +0.37 | +1.61 | +1.23 | too high |
| 0111 cereals & bread | +0.42 | +2.52 | +2.10 | too high |
| 0116 fruit & nuts | +2.05 | +4.29 | +2.24 | right direction, double size |
| 0112 meat | -1.99 | +1.71 | +3.70 | wrong direction |
| 0117 vegetables | +8.04 | +3.67 | -4.36 | right direction, half size |
| 0113 fish | -4.72 | +0.05 | +4.77 | misses the fall |
| 0114 milk, cheese, eggs | +3.05 | +9.25 | +6.20 | worst class |

* **Only two comparable months.** March is before the base and April is the base, so the series carries just May and
  June. Any conclusion is provisional.
* **Personal care (1312) agrees closely; household non-durables (0561) and oils (0115) are close.** Electronics is not
  in this file, so it cannot be judged from it.
* **Fresh is not the only problem.** Average June gap: fresh-type classes (0112, 0113, 0116, 0117) 3.8 pp, packaged
  food (0111, 0114, 0115, 0118, 0119) 2.1 pp, non-food (0561, 1312) 0.2 pp. The fresh vs packaged difference is not
  statistically clear with this few points (Mann-Whitney p = 0.21), but non-food is clearly better.
* **The worst class is dairy (0114), which is mostly barcoded** (94% of its basket lines carry a GTIN): scraped +9.3% vs
  official +3.1%. Having a barcode does not by itself make the scraped index right. Barcode share vs gap across
  classes: r = -0.2, not significant. (The most barcoded class is 0115, at 100%; it is close.)
* **In quiet months the scraped series adds about 1 pp of movement that is not there** (0111 May +2.8 vs -0.05; 0118
  June -1.9 vs +0.2). That is the signature of unit changes, pack-size changes, promotions or product
  substitutions in the scraped data - exactly what the barcode + size + page checks in this repo are built to stop.
* When the official index moves at least 0.5% in a month, the scraped one moves the same way 8 times out of 9, but the
  size is often wrong.

## The smart move

1. **Do not decide by the label "barcoded" or "fresh". Decide class by class on measured agreement.**
   * Adopt now (with a tripwire): **1312 personal care.**
   * Run in parallel (shadow) and compare every month: **0115, 0119, 0118, 0116, 0561.**
   * Keep manual for now: **0111, 0112, 0113, 0114, 0117.**
2. **Scrape barcoded and packaged items first.** Not because they already agree (0114 shows they may not), but because a
   barcode lets you audit every single price: same barcode, same size, price from the product page. When a class
   disagrees you can find the bad items. With fresh produce you cannot.
3. **Keep fresh produce manual and scrape it as a shadow pilot.** Use specification pricing (product + grade, price per
   kg, origin recorded, a price band around the median) as described in the README (rule 4) and `cpi/pricing.py`. Move a fresh class only after it
   tracks the manual series.
4. **Ask for the item-level June data** for 0114, 0113, 0117, 0112 and 0116 (price, size, barcode, retailer, date). The
   gaps will most likely trace to a handful of items - a pack-size change, a promotion, a wrong product - and that is
   checkable.
5. **Re-assess after 3-6 more months with thresholds fixed in advance**, e.g. adopt a class when |level gap| < 0.5 pp
   and monthly direction agrees in at least 5 of 6 months; drop back to manual if the gap exceeds 1 pp twice in a row.

ONS (UK) and Eurostat practice is the same: scanner/web data replace manual collection class by class, after a period
of parallel running, and fresh produce is the last to move.
