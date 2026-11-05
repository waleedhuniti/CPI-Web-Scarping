# Portal rebuild brief v2: three projects, each a PIP-style workspace (BUILDER and QA)

This replaces `council3/draft_brief.md`. Council decision: `council3/decision_ar.md` (Arabic, for the user). Debate:
`council3/transcript_ar.md`. Where this brief and the draft disagree, this brief wins.

## 0. What the user asked
"Home page with 3 projects — CPI, SPPI, TrendX. Inside each project, exactly the layout of our office platform (PIP):
the same left sidebar menu and each page with the same system."

## 1. Paths, roles, harness (unchanged from the draft)
- Source (do not edit in place): /home/user/CPI-Web-Scarping/panel_artifact/scraping-panel.html (3,303 lines; claude.ai
  artifact page, Arabic RTL today). It uses `window.claude.use("db")`, `"mcp"` (Claude Code Remote get/update/fire_trigger)
  and `"downloads"`, and it reads uploaded blobs with `fetch("/_blob/<id>")`.
- Working copy (BUILDER edits only this): /tmp/claude-0/-home-user-CPI-Web-Scarping/60ceec26-2c73-59ee-8091-dd0a0c8d8ad5/scratchpad/pip2/scraping-panel.html
  (copy the source there first, if it is not already a fresh copy).
- Nobody publishes, writes the artifact database, commits or pushes. The orchestrator publishes after QA passes.
- Test harness: /tmp/claude-0/-home-user-CPI-Web-Scarping/60ceec26-2c73-59ee-8091-dd0a0c8d8ad5/scratchpad/portal_redesign/harness/.
  Run `node run.js <panel.html> <out dir> [--viewports=1366x900,390x844]`. It loads the page with a window.claude stub backed
  by an in-memory copy of /home/user/CPI-Web-Scarping/data/portal (see lib/portal_db.js).
  Two things about the stub data:
  - It holds CPI row chunks only for the latest N runs (portal_db.js line 98).
  - It synthesizes projects/te/runs from te/days (lines 100-112).
  Copy the harness into pip2/harness before extending it. Never call the real artifact.
- SPPI test data: the BUILDER writes /tmp/claude-0/-home-user-CPI-Web-Scarping/60ceec26-2c73-59ee-8091-dd0a0c8d8ad5/scratchpad/pip2/sppi_sample.json
  in the EXTENDED shape (§9), taken from data/exports/tickets_Nov_2026_weeks_1-3.xlsx and dnata_packages_Nov_2026_weeks_1-3.xlsx
  (weeks 1-3). Load it into the harness db. Map the workbook columns by position, not by header text: the headers carry trailing
  spaces, and the foreign sheet has a stray value at S15. Use scripts/oneoff/dnata/build_month_workbooks.py (DOM_BLOCK, FOR_BLOCK,
  PKG_COL) as the column map. The orchestrator writes the same shape to projects/sppi before publishing.

## 2. Reference screenshots (PIP)
In /tmp/claude-0/-home-user-CPI-Web-Scarping/60ceec26-2c73-59ee-8091-dd0a0c8d8ad5/images/:

| File | Page |
|---|---|
| 31.png | Dashboard KPIs and trend |
| 32.png | Donut and Recent Activity |
| 33.png | Outlet Management |
| 34.png, 20.png | Price History |
| 35.png | Schedules |
| 30.png, 21.png, 22.png, 23.png | Scraper workspace |

Pages not saved as files, described here:
- **Price Logs:**
  - Centered blue title.
  - One white card: a soft-blue pill "N runs" on the left and a square refresh button on the right.
  - Then the list, or the pink error box "Unable to load price log data right now." with a red "!".
- **Years & Months:**
  - Centered title, with "+ Create Year" on the right above the card.
  - The card has a muted "N years" on the left and a refresh button on the right.
  - Then the accordion list.
- **Scraper Management list:**
  - Centered title, with "+ Create scraper" on the right.
  - 4 KPI cards: Total scrapers [chip, blue], Active [check, green], Inactive [ban, red], Target items [hexagon, amber].
  - A filter card: search "Search by label, outlet name, or actor ID", "All scraper types", "All states", refresh.
  - Then the table.

## 3. Look: copy PIP's system, not its brand
- **Light theme.**
  - Page ground #f5f7fb.
  - Navy top band (#1b2a52-ish), about 96px tall, full width, with the title centered in white bold: "Price Collection Platform"
    (Arabic: "منصة جمع الأسعار").
  - Left of the title: a small home button and a project pill (CPI / SPPI / TrendX).
  - On the right, dark rounded buttons: a language toggle that names the other language ("العربية" / "English"), and the
    connection status (dot + "Connected").
- **Type.** Nunito (Latin and digits) and Tajawal (Arabic) from Google Fonts, with fallbacks. Page titles are centered, 800 weight,
  large, primary blue #1a75b8.
- **Cards.** White, radius 18px, 1px #e2e8f0 border, very soft shadow.
- **Controls.**
  - Inputs, selects and buttons have radius 12px.
  - Primary buttons are solid blue with a "+" icon. Secondary buttons are white with a blue border.
  - Icon-square buttons are used for refresh, reset and back.
- **KPI cards.**
  - A 64px tinted icon tile (blue, green, red or amber).
  - A big number, with a muted label under it.
  - A delta chip with a real value ("+601 latest run"), grey "0" when equal, hidden when unknown. Never a caret-only chip.
- **Chips** are pill-shaped and always carry text.
- **Icons.** Inline SVG stroke icons only (stroke 1.75, currentColor). No emoji, no icon fonts.
- **Sidebar** (inside a project), exactly like PIP:
  - A white column of width clamp(280px, 22vw, 370px).
  - Header: a blue square tile with a menu icon, "MAIN NAVIGATION" (small, blue, letter-spaced, uppercase), "Platform pages"
    (bold), and a square collapse button "<".
  - A divider, then 7 items. Each item is a grey 56px rounded icon tile, a label and a ">" chevron.
  - Active item: #e8f2fc fill, blue border, blue tile with a white icon, blue text, `aria-current="page"`.
  - Collapsible to an icon rail that keeps aria-label and tooltips.
  - Below the 7 items, a divider and a muted footer link "Project settings". It is not an 8th item.
- **Must NOT appear anywhere** (QA string check): "Digital Dubai", "Price Intelligence", "PIP Beta", "PIP" as a visible label,
  "Sync from Apify", PIP's logo, a logout button, and PIP's "© 2026 …" footer.
- **Language.**
  - English LTR by default, as in PIP (the user may change the default; see the decision's open question 1).
  - The toggle switches every UI label to Arabic and sets `dir="rtl"` on `<html>`, so the sidebar moves to the right.
  - Mirror the chevrons, the back arrow and the collapse icon. Never mirror charts, sparklines, time axes or code fields (dir=ltr).
  - Latin digits in both languages (`ar-u-nu-latn` for dates), tabular-nums.
  - Data values stay as stored. Arabic names get `dir=auto` per cell.
  - Store the choice in localStorage inside try/catch.
- **Responsive.**
  - Under 900px the sidebar becomes a horizontal scroll strip under the band (icon + short label, the active item scrolled into
    view).
  - KPIs go 2x2, then 1 column at 390px. Filter controls stack full width.
  - Tables and grids scroll inside their card. No page-wide horizontal scroll at 390px.
  - When the Price History grid is shown at 1366px or less, the sidebar auto-collapses to the rail.
- **Accessibility (WCAG 2.1 AA).**
  - A visible 3px focus ring and a skip link to main.
  - Contrast of 4.5:1 or better, including muted text and the disabled Apply. Use `aria-disabled` with readable colors, not the
    pale PIP button.
  - Targets of 44px or larger on mobile.
  - Charts have an aria-label summary and a visually hidden table.
  - Toasts use `aria-live="polite"`.
  - Inline confirms move focus to the confirm button and restore it after.
  - Grids are plain tables with `th scope`.

## 4. Shell, routes, ids
- **Routes** (hash, ASCII):
  - `#home`
  - `#<p>-<page>` with p in {cpi, sppi, trendx} and page in {dashboard, outlets, price-history, schedules, years-months,
    scrapers, price-logs}
  - `#<p>-price-history/commodities`
  - `#<p>-scrapers/new` and `#<p>-scrapers/<map_name>`
  - `#<p>-settings`
  - `#other-projects` (cci, rent; keep their data and code)
  - The internal id `te` maps to the route `trendx`.
  - An unknown route shows the pink box "This page does not exist" with a "Back to Dashboard" button, as PIP's
    "The requested scraper route is invalid." does (30.png).
- **Stable ids for QA.** Prefix by page: `db-`, `ol-`, `ph-`, `sch-`, `ym-`, `sc-` (keep the existing scraper ids), `pl-`, `home-`.
  Examples:
  - `home-card-cpi`
  - `db-kpi-outlets`, `db-trend`, `db-donut`, `db-latest`, `db-activity`
  - `ol-search`, `ol-status`, `ol-state`, `ol-refresh`, `ol-table`
  - `ph-outlet`, `ph-from`, `ph-to`, `ph-reset`, `ph-apply`, `ph-grid`, `ph-commodities`
  - `sch-toggle`, `sch-sync`, `sch-create`
  - `ym-create`, `ym-list`
  - `pl-count`, `pl-refresh`, `pl-list`
  Keep every existing id the current page's code depends on (`ct-*`, `r-*`, `a-*`, `sc-*`, `sched-*`, the basket ids).
- **One-time note.** A dismissible "Where did it go?" note (dismissal kept in localStorage inside try/catch) lists the moves in §11.

## 5. Shared rules (statistics). These decide what every page shows.

### 5.1 Outlet state: one vocabulary, one parser per project
States, always shown with text plus the reason:
- **Read OK**
- **Partial**
- **Blocked**: the site refused our pages. This word means nothing else.
- **Failed**: our side, e.g. the parser raised or a script error.
- **Not read**: no run, or no log line for this outlet.
- **Manual**: SPPI only.

SPPI also shows access modes as separate chips: Auto / PC run / Manual.

**CPI parser.** Use one function, `outletStates(run)`, everywhere: Home, Dashboard, Outlets, Schedules, Price Logs and the
Price History cells.
- It parses the log lines `"<Retailer> barcode: X pages read, Y failed"`.
  - failed share = Y/(X+Y).
  - ≤ 5% gives Read OK; > 5% and < 90% gives Partial; ≥ 90% gives Blocked.
- Category lines (`"<shop> | <cat>: N products from P pages"`) add to the outlet's detail.
- An outlet with no line is Not read.
- Catalogue stores take their state from catalogue/latest: date, and store count > 0.
- Expected on the backup:
  - 27 Oct: Carrefour Read OK (0/363 failed).
  - 28 Oct: Partial (20/363).
  - 29 Oct: Partial (27/363).
  - 30 Oct - 2 Nov: Blocked (363 then 362 refused).
  - Lulu: Read OK in every run.
- "Blocked since": walk back through the runs to the first Blocked run (Carrefour: 30 Oct, 4 runs).

**TrendX parser.**
- Read OK if rows ≥ the enabled basket count (107).
- Partial if 20-106 rows or any basket item is missing ("Partial: N of 107 rows").
- Failed if the run errored or the parser raised ("only N rows").
- Not read if there was no run that day.

**SPPI parser** (per outlet, per week, from that week's observations):
- Read OK if all of the outlet's cells are `ok`.
- Partial if mixed.
- Blocked if all are `blocked`.
- Manual if any `source=manual`.
- Not read if there are no rows.

**Run status chip** (Price Logs, Schedules, Home):
- Completed: every outlet Read OK.
- Partial: at least one outlet is Partial, Blocked or Not read while others read. The text names the outlet and the counts.
- Failed: 0 seen prices, or no outlet read.
- Running.
- Completed with warnings (amber): every outlet Read OK, but the run doc says `status: "error"`. The text shows the first failing
  log line (backup: 15 Oct, 2/373 Carrefour pages failed).

Never take status from the row `status` column alone, or from `projects/*.status = "live"`.

### 5.2 No price for a period it was not seen
- **CPI, carried rows.** In a run where an outlet is Blocked by 5.1, that outlet's rows with `source == "category"` are
  "Blocked (carried)".
  - They are not prices. They are excluded from every KPI, chart, monitor and completeness count.
  - They show as Blocked cells in Price History. They stay in the downloads, unchanged.
  - Backup: Carrefour category rows of 30 Oct, 31 Oct, 1 Nov and 2 Nov, 217 per run. They are identical to 29 Oct
    (data/portal/README.md line 8).
- **Seen prices of a CPI run** = accepted − carried. Compute it from the run doc alone: subtract
  `summary.<retailer>_category.accepted` when that retailer is Blocked.
  - Backup: 2 Nov = 818 − 217 = **601**; all 22 runs = **19,340**.
- **Never fill a day from another day.** The cell states are:
  - Price, with Offer (offer price small) when `price ≠ regular_price`.
  - Blocked: grey hatched, with text.
  - No run: a hatched column (CPI 25 Oct).
  - Not found: "—".
  - Out of stock.
  - Stale quote (TrendX).
  - Incomplete (SPPI total with a missing leg).
  - Substituted (SPPI flag).
  - Not available (SPPI).
- **TrendX.** Show the source's value as published. When `price_date < run_date`, show the cell in grey italic with a clock icon
  and the quote date in the tooltip. Add a "Stale" badge when the quote is more than 7 days old.
- **The price shown is the regular price.** The offer price goes beside it, labelled.

### 5.3 Trend chart: an index, never a mean of raw prices
Use one `LineChart` component. The title and subtitle come from ProjectConfig, and the chart always prints the base and n.
- **CPI.**
  - Title: "Internal price monitor (12 Oct = 100), not the CPI".
  - Method: chained Jevons over item-shop pairs that are seen on both consecutive run days, on `regular_price`, with
    `status = found` and `accepted = yes`. Exclude the carried rows (5.2).
  - Only exact matches count: `source = barcode` (detail barcode_search_match / name_match / barcode_match_unit_label),
    `detail = "catalogue name match"` and `source = name_search`. Product sets (detail product_set, or "catalogue product set …")
    are Tier B and excluded.
  - Use one run per day (the latest finished). Print n pairs per day under the chart.
  - The period chip states the real span ("12 Oct – 2 Nov").
  - It needs row chunks for every run: load lazily, with progress text ("Reading run 7 of 21…"). Cache per session.
- **TrendX.**
  - Title: "TrendX Index (2 Oct 2026 = 100)".
  - Method: chained Jevons keyed on the run date. Use the exclusions from `projects/te.index` when present; otherwise the
    ProjectConfig default `{base:"2026-10-02", exclude_categories:["Index","Electricity"], method:"chained_jevons",
    monthly:"mean_of_daily"}`.
  - A category SegmentedToggle: All / Energy / Agricultural / Industrial / Metals / Livestock. Each category is its own chain.
  - Expected on the backup: 90 series in the index, Oct mean 100.28, 2 Nov 99.39.
  - Show a note: "The public site (build_pages_site.py) still includes Electricity". Fixing that script is a separate task; do not
    edit it.
- **SPPI.**
  - Title: "Weekly price index (week 1 = 100)".
  - Two lines: Tickets and Packages.
  - Method: Jevons over item × outlet cells priced in both weeks. Use status `ok`, no flags, complete totals only. Print n cells.
  - With fewer than 2 weeks, show the empty state "Needs two weeks".

### 5.4 Other shared rules
- **KPIs.** Every KPI equals the count shown on the page it links to.
- **Dates.**
  - Shown in Asia/Dubai.
  - `run_date` is the Dubai day; `startedAt` is UTC.
  - Years & Months counts DAYS. On a day with two runs, the latest finished run counts and the other shows "duplicate".
  - Runs whose id does not end in `-auto` (browser Apify runs, scraping-panel.html line 1539) get the tag "Browser / Apify
    (legacy)" and are excluded from completeness and from the CPI monitor.
- **Downloads** keep today's column sets and order (Dataiku depends on them). New columns go at the end only:
  - CPI: `obs_state` (seen / blocked_carried).
  - TrendX: `price_date`, `collected_dubai`.
- **No item-level official prices or weights** in charts or in the database. The COICOP card (official weights) stays inside a
  collapsed CPI Dashboard card labelled "Internal".
- **TrendX pages** show no CPI basket or official data.
- **Reads.** A CPI run is about 21 row chunks. Never read row chunks on page open except for the latest run. Everything else is
  lazy, per outlet and date range, with progress text.
- **Writes** go only through the existing db helpers, and only on a user action:
  - Create outlet: `projects/<id>/outlets/<code>`.
  - Create Year: `projects/<id>/years/<yyyy>`.
  - The existing basket, scraper and settings writes.
  - The database is near quota: keep new docs tiny, and surface `quota_exceeded` through dbErr.

## 6. Shared components: build once, drive by ProjectConfig
- **Shell:** AppShell; TopBand (home button, title, project pill, LangToggle, ConnStatus); Sidebar (SideHeader, NavItem ×7,
  collapse rail, footer link, mobile strip).
- **Page frame:** PageTitle + PageActions; PageHeadCard (back, centered title, right link).
- **KPIs:** KpiCard (tint, value, label, DeltaChip) and KpiGrid.
- **Filters:** FilterCard (SearchInput, Select, DateInput, PeriodChips for SPPI, IconButton refresh/reset, Apply).
- **Tables:** DataTable (sticky header, sort, paging, expandable rows, inner horizontal scroll, numeric right-align); PriceGrid
  (sticky first column, row groups, sub-rows, multi-value cells, the cell states of 5.2, sparkline column).
- **Chips and states:** StatusChip (vocabulary of 5.1/5.2); CountPill; StateBlock (Loading with text, Empty with
  icon/title/sentence/one action, ErrorBox pink with "!" and Retry); values not loaded show "—", never 0.
- **Controls:** SegmentedToggle; Button (primary, secondary, ghost, danger, icon-square, aria-disabled); Field (label, hint,
  error) + Input, Select, Textarea-code, CheckboxCard, TimeInput; InlineConfirm (never confirm()); SidePanel form.
- **Charts:** LineChart (area, points, y grid, tooltip, hidden table); Donut + Legend (count and %); Sparkline.
- **Lists and cards:** ActivityList (≤ 6 rows, then "View all in Price Logs"); LatestCollectionCard (outlet × source rows: pages
  read/failed, accepted/lines, StatusChip, and for SPPI a stacked status bar with text labels); Accordion; ScheduleCard;
  ProjectCard; LogViewer (monospace, wrapped, copy button); Toast.
- **ProjectConfig** per project: labels (EN/AR), route id, data adapters, outlet-state parser, index function and chart title,
  period mode (days with a 15-day max, or SPPI weeks), column defs, feature flags, and extra schedules (CPI catalogue trigger
  constant).

## 7. Home
- Three equal ProjectCards in a row (one column under 900px). The whole card is one link with a focus ring, to `#<p>-dashboard`.
- Under them, a small muted link "Other projects (2)" to `#other-projects`.
- No footer, or a one-line muted "Internal tool".
- Show skeleton "—" while loading. A figure that fails shows "—" with a tooltip.

**CPI card**
- 1,301 basket lines, counted from the basket chunks.
- Seen prices in the latest run: "601 / 1,089 rows".
- Latest run date: 2 Nov, Dubai.
- Chip from 5.1: amber "Partial: Carrefour blocked since 30 Oct".

**SPPI card**
- Items 46 (18 routes + 28 hotels).
- Weeks collected this month: 3.
- Last collection date: 5 Nov.
- Chip: the open week with its blocked-cell count.
- When meta is absent: "—" and a grey "No data yet" chip.

**TrendX card**
- "107 commodities · 90 in index".
- "99.39 · 2 Oct 2026 = 100".
- Two lines: "Collected 2 Nov 03:09 Dubai" and "Latest quote 30 Oct" (max price_date).
- Chip: green if 107/107; amber if fewer rows or no run today; red if failed.

## 8. The 7 pages: shared skeleton and data per project
CPI data paths:
- `projects/cpi` doc.
- `projects/cpi/runs/<id>` and `/rows/cNNN`.
- `projects/cpi/basket/cNNN`.
- `projects/cpi/pins/current`.
- `projects/cpi/catalogue/latest`.
- `projects/cpi/products/latest`.
- `scrapers` where project == "cpi".
- `system/scrapers_routine`.

Never read barcodeCount/specCount/serviceCount from `projects/cpi` (stale: 384/253/114). Compute from the basket:
barcode 363, spec 274, name 550, service 112, market 2.

TrendX data: `projects/te`, `projects/te/runs/*` + rows, `projects/te/basket`, scrapers where project == "te". SPPI data: §9.

### 8.1 Dashboard (31.png, 32.png; no page title, as in PIP)
Layout, top to bottom:
1. KPI grid (2×2; 4 across at 1600px and wider).
2. Trend card (5.3).
3. LatestCollectionCard.
4. Donut card.
5. Recent Activity.

| | CPI | SPPI | TrendX |
|---|---|---|---|
| Total Outlets | 6 (Outlets rows) | 11 | 1 |
| Commodities Tracked | 1,301; sub "N priced in latest run" | 46; sub "18 routes · 28 hotels" | 107; sub "90 in index" |
| Price Records | 19,340 seen in all runs; delta "+601 latest run" | priced cells in all weeks; delta = latest week | 3,317; delta "+107 latest run" |
| Active Scrapers | active rows on the CPI Scrapers page (routine collectors + active custom scrapers) | active rows on the SPPI Scrapers page (0 is fine once loaded) | 1 |
| Trend | CPI monitor (5.3) | weekly index (5.3) | TrendX index + category toggle (5.3) |
| Latest collection | latest run: Carrefour barcode, Carrefour category, Lulu barcode, Lulu category, catalogue, name search (from summary + log) | latest week: outlet × survey with a stacked status bar | latest run: Trading Economics, rows/107, method, missing items |
| Donut (composition) | basket by COICOP division (8 divisions, `division_name`; top 6 + Other), with a toggle [Group \| Method] | items: domestic routes / foreign routes / hotels by city | commodities by 7 categories; Electricity and Index greyed "not in index" |
| Recent Activity | per run: one line per source from log (green ok, amber partial/blocked, red failed) + custom scraper last_run | per week × survey: collected, priced/expected, blocked outlets | run done/rows, missing day 7 Oct, stale quotes > 7 days |
| Extra | collapsed card "Index by group (COICOP 2018) · Internal": the existing ct-* tree with its store and weights selects and Excel | — | note on build_pages_site.py |

### 8.2 Outlets (33.png)
Layout:
- Title "Outlet Management", then "+ Create outlet" on the right.
- 4 KPIs: Total, Working (Read OK), Failed (Blocked + Failed), Required items.
- FilterCard: search "Search by code, English name, or Arabic name", "All statuses", "All working states", refresh.
- DataTable with columns: Code, English name, Arabic name, Status (Active/Inactive), Working state (5.1, with "since"),
  Prices in latest run, Last price seen, Last read.
- Row click opens a SidePanel with the outlet's latest log lines.
- "+ Create outlet" opens a SidePanel form (code, EN name, AR name, kind, status) with the note "Adds the outlet to this list; it
  does not start scraping". It saves to `projects/<id>/outlets/<code>`; saved outlets merge into the list.
- States: "Loading outlets…", Empty, Error.

| | CPI | SPPI | TrendX |
|---|---|---|---|
| Rows | carrefour, lulu, sharafdg, zara, max, centrepoint (child rows Splash, Babyshop, Shoexpress, Shoe Mart, Centrepoint, not counted again) | meta.outlets (11: flydubai, Emirates, Saudia, EgyptAir, Royal Jordanian, PIA, British Airways, Air India, Turkish, dnata, Emirates Holidays) | Trading Economics (TE) |
| Extra columns | sources (daily barcode/category, catalogue) | kind, market, access (Auto / PC run / Manual), a week selector for the state | fetch method, missing basket items |
| Required items | basket lines served by this outlet (barcode lines 363 for Carrefour and Lulu; catalogue lines per store) | meta.sample assignments for the outlet | 107 |
| Backup check | Carrefour "Blocked since 30 Oct"; Lulu "Read OK" | PIA Read OK in W1 and W2, Blocked in W3 | Read OK, 107 |

### 8.3 Price History (34.png, 20.png)
**PageHeadCard:** a square back button, a centered "Price History", and on the right a "Commodities ☰" link to
`#<p>-price-history/commodities`.

**Filter row:**
- Labels in blue bold.
- Outlet select, Date From and Date To.
- A square reset button.
- "Apply Filter" with a funnel icon. It stays aria-disabled until valid, with aria-describedby pointing to the hint
  "Maximum date range is 15 days".
- Default dates: the last 7 days that have data.

**Empty state:** a pulse icon, "Select an outlet to begin", and "Choose a retail outlet from the dropdown above to view the price
history grid."

**After Apply:** a PriceGrid with:
- a sticky first column (code, name, unit, method tag);
- one column per day, with a sticky header showing the date and weekday;
- a sparkline column;
- Excel and CSV buttons that download exactly the grid shown (reuse offerXlsx/offerFile).

| | CPI | SPPI | TrendX |
|---|---|---|---|
| Period control | days, 15-day maximum | Survey select (Tickets domestic / Tickets foreign / Packages) + Month + week chips; Outlet defaults to "All outlets", so Apply is enabled; hint "Weeks of the selected month" | days, 15-day maximum; Outlet preselected, so Apply is enabled |
| Rows | basket lines grouped by COICOP group (collapsible), 50 per page, search box; method tag from `basket.match_mode`; Tier B rows muted with "Not index-grade" | tickets: route › out / back / total sub-rows, with outlet columns as in the template; packages: hotels grouped by city (EN + AR) | 107 commodities (category, name, unit with currency); filters: category, search |
| Cell | regular price large, offer price small + "Offer"; a mark only if the row's source differs from its method; Blocked (carried) / No run (25 Oct) / Not found / Out of stock | lowest / highest / price stacked; totals by the template rule (total low = out + back; high falls back to low per leg; price = average of the totals). A missing leg gives "Incomplete", never one leg. Flags: Substituted (yellow, with note), Blocked, Not available; tooltip with note, flight numbers, matched hotel | close; Stale quote styling + price_date tooltip; % change over the range per row |
| Column header | date + weekday | week label + ticket window + package window + collected_on | date + weekday |
| Extra | load row chunks lazily for the chosen outlet and range ("Reading 7 of 15 days…") | — | second tab "Index": daily All + 5 categories, level and % change, Excel |
| Commodities ☰ | the existing basket editor, complete (renderBasket, search, group select, add/edit, save via saveChunks, CSV import/export, paging); catalogue browser and product photos; pins table read-only (`<item>\|<shop>`: title, URL, unit price, since, last, miss) with a "pending registry" note | read-only list of routes and hotels (meta.items) and the fixed sample (meta.sample) | the existing TrendX basket editor + gcSpark/gcToggle commodity detail + a read-only "in index" column (off for Electricity and Index) |

### 8.4 Schedules (35.png)
- Title, then a SegmentedToggle [By Schedule | By Outlet] on the left.
- On the right: a secondary "Sync schedules" (re-reads docs and get_trigger) and a primary "+ Create Schedule".
- "+ Create Schedule" opens an inline panel: "Schedules are created by asking Claude", plus the fields needed (name, time, days,
  outlet). Never a dead button.
- ScheduleCard shows:
  - name;
  - Dubai time parsed from the cron;
  - an Enabled/Paused chip;
  - next run;
  - last run with the run status chip (5.1) and seen/lines;
  - linked outlets.
- ScheduleCard actions, through the existing renderSchedule / update_trigger / fire_trigger code paths:
  - a time input + "Save time";
  - an enable switch;
  - "Run now" with InlineConfirm.
- States: "Reading schedules…"; schedFail() text in the pink box; outside claude.ai: "Schedules need this page opened in
  claude.ai".

| | CPI | SPPI | TrendX |
|---|---|---|---|
| Cards | "CPI daily scrape" (projects/cpi.schedule, trig_018GydPXyp4MkLmnMj8dAoqY, 06:47); "Catalogue crawl" (ProjectConfig constant trig_01BKPxvQYZr2sCFEWDEJ9LGk, 06:52, read with get_trigger); "Custom scrapers" (system/scrapers_routine, mode on_demand: no time, "Runs from Scrapers › Run now") | none. Empty state "No automated SPPI schedule yet", then a read-only table: outlet → run mode (Cloud script / PC run, showing the command, e.g. `run_ek_windows.cmd` for Emirates / Manual) and collected_on per week. No Run now | "TrendX daily close capture" (projects/te.schedule, trig_01FWxfp4cQQtbe3CJxqw9EH4, 03:00 Dubai), with steps text: collect_te.py, Commodity Price Log, projects/te run, Excel email |
| Extra | "Run now (server, Scrapling)" quick run; below it a collapsed "Legacy: Apify run (not part of the daily CPI method)" holding today's whole Run tab (actor picks, groups, codes, start/stop, progress, log) | — | — |
| By Outlet | Carrefour: daily + catalogue; Lulu: daily + catalogue; the other stores: catalogue | outlets grouped by run mode | Trading Economics: daily |

### 8.5 Years & Months
- Title, then "+ Create Year" on the right. "+ Create Year" opens an inline yyyy form that writes `projects/<id>/years/<yyyy>`.
- A card with "N years" and refresh.
- An Accordion of years, then months.
- Years are derived from run dates, so the page works with no year docs.
- No "Lock month" and no "comparison month" in v1.

| | CPI | SPPI | TrendX |
|---|---|---|---|
| Month row | days collected / days in period (Oct: 19 of 20, from 12 Oct; missing 25 Oct; 2 runs on 14 Oct, one marked duplicate), runs (20), seen prices, blocked days per outlet (Carrefour Oct: 30, 31), status Open / Complete / Partial, a day strip (green read, amber partial/blocked, grey no run) | weeks inside the month: ticket window, package window, collected_on, cells priced / expected per survey, blocked, status Open / Complete | days / expected (Oct 29 of 30 from 2 Oct, 7 Oct missing), runs, records, stale-quote count, monthly index (Oct 100.28) + 5 category means, status Open "provisional, n days" / Complete / Complete with gaps |
| Actions | "Check completeness": on demand, reads the month's row chunks with progress text and applies the half-month rule (≥ 1 observation in days 1-15 and in 16-end; fresh items need a span > 7 days; non-fresh items seen on fewer than 3 days are low-coverage), then shows usable / missing / low-coverage counts. "Download month for Dataiku": all rows of the month's runs with the existing column set (r-export-all helper) | "Office workbooks": download links when `meta.files` lists uploaded assets, otherwise hidden | "Monthly report (Excel)": 4 sheets built in the browser from the shared index: Monthly (commodity × monthly mean, % change), Daily index (All + categories), All Days prices (run_date and price_date), Notes (method, base, exclusions, missing days) |
| m/m | not shown in v1 | not shown in v1 | Nov vs Oct monthly index once Nov is Complete; otherwise "Not comparable yet: provisional" |

### 8.6 Scrapers (list as described; workspace 30.png, 21-23.png)
**List:**
- Title "Scraper Management", then "+ Create scraper" on the right.
- 4 KPIs.
- FilterCard: search, types, states, refresh.
- DataTable: label, outlet, type, status chip, last run (status + items + relative time), actions (Run now, Edit, Duplicate,
  Delete with InlineConfirm).
- A SegmentedToggle at the top: [Scrapers | Apify actors]. The second view hosts today's project Actors tab (a-list, a-add, a-save).
- Filter by `scraper.project`.
- Keep every existing scraper function: scGo routes, validation, JS syntax check, the leave-without-saving confirm, Apify and
  Scrapling run_request, the runs/rows view, Excel.

**Workspace:**
- Top card: the pill "SCRAPER MANAGEMENT", a large title "Scraper workspace", a subtitle, "Back to scrapers" (blue) and
  "Save changes" (pale until dirty).
- A pink banner for errors.
- Left column cards:
  - Identity: Outlet, Label, Scraper Type, Apify Actor ID.
  - Playwright Configuration: browser, wait until, link selector, unique map name.
  - Scripts & URLs, in monospace.
  - Behavior: Target Items, and an "Active" CheckboxCard.
  - Auto Trigger.
  - Payload.
- Right column: a sticky "Operations" card (Status, Auto Trigger, time, TZ, Last Scraped, Last Run, Created At).
- One column under 1100px.
- Auto Trigger: keep the section, shown off and disabled, with the note "Scrapers run on demand (Run now)"
  (docs/routines/custom_scrapers.md lines 4-6).

| | CPI | SPPI | TrendX |
|---|---|---|---|
| Read-only rows (type "Routine") | Carrefour barcode, Carrefour category, Lulu barcode, Lulu category, Catalogue stores, Name search, each with pages read/failed from the latest run log | `meta.collectors` if present (outlet, survey, script, run location), with the method rules as text (economy, 1 adult, direct own-carrier, cheapest fare, next day if none, B&B else cheapest, 4 nights); otherwise an empty state | Trading Economics: routine direct fetch, apify/web-fetch fallback, parser te_commodities, 107 target items, note "parser fails below 20 rows" |
| Custom scrapers | scrapers where project == "cpi" | where project == "sppi" | where project == "te" |

### 8.7 Price Logs (described)
- Title.
- A card with a CountPill "N runs" and refresh.
- A list, latest first. Each row shows: date and time (Dubai), duration, run status chip (5.1), seen / lines, per-source summary
  chips, and tags ("Browser / Apify (legacy)").
- Expanding a row shows the LogViewer, then "Open rows": the existing r-* viewer (loadRuns / showRun / drawRun: search, filters
  for outlet / source / status / group, Excel, delete run with InlineConfirm).
- Header action "Download all prices (Excel)": the existing r-export-all, Dataiku layout unchanged plus `obs_state` at the end.
- Error: the PIP pink box "Unable to load price log data right now." + Retry.
- Empty: "No runs yet" + a link to Schedules.

| | CPI | SPPI | TrendX |
|---|---|---|---|
| Entries | projects/cpi/runs (22 on the backup) | one per week × survey (from observations; `projects/sppi/runs` if present): collected_on, source, priced / expected, blocked list with reasons | projects/te/runs, with method, rows/107 |
| Notes / checks | a data note on 30 Oct – 2 Nov: "Carrefour category rows carried forward, shown as Blocked, excluded from all figures" | — | per run: rows < 107 or missing items; quotes > 7 days old |

## 9. SPPI data shape (EXTENDED; the pages also tolerate the draft's minimal shape)

### projects/sppi/meta
```
{ name, description,
  weeks:   [{ id:"2026-11-W1", month:"2026-11", n:1, label_en, label_ar,
              tickets:{ out:"2026-11-01", back:"2026-11-06" },
              packages:{ checkin:"2026-11-01", checkout:"2026-11-05", nights:4 },
              collected_on:"2026-10-22", status:"open"|"complete" }],
  outlets: [{ code, name_en, name_ar, kind:"airline"|"travel_agent"|"tour_operator",
              market:"domestic"|"foreign"|null, url, access:"auto"|"pc_only"|"manual", status:"active" }],
  items:   [{ code, kind:"route"|"hotel", market, name_en, name_ar, city, country, stars, board_rule, sort }],
  sample:  [{ survey:"tickets"|"packages", outlet, item, legs:["out","back"]|["package"], since }],
  collectors: [{ code, outlet, survey, script, run_location:"cloud"|"pc"|"manual" }],   // optional
  files:   [{ label, asset }] }                                                          // optional, office workbooks
```

### projects/sppi/observations/<weekId>
```
{ rows:[{ week, survey:"tickets"|"packages", outlet, item, leg:"out"|"back"|"package",
          lowest, highest, price, currency:"AED",
          status:"ok"|"partial"|"blocked"|"not_available"|"to_review",
          flags:["next_day","other_hotel","no_bb","plus_one_day","transfer_incl"],
          date_used, matched_name, flights:[{no, dep, fare}], note,
          source:"scraped"|"manual", entered_by, entered_at }] }
```

Rules for this shape:
- Store legs only. Totals are computed in the page (8.3).
- Minimal shape: a row without `status` but with a price counts as `ok`. `kind` stands for `survey`. `{week, label, from, to}`
  weeks give one window for both surveys.
- Week windows on the backup:

  | Week | Tickets | Packages | Collected on |
  |---|---|---|---|
  | W1 | out 1 / back 6 Nov | 1-5 Nov | 22 Oct |
  | W2 | 6 / 13 Nov | 6-10 Nov | 29 Oct |
  | W3 | 13 / 20 Nov | 13-17 Nov | 5 Nov |

- Items: 11 domestic routes (flydubai, Emirates), 7 foreign routes (one national carrier each), 28 hotels in 10 cities (dnata,
  Emirates Holidays).
- Known cases the sample must keep:
  - BA London: outbound lowest only in W1-W3 (3,855 / 1,725 / 1,325), giving "Incomplete".
  - Riyadh flydubai W3: 2,745 / 2,807 against 530-855 before, giving `to_review`.
  - PIA blocked in W3 only.
  - EgyptAir blocked in W2.

## 10. Features moved, nothing removed
| Today (scraping-panel.html) | Goes to |
|---|---|
| Home project list (`view-home`) | Home (3 cards) + Other projects |
| Overview tab, incl. COICOP tree (ct-*) | Dashboard (CPI collapsed "Internal" card) |
| Run tab, schedule (sched-*), Apify run | Schedules (CPI: quick run + collapsed Legacy Apify) |
| Basket tab, catalogue browser, product photos, TrendX commodity list (gcSpark/gcToggle) | Price History › Commodities ☰ |
| Actors tab (a-*) | Scrapers › Apify actors |
| Results tab (r-*), Excel/Dataiku exports, globalSheet | Price Logs (+ Price History grid exports) |
| Project settings tab, delete project | Sidebar footer "Project settings" (`#<p>-settings`) |
| Custom scrapers view (`view-scrapers`, sc-*) | Scrapers list + workspace |

## 11. Out of scope for v1 (do not build; no dead buttons for them)
- **SPPI:** screenshot upload/lightbox (manual entry IS in v1, see §14), review queue, Lock month, browser-built office workbooks, scheduling.
- **CPI:** official match rate and the locked comparison month (permanently out, §14.5), month close, product registry (pin approval, substitutes), alerts,
  imputation share.
- **TrendX:** emailed report, month-average lines on the chart, top movers, structure-change alerts, the build_pages_site.py fix.
- **All:** donut click-through, run compare, per-outlet history strip, creating or deleting triggers from the page.

## 12. Page contract and rules (unchanged)
- No external hosts except Google Fonts and pinned cdnjs scripts (exact versions).
- No alert/confirm/prompt.
- Database writes only through the existing helpers.
- No localStorage for shared state; localStorage only for language, collapsed sidebar and dismissed notes, each inside try/catch.
- Stable ids on every control. Keyboard focus visible. No console errors.
- Keep every existing read/write path.

When done, write /tmp/claude-0/-home-user-CPI-Web-Scarping/60ceec26-2c73-59ee-8091-dd0a0c8d8ad5/scratchpad/pip2/builder_notes.md
covering: structure, routes, ids, the data mapping per page per project, what moved where, the numbers seen in the harness for
each check in §13, and known gaps.

## 13. Acceptance checks for QA (harness, viewports 1366×900 and 390×844, EN and AR)

### Shell
1. Home shows exactly 3 project cards (`home-card-cpi`, `home-card-sppi`, `home-card-trendx`) and an "Other projects" link. No
   card shows 0 while loading.
2. Each project route shows the band, the project pill, and the sidebar with 7 items in PIP order. The active item has
   `aria-current="page"`. "Project settings" sits in the footer. There is no 8th nav item.
3. The 21 routes `#<p>-<page>` render without console errors. An unknown route shows the pink "does not exist" box.
4. The string check fails on "Digital Dubai", "Price Intelligence", "PIP Beta", visible "PIP", "Sync from Apify", and any logout
   control.
5. The language toggle flips `dir` and moves the sidebar to the right. Chevrons are mirrored and charts are not. Digits stay
   Latin. The choice survives a reload, and the page works when localStorage throws.
6. No page-wide horizontal scroll at 390px. The sidebar is a strip under 900px.

### CPI numbers (backup)
7. Home CPI: 1,301 lines; "601 / 1,089"; 2 Nov; amber chip naming Carrefour. The figure 818 must NOT appear as seen prices.
8. Dashboard KPIs: outlets 6, commodities 1,301, price records 19,340 with delta +601. The donut Method toggle shows 363 / 274 /
   550 / 112 / 2.
9. outletStates:
   - 27 Oct Carrefour Read OK.
   - 28 Oct Partial (20/363).
   - 29 Oct Partial (27/363).
   - 30 Oct – 2 Nov Blocked.
   - Outlets page: "Blocked since 30 Oct".
   - Lulu: Read OK.
10. Price Logs:
    - 22 runs.
    - Every run from 12 Oct to 27 Oct with status "done" shows Completed.
    - 14 Oct 06:00 shows Partial (Carrefour 43/384).
    - 15 Oct shows "Completed with warnings".
    - 28 and 29 Oct show Partial.
    - 2 Nov shows "Partial: Carrefour blocked (362 pages refused)".
    - The data note is present on 30 Oct – 2 Nov.
11. Price History, Carrefour, 29 Oct – 2 Nov:
    - Carrefour category cells for 30 Oct – 2 Nov are "Blocked", not prices.
    - 25 Oct is a "No run" column when the range covers it.
    - Apply is aria-disabled until an outlet is chosen, with contrast ≥ 4.5:1.
    - The range is capped at 15 days.
12. CPI monitor: the title contains "not the CPI", the series starts at 100 on 12 Oct, n pairs are shown, and no point uses
    Carrefour rows from 30 Oct onward.
13. Years & Months, Oct: "19 of 20 days", 25 Oct missing, 14 Oct duplicate flagged, Carrefour blocked days listed. "Check
    completeness" runs only on click.
14. Commodities ☰: the basket editor loads 1,301 lines. Pins (463) are read-only. Basket CSV export works.
15. Schedules: 3 CPI cards (daily, catalogue, custom on demand). Run now asks inline before firing. The Legacy Apify section is
    collapsed.

### TrendX numbers (backup)
16. Home: "107 · 90 in index", "99.39", two date lines.
17. Index: Oct mean 100.28, 2 Nov 99.39; Electricity and Index are excluded; the category toggle changes the line.
18. Price History: the outlet is preselected and Apply is enabled. A Tea cell on 2 Nov shows Stale with quote date 3 Oct.
19. Years & Months: "29 of 30", 7 Oct missing, Oct 100.28. "Monthly report (Excel)" downloads 4 sheets with price_date and
    run_date.

### SPPI (sample in the extended shape)
20. With no projects/sppi: every SPPI page shows "—" / "No data yet", no errors, no zeros.
21. With the sample:
    - 11 outlets including Emirates Holidays.
    - PIA Read OK in W1/W2 and Blocked in W3.
    - The BA London total shows "Incomplete".
    - Riyadh flydubai W3 shows "To review".
    - The week headers show both windows and collected_on.
    - Schedules shows "No automated SPPI schedule yet" and no Run now.

### Shared
22. KPI equals list: each Dashboard KPI equals the count on its linked page, for all 3 projects.
23. Every chip carries text. Every loading state has text. Every error uses the pink box with Retry. No confirm(), alert() or
    prompt(). No dead buttons: "+ Create Schedule" and the disabled Auto Trigger explain themselves.
24. Downloads: the CPI Excel columns equal today's set in today's order, with only `obs_state` appended. TrendX appends
    price_date and collected_dubai.
25. No database write happens on page load. Writes happen only on Create outlet, Create Year, basket save, scraper save/delete,
    and settings.

## 14. The user's answers (5 Nov). These OVERRIDE anything above that disagrees.
The user answered the council's 6 questions (decision_ar.md "أسئلة لك"):

1. **Language: English by default, like PIP.** First load = English, `dir="ltr"`, sidebar on the left. The AR toggle stays
   (§13 check 5). The stored choice (localStorage, try/catch) wins over the default.

2. **SPPI published figure: deferred. The user maintains the SPPI basket by hand in the portal.** So:
   - No SPPI index / weekly figure in v1. SPPI pages show prices only (legs and the page-computed totals of §8.3).
   - NEW in v1: **SPPI basket editor** under SPPI › Price History › Commodities ☰ (same place as the CPI basket editor).
     It lists `meta.items`, `meta.outlets` and `meta.sample` in three tabs and lets the user add, edit and retire rows
     (retire = `status:"retired"` / `until:<date>`, never a hard delete of an item that has observations). Required fields:
     item {code, kind route|hotel, market, name_en, name_ar, city, country}; outlet {code, name_en, kind, market, access};
     sample {survey, outlet, item, legs}. Codes are unique; validation errors show inline. Save writes `projects/sppi/meta`
     through the existing db helper with the read version (`if_version`); on a version conflict show the pink box with
     "Reload and retry", never overwrite.
   - With no projects/sppi at all, the editor offers "Start SPPI basket" which creates an empty meta (only on click).

3. **Manual-entry card: YES, build it in v1** (remove "manual entry" from §11). For outlets the scrapers cannot read
   (blocked, pc_only, manual: e.g. Emirates, Air India, Turkish, Emirates Holidays, PIA when blocked):
   - SPPI: on Price History (and from a "Blocked"/"Not read" cell) a card "Add price manually": period, survey, outlet,
     item, leg, lowest, highest (optional), price, flags, note, date seen. Saves one row with `source:"manual"`,
     `entered_by` (viewer name if the runtime gives one, else "manual"), `entered_at` (ISO) into
     `projects/sppi/observations/<periodId>` (read-modify-write with if_version; conflict → pink box, no overwrite).
     The grid then shows the cell with a "Manual" chip (state vocabulary §5.1 already has Manual). A manual row can be
     edited or withdrawn by its card; withdrawn = `status:"withdrawn"`, kept in the doc, not shown as a price.
   - Screenshot is OPTIONAL (not required to accept the cell); v1 has no upload field — a "screenshot ref / URL" text field only.
   - CPI: the same card on CPI Price History for a Blocked outlet cell, saving to `projects/cpi/manual/<YYYY-MM-DD>`
     `{rows:[{line_code, outlet, price, regular_price, unit, url, note, entered_by, entered_at, source:"manual"}]}`.
     Manual CPI prices show with the "Manual" chip and are NOT mixed into the CPI monitor series (§5.3) in v1.
   - Validation: price > 0, numeric, AED; no default value is ever prefilled from another day (no carry-forward).
   - Writes happen only on the card's Save (add these to check 25's allowed writes).

4. **TrendX base: keep 2 Oct 2026 = 100 (it stands for September).** October = mean of 2-31 Oct. No change to §13 checks
   16-19. The "drop ratios whose price date did not change" question was not answered: keep today's behaviour (Stale shown).

5. **Only prices are shown. No official weights, no official prices, no match-rate store.**
   - Remove the COICOP weights from every page. The COICOP tree may stay as a category browser (codes, names, line counts)
     with NO weight column, NO weight bars, NO "official" figures. Check: the strings "weight", "وزن", "الوزن" do not appear
     next to any COICOP number on any page; no number from the official basket weights file appears.
   - No official-price comparison or match-rate panel anywhere (stays out of scope permanently, not "later").

6. **SPPI collection is MONTHLY; the collection timing of some items is still to be determined.**
   - Periods are months: `meta.periods:[{id:"2026-11", month:"2026-11", label_en, label_ar, status}]`. The November
     sample keeps its three collections as sub-windows inside the month: `meta.weeks` stays readable, each week is a
     "collection" of period 2026-11 (W1/W2/W3 shown as "Collection 1/2/3" with both travel windows and collected_on).
     Observations stay keyed by collection id (`2026-11-W1`…); a new month with one collection uses id `2026-12-C1`.
   - Per-item timing: `meta.items[].collection` = `{frequency:"monthly", lead_days:null, note:"to be determined"}`.
     Show "Timing: to be determined" where it is null. Do NOT hard-code a lead-days rule (drop the 8-days idea).
   - Years & Months for SPPI: one row per month, expanding to its collections.
   - Schedules for SPPI: still "No automated SPPI schedule yet" (no Run now), plus the text "Collected monthly; timing
     per item to be determined".

Acceptance additions (QA, same viewports, EN and AR):
26. First load with empty localStorage is English/LTR; the toggle to AR survives a reload.
27. SPPI basket editor: loads 46 items (11+7 routes, 28 hotels) and 11 outlets from the sample; add a test item → Save
    writes projects/sppi/meta once with if_version; a duplicate code is refused inline; a stub version conflict shows the
    pink box and does not overwrite.
28. Manual card SPPI: add a price for PIA Karachi W3 out → the cell shows the price with a "Manual" chip; the doc has
    source:"manual", entered_at; withdraw → the cell returns to "Blocked". Nothing is written on page load.
29. Manual card CPI: on a Carrefour Blocked cell (30 Oct – 2 Nov) save a price → stored under projects/cpi/manual/<date>,
    shown with "Manual"; the CPI monitor values are unchanged.
30. No weights: string/number check per item 5 passes on all CPI pages.
31. SPPI Years & Months shows "Nov 2026" with 3 collections; items show "Timing: to be determined".
