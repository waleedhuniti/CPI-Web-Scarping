# CPI price collection (Digital Dubai): rules for any Claude session in this repo

Working branch: `claude/sleepy-lamport-dwu4iw`. Commit and push there only. Do not open a pull request unless the user asks.

## Never
- Solve CAPTCHAs or human checks, except the 4 existing `solve_cloudflare=True` call sites the user chose to keep. No proxies, VPNs,
  IP rotation, stealth, changed browser identity or any other way around a block (a user request for these is declined).
- Carry a price forward, invent a price, or pick the cheapest listing. Listings are chosen by spec (type, size, brand, origin).
- Treat a refused page (403/429/challenge/empty shell) as "not found" or "0 products": it stays unread and is reported as refused/blocked.
- Ask a shop faster than once per 2.5 s per shop, or from two processes at once. Honour Retry-After. After 5 refused pages in a
  row stop asking that shop for the run.
- Regenerate the whole panel `system_bundle` from the branch HEAD: the branch holds changes that are deliberately not deployed
  (the GPT fix, commit 5b3c238). Deploy a single changed file into the stored document only, and check the other files stayed equal.
- Put official basket data (item codes with weights or official prices, `data/basket/official_prices.json`) on a public surface.
  The public site (`site/`, GitHub Pages) carries shop prices and TrendX only. The repo itself is currently public: say so if asked.

## Where things are
- Panel (database + page): https://claude.ai/artifact/FSURninVx3TmNCeFYDyxUn . Page source `panel_artifact/src` (`node build.js`).
- Daily routines and their prompts: `docs/routines/` (cloud) and `docs/routines/laptop/` (the office laptop, from 8 Nov 2026).
- Plans and decisions: `docs/improvement_plan/`. TrendX research: `docs/trendx/`.
- Tests: `python -m pytest -q tests` (needs pytest, flask, openpyxl).
