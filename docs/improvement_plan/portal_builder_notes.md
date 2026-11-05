# Builder notes: portal rebuild (PIP-style, 3 projects)

Brief: ../council3/build_brief.md (§14 overrides). Working copy: `scraping-panel.html` (GENERATED; 5,184 lines, ~525 kB).
Status: all pages of §8 for CPI, SPPI and TrendX plus §14 implemented. Harness: all 32 routes clean (no console/page errors,
no overflow, no writes on load) at 1366x900 and 390x844, in EN, in AR (`--lang=ar`), and without SPPI data.

## Build
- Source parts live in `src/`; `node build.js` concatenates them (sorted by name) into `scraping-panel.html`.
  Never edit scraping-panel.html by hand: edit src/ and rebuild. `orig/source.html` = untouched copy of the source page.
  - `00_style.html`  title, Google Fonts link (Nunito + Tajawal), all CSS (tokens, band, sidebar/rail/strip, cards, KPIs, grid cells)
  - `10_markup.html` shell (skip link, band, sidebar, #main/#page, side panel root) + hidden `#hold` with the legacy blocks
    (ids kept: blk-basket, blk-actors, r-export-all, r-list/r-view, quick, apify-run, blk-settings, blk-sc-ws) + dialog + toast
  - `20_core.js`     original toast, parsers, matchers, Apify helpers, db helpers (saveChunks, dbErr, plain…), strings via L(en, ar)
  - `21_icons.js`    inline SVG stroke icon set
  - `22_ovlegacy.js` original latestBySource/dubaiDay/drawGlobalRows/gcSpark/gcToggle (TrendX commodity list)
  - `30_legacy.js`   original run/basket/actors/results/settings/schedule/quick/export/Excel/COICOP (weights removed)
  - `35_scrapers.js` original scrapers code, routed per project (scProj)
  - `40_base.js`     formatting, KPI/chip builders, per-project caches S[pid], CPI outletStates (cpiLogStates), runStatus,
                     cpiSeen/cpiCarried/annotateRows, TrendX index (teIndex/teMonthly), SPPI loader (sppiLoad, sppiCell, sppiTotal)
  - `41_ui.js`       lineChart / donutChart / sparkline / segToggle / stackBar / side panel / "Where did it go?" note
  - `42_shell.js`    language (applyStatic/setLang), band, sidebar (collapse rail, strip <900px), router, headCard/titleRow
  - `43_home.js`     Home (3 ProjectCards + Other projects), pgOthers, pgOther (cci, rent: basket + settings)
  - `44_data.js`     outletRows(pid), routineRows(pid), outletOptions, activeScraperCount
  - `45_dashboard.js` 3 dashboards
  - `46_outlets.js`  Outlet Management + Create outlet side panel
  - `47_history.js`  Price History frame, CPI + TrendX grid, CPI manual card
  - `48_sppi_history.js` SPPI grid + SPPI manual card
  - `49_commodities.js` Commodities ☰ (CPI/TrendX basket editor mount, catalogue, pins read-only; SPPI basket editor)
  - `50_stubs.js`    `let viewer`
  - `51_schedules.js`, `52_logs.js`, `53_years.js`, `54_scrapers_page.js` (Scrapers list frame + settings page)
  - `59_boot.js`     boot (lang from localStorage else EN, db/mcp/downloads/user, loadProjects, scLoad, route)

## Routes (hash)
`#home`, `#<p>-<page>` with p ∈ {cpi, sppi, trendx} (internal id `te` ↔ route `trendx`) and page ∈ {dashboard, outlets,
price-history, schedules, years-months, scrapers, price-logs}; `#<p>-price-history/commodities`; `#<p>-scrapers/new`,
`#<p>-scrapers/<map_name>`; `#<p>-settings`; `#other-projects`, `#other-<id>` (cci, rent). Old addresses redirect
(`#cpi`, `#te`, `#scrapers`, `#scraper-<id>`). Unknown → pink box "This page does not exist" + Back button (#unknown-route).

## Stable ids (QA)
- Shell: #band-proj, #lang-toggle, #conn, #side, #side-nav (.nav-item ×7, aria-current), #side-toggle, #side-settings, #skip-link,
  #where-note/#where-close.
- Home: home-card-cpi / home-card-sppi / home-card-trendx; other links home-card-<id> on #other-projects.
- Dashboard: db-kpi-outlets, db-kpi-commodities, db-kpi-records, db-kpi-scrapers, db-trend(-h/-chip/-body), db-monitor-load,
  db-monitor-prog, db-te-cat, db-latest, db-donut (db-donut-mode Group|Method), db-activity, db-internal (collapsed COICOP
  browser, ct-* ids), db-te-note.
- Outlets: ol-create, ol-kpi-{total,working,failed,required}, ol-search, ol-status, ol-state, ol-week (SPPI), ol-refresh, ol-table.
- Price History: ph-back, ph-outlet, ph-from, ph-to, ph-reset, ph-apply (aria-disabled + aria-describedby ph-hint), ph-grid,
  ph-commodities, ph-xlsx, ph-csv; SPPI: ph-survey, ph-month, ph-weeks, ph-manual; manual cards: CPI mc-* (form mc-form, mc-price,
  mc-save, mc-withdraw), SPPI sm-* (sm-form, sm-week, sm-survey, sm-outlet, sm-item, sm-leg, sm-low, sm-high, sm-price, sm-save,
  sm-withdraw). Grid cells that open the card: CPI `[data-man="<code>|<day>"]`, SPPI `[data-sman="<wid>|<outlet>|<item>|<leg>"]`.
- Commodities: legacy basket ids (b-*), cm-pins; SPPI editor sp-editor, sp-card, sp-tab (items/outlets/sample), sp-search, sp-add,
  sp-save (aria-disabled until dirty), sp-state, sp-box (errors/conflict), sp-form/spf-* fields, sp-start (no meta).
- Schedules: sch-toggle, sch-sync, sch-create (+ inline request form), legacy sched-*, quick, btn-quick, apify-run (collapsed).
- Years & Months: ym-create, ym-count, ym-refresh, ym-list; data-check / data-dl / data-te-report buttons per month.
- Scrapers: sc-new, sc-view (Scrapers | Apify actors), sc-k-{total,active,inactive,target} (value spans inside
  sc-k-*-card), sc-q, sc-filter, sc-state, sc-refresh, sc-count, sc-table/sc-list, sc-actors-view (mounts blk-actors: a-list,
  a-add, a-save); workspace: all original sc-* ids + sc-save-top, sc-banner.
- Price Logs: pl-count, pl-refresh, pl-list; legacy r-export-all, r-view etc.
- Settings: blk-settings (s-name, s-kind, s-desc, s-cols, s-listkey, s-save, s-delete with inline confirm).

## What moved where (§10)
view-home → Home + Other projects; Overview + COICOP → Dashboard (CPI collapsed "Internal" card, no weights); Run tab, schedule,
Apify run → Schedules (CPI quick run + collapsed "Legacy: Apify run"); Basket, catalogue browser, photos, TrendX commodity list →
Price History › Commodities ☰; Actors → Scrapers › Apify actors; Results + Excel/Dataiku → Price Logs (+ grid exports);
Project settings / delete → sidebar footer `#<p>-settings`; view-scrapers → Scrapers list + workspace.

## Data mapping per page per project (summary)
- CPI: projects/cpi, runs/<id> (+rows/cNNN lazily; latest run only on open), basket/cNNN, pins/current, catalogue/latest,
  products/latest, manual/<YYYY-MM-DD> (manual prices), scrapers (project=="cpi"), system/scrapers_routine, years/<yyyy>,
  outlets/<code>. Counts from the basket (barcode 363, spec 274, name 550, service 112, market 2), never from projects/cpi counters.
- TrendX: projects/te (+ index config if present, default TE_DEFAULT_INDEX), te/runs + rows, te/basket, scrapers (project=="te").
- SPPI: projects/sppi/meta/current (or projects/sppi.meta / minimal shape on projects/sppi), observations/<collectionId>;
  periods are months, collections W1..W3 shown as "Collection 1/2/3" inside 2026-11; timing "to be determined" when lead_days null.

## §14 implementation
1. EN default/LTR; stored choice (localStorage "lang", try/catch) wins.
2. No SPPI index (dashboard shows a collections table "Prices only; no SPPI index in v1"). SPPI basket editor in
   SPPI › Price History › Commodities ☰: tabs Items/Outlets/Sample, add/edit/retire/restore (retire = status "retired" + until),
   inline validation (required fields, unique codes, survey/kind match, duplicate sample), Save = re-read + compare with the
   version read (raw JSON) → write once with `version+1`; on change shows pink box + "Reload and retry", no overwrite.
   NOTE: the runtime db API (db.d.ts 0.2.96) has no `if_version` precondition (set is last-writer-wins), so "if_version" is
   implemented as this client-side check of the stored `version` field / content. "Start SPPI basket" creates an empty meta on click.
3. Manual-entry cards: SPPI (button "Add price manually" + Blocked/Not read cells) → observations/<wid> row source "manual",
   entered_by (viewer name or "manual"), entered_at; edit/withdraw (status "withdrawn"). CPI (Blocked cells) →
   projects/cpi/manual/<day> {rows:[{line_code,outlet,price,regular_price,unit,url,note,entered_by,entered_at,source:"manual"}]};
   shown with "Manual" chip; not used by the CPI monitor. Validation >0 numeric AED, nothing prefilled.
4. TrendX base 2 Oct 2026 = 100 unchanged; Stale shown.
5. No weights: coicopBuild gets {} and weighted:false, no weights doc read, no weight columns/bars; string check passes on all routes
   (evals/strings.js: no "weight"/"وزن" in visible text with all details opened).
6. SPPI monthly periods; Years & Months shows "Nov 2026 · 3 collections"; Schedules: "No automated SPPI schedule yet" + "Collected
   monthly; timing per item to be determined", no Run now.

## Harness
- `harness/routes.js ../scraping-panel.html <out> [--viewports=..] [--routes=a,b] [--sppi=../sppi_sample.json] [--lang=ar] [--eval=file]`
- evals: `strings.js` (banned strings/weights), `sppi_editor.js` (check 27), `sppi_manual.js` (check 28), `cpi_manual.js` (check 29),
  `cpi_db.js` (donut + monitor), `te_ph.js` (check 18), `logs.js` (check 10), `sc_new.js` (scraper create + actors), `fulltext.js`.

## Numbers seen in the harness (§13)
- 1/7 Home CPI: 1,301 lines; "601 / 1,089 rows"; 2 Nov; "Partial: Carrefour blocked since 30 Oct". TrendX: "107 commodities · 90 in
  index", "99.39 · 2 Oct 2026 = 100", "Collected 2 Nov 03:09 Dubai", latest quote 30 Oct.
- 8 CPI dashboard: outlets 6, commodities 1,301 (555 priced in latest run), records 19,340 (+601 latest run), active scrapers 6
  (= Scrapers page). Donut Method: 363 / 274 / 550 / 112 / 2.
- 9 Outlets: Carrefour "Blocked since 30 Oct" (362 of 363 pages refused); Lulu Read OK.
- 10 Price Logs: 22 runs; 12-27 Oct Completed; 14 Oct 10:00 Dubai "Partial: Carrefour 43/384 pages failed"; 15 Oct "Completed with
  warnings: 2/373 Carrefour pages failed"; 28/29 Oct Partial 20/363, 27/363; 30 Oct–2 Nov "Partial: Carrefour blocked (362 pages
  refused)" (30 Oct: 363) with the data note.
- 11 Price History Carrefour 29 Oct–2 Nov: Apply aria-disabled until outlet; 15-day cap; 196 Blocked cells on page 1.
- 12 CPI monitor: "Internal price monitor (12 Oct = 100), not the CPI", 12 Oct = 100.00, 2 Nov 101.11, n per day printed
  (30 Oct–2 Nov n≈221-231: Carrefour excluded).
- 13 Years & Months Oct: "19 of 20 days", missing 25 Oct, duplicate 14 Oct 08:04 flagged, Carrefour blocked days 30, 31;
  Check completeness only on click.
- 15 Schedules: 3 CPI cards (daily 06:47, catalogue, custom on demand); Legacy Apify collapsed. (Catalogue shows 06:47 in the
  harness because the stub get_trigger returns the same cron for every trigger id.)
- 16-19 TrendX: index Oct 100.28, 2 Nov 99.39; Price History outlet preselected, Apply enabled, Tea 2 Nov "Stale 3 Oct";
  Years "29 of 30 days", Complete with gaps, monthly 100.28; Monthly report has sheets Monthly, Daily index, All Days prices, Notes.
- 20 No SPPI: every SPPI page shows "—" / "No data yet" (KPIs, scrapers KPIs, years count), no errors.
- 21 Sample: 11 outlets; PIA W3 Blocked; week headers show both windows + collected_on; Schedules no Run now.
- 22 KPI = list: CPI 6/1,301/19,340/6; SPPI 11/46/112 (+31)/8; TrendX 1/107/3,317 (+107)/1.
- 27 editor: 46 items (18 routes: 11 dom, 7 for; 28 hotels), 11 outlets, 80 sample; duplicate code refused inline; save writes
  meta once; external change → pink box, no overwrite.
- 28 SPPI manual: PIA TF-ISB (the sample has PIA → Islamabad, not Karachi) W3 out: Blocked → "1,234 Manual" → withdraw → Blocked.
- 29 CPI manual: Carrefour 31 Oct cell → projects/cpi/manual/2026-10-31, cell "9.75 Manual".
- 25 No writes on load on any route (all three runs).

## Known gaps / notes
- projects/te/basket is not in the backup, so the TrendX basket editor shows 0 lines in the harness (real db has it).
- Two empty `.chip` spans exist inside hidden legacy blocks (#job-state, #sc-job-state) until a run starts; never visible empty.
- Brief check 28 names "PIA Karachi"; the data agent's sample assigns PIA to TF-ISB (Islamabad). The page follows the data.

## Fix round 2 (QA failures, 5 Nov)
All in src/, rebuilt with `node build.js` (5,214 lines). Probes: `qa_fix2/t_fix.js` (run with `qa_r1/qa.js`); full harness
re-run in `qa_fix2/` (en_s, ar_s, en_n, ev_str, ev_str_ar, ev_logs, fin): all clean, 0 page/console errors, 0 writes.
- Check 23 / §12 / §10 (`51_schedules.js` drawSched): every `body.innerHTML =` (CPI cards, By Outlet, SPPI, TrendX, error box)
  now calls `unmountAll()` first, so #quick and #apify-run are parked in #hold rather than destroyed; `.open = false` is guarded.
  Probe: Sync schedules, By Outlet then By Schedule, Sync again, leave and return: the "Run now (server, Scrapling)" card and the
  collapsed "Legacy: Apify run" are present every time, with no pageerror.
- Check 6 (`00_style.html`): `.tw { position: relative }`, so `td > .sr-only` stays inside the table scroller. At 390x844 the
  CPI grid (Carrefour, Apply) gives scrollWidth 390, and SPPI/TrendX grids also give 390.
- Check 5 (`21_icons.js`, `30_legacy.js` ct-row, `47_history.js` group rows): new `chevd` (down) icon. Collapsed rows use
  `chevr` + `flip` (">" in LTR, mirrored "<" in RTL); open rows use `chevd`. The CPI grid group button had the same bug and is fixed too.
- §3 contrast (`00_style.html`): `.seg-toggle button[aria-pressed=true]:hover:not(:disabled):not([aria-disabled=true])
  { background: var(--primary-hover); color: #fff }` (specificity 0,3,1 beats the generic hover). Hovering the active button gives
  white on rgb(21,101,159) for TrendX Prices/Index, donut Group/Method and Schedules.
- §4 unknown route (`42_shell.js`): a project-prefixed unknown hash (`#cpi-nope`, `#trendx-foo`, `#sppi-x/y`) keeps its pid and
  goes back to that project's dashboard. An unprefixed one goes to the dashboard of the project last open (else CPI). The button always
  reads "Back to Dashboard".
- §6 "—" (`44_data.js`, `35_scrapers.js`, `54_scrapers_page.js`): `scRoutineData` uses `Promise.allSettled`, so a failed runs read
  no longer stops the basket read. A routine target is `null` when the basket is not read, and the Target items KPI then shows "—".
  If runs fail but the basket loads, the KPI shows the real 1,824, which comes from the basket. Schedules "Last run" on a failed
  runs read shows "— runs could not be read" (the raw error is kept only in a title attribute).
- §5.1 (`52_logs.js` `sppiRunIssues`): the SPPI Price Logs chip names each outlet that is not Read OK, grouped with counts and
  singular/plural, e.g. "Partial: Emirates Holidays not read (0 of 28 cells); dnata Travel 19 of 28 priced" and "Partial: Emirates,
  Air India, PIA, Turkish Airlines blocked (26 cells); Saudia, Royal Jordanian failed (4 cells); …". AR uses "،"/"؛".
  `.acc > summary .chip, .kv dd .chip` may now wrap, which removes an AR overflow at 1366 caused by the longer text.
- §8.4 (`51_schedules.js`): the Catalogue crawl card has a "Last run" line from catalogue/latest: a run chip (Completed if store
  count > 0, else Failed "0 stores") + date · stores · products. Harness: "Completed 3 Nov · 10 stores · 15,460 products".
  If there is no catalogue: "— no catalogue yet".

## Fix round 3 (QA round 2 failures, 5 Nov)
All in src/, rebuilt with `node build.js` (5,258 lines). Previous build kept as `qa_fix2/before_fix3.html`. Probes in `qa_fix3/`:
`t_fix3.js` (run with `qa3.js`, a copy of qa_r2/qa.js whose read failure can be switched on mid-test through `global.FAILRE`),
`t_err.js` with `--fail=projects/sppi/(meta|observations) --failread`, `t_shell.js --only=mobile --vp=390x844`. Full harness
re-run: `en_s`, `ar_s`, `en_n` all clean (both viewports, 0 page/console errors, 0 writes on load); evals sppi_editor (check 27),
sppi_manual (28), cpi_manual (29), sc_new and strings pass (strings output identical to round 2).
- Checks 23 / §14.2 / §14.3, data loss (`40_base.js`): new `getDocStrict(path)` returns null only when the doc does not exist and
  throws on a failed read. `getDoc` (error = absent) stays only for optional reads such as pins, catalogue and routine.
  `sppiLoad` now reads meta, `projects/sppi` and every observations doc strictly. A failed read throws, `sppiCache` is not set,
  and each SPPI page shows its pink box with Retry: dashboard ×4, outlets, price history, schedules, years, price logs, editor,
  and the Scrapers list (new `scRoutineErr`, pink box above the table, count "—" instead of "No data yet").
  - "Start SPPI basket" appears only after a successful read that found nothing. On click it re-checks meta and `projects/sppi`
    with strict reads. A failed check shows the pink box "Unable to check the SPPI basket right now, so nothing was written" and
    does not write. Probe: no writes, and meta keeps its 46 items. The stale `e.currentTarget` after await is also fixed.
  - SPPI manual card: refuses to write when the collection was never read. The save-time read is strict, so a failure shows the
    pink box "Not saved: nothing was written" + Retry (probe: W3 stays at 104 rows, 0 writes). SPPI basket save also reads strictly.
  - CPI manual card: the grid reads `projects/cpi/manual/<day>` strictly. A failed read shows the pink grid box + Retry, never
    an empty manual set. The save-time read is strict and refuses when the day was not read (probe: 0 writes, doc unchanged).
    Save and withdraw errors in both cards now use the pink box with Retry.
- Check 23 / §4 Writes, basket (`20_core.js`, `30_legacy.js`, `42_shell.js`, `49_commodities.js`, `43_home.js`): new flag
  `basketLoaded` and shared `mountBasketLoad(pid, seq)`, used by Commodities (CPI/TrendX) and Other projects. On a failed read
  the basket card is hidden and a pink box with Retry ("nothing can be saved until it loads") takes its place, with no toast.
  `#b-save` is aria-disabled (with a title) until the basket has loaded AND something changed, and the handler refuses
  both cases. Probes: failed CPI/TrendX read gives 0 writes even on a forced click. With a loaded basket, a clean Save writes
  nothing, and deleting a line enables Save, which writes the chunks.
- §3 mobile targets (`00_style.html`, `@media (max-width: 899px)`): `:where(button, .btn) { min-height: 44px }`. `.home-foot a`
  and `a.tap` ("Open Scrapers" now has class `tap`) are 44px inline-flex. SPPI/CPI grid cell buttons (Blocked / Not read /
  Manual) are min-height 44px. Checkboxes and radios are 24×24, and their labels (`.picks`, `.flags`, label > checkbox) are 44px tall.
  Probe at 390×844 finds nothing under 44px except the 24×24 checkbox inputs inside their 44px labels and two inline
  product links in the basket table (41px).
- §8.3 labels (`00_style.html`): `.fld > label.fl` is blue `--primary-ink` rgb(21,95,151), weight 800 (it was overridden by the
  generic `.fld > label` colour). Outlet / Date From / Date To are now blue bold.
- Check 21 / §8.3 totals (`40_base.js` sppiTotal, `48_sppi_history.js`): a leg counts only if it is manual or has status
  ok / partial / to_review, so blocked, not_available, failed and withdrawn legs give no total. A total with a to_review leg gets
  `status:"to_review"`: the cell shows the "To review" chip and a tooltip "Built from a leg marked To review: not a validated
  price", and the Excel/CSV status column reads `to_review`. Riyadh flydubai W3: "5,552 … To review". BA London stays "Incomplete".
- §8.6 workspace (`35_scrapers.js`): `#sc-save-top` is aria-disabled + `secondary` (pale, rgb(219,227,236)) until the form is
  dirty, for new and saved scrapers. Once dirty it is `primary`. Clicking it while pale on a new form says
  "Fill the required fields (*), then save". The bottom Save keeps today's behaviour.
