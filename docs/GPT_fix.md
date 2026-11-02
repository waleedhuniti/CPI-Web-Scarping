# GPT fix: acceptance and saved category mappings

Scope: the agreed review-status, category-filter and pinning fixes. The bulk category crawl remains the source of candidates.

## Changes

- `cpi/decision.py` no longer approves quantity-unverified barcode matches, ambiguous category matches, or unknown-origin review rows. The same policy feeds the panel and long Dataiku export.
- Category pins must pass the current specification filter and match the basket origin. Only accepted matches create pins. Version-1/unversioned pins are reassessed against all current candidates; they are not grandfathered into approval.
- Unknown/different-origin candidates stay in review, including the first observation. Price proximity alone cannot approve a substitution.
- Pins persist by default in `data/state/category_pins.json` (gitignored); `CPI_PINS` still overrides this. Writes use atomic replacement. Run only one writer per pin file; a shared concurrent service needs a transactional store.
- Missing English specifications no longer match an entire category accidentally.
- Long export retains category candidate evidence with `accepted=no` for review.
- The newer product-panel calculation ignores origin/brand and produces a chained estimate, not an observed quote for the exact basket specification. Its output now remains `review_product_set`, `accepted=no`, with the calculation in `estimated_price` and `line_index`; price/unit_price are empty. The daily CSV retains these diagnostic fields. This deliberately lowers automatic acceptance until the broader product-set methodology is explicitly approved or narrowed to the basket specification.
- Existing `not_observed` handling for incomplete shop crawls remains intact.

## Deployment and verification

Run `python -m pytest -q`. Regression tests cover review acceptance, changed pinned attributes/origins, ambiguous and legacy pins, initial origin substitution, default persistence, missing specs, long export, and panel overrides including incomplete crawls.

Repository code is updated; existing saved runs/feed files and the hosted panel database are not rewritten. A separately hosted daily routine uses a copy of the source: regenerate with `python scripts/bundle_for_panel.py <output_dir>` and refresh its `system_bundle` collection before expecting the live panel to execute these fixes. Preserve the pin file between scheduled runs. Review/rebuild historical outputs separately with recorded policy versions.

## Remaining work from the broader audit

This commit is not a full statistical certification. Product-page GTIN verification, stricter name/variant matching, crawl-completeness handling, live retailer availability checks, and an independently labelled accuracy benchmark remain separate work. Product-panel historical membership and replacement/index methodology also require review. Existing auxiliary name/catalogue fill paths have their own acceptance rules; they are not all redesigned here.
