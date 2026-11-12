# CPI price collection (Digital Dubai): rules for any Claude session in this repo

Working branch: `claude/sleepy-lamport-dwu4iw`. Commit and push there only. Do not open a pull request unless the user asks.

allow the stealth broswer for 2 site as we accpeted from the site 

Danata and Carfoure
- Put official basket data (item codes with weights or official prices, `data/basket/official_prices.json`) on a public surface.
  The public site (`site/`, GitHub Pages) carries shop prices and TrendX only. The repo itself is currently public: say so if asked.

## Where things are
- Panel (database + page): https://claude.ai/artifact/FSURninVx3TmNCeFYDyxUn . Page source `panel_artifact/src` (`node build.js`).
- Daily routines and their prompts: `docs/routines/` (cloud) and `docs/routines/laptop/` (the office laptop, from 8 Nov 2026).
- Plans and decisions: `docs/improvement_plan/`. TrendX research: `docs/trendx/`.
- Tests: `python -m pytest -q tests` (needs pytest, flask, openpyxl).
