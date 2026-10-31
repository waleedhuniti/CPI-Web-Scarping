# dnata one-off scrapes (packages and air tickets)

Headless Chromium (Playwright) driving dnatatravel.com; the site's own GraphQL calls are made from the page. Python 3, `playwright`.
Chromium path is set in each script (`/opt/pw-browsers/chromium-1243/chrome-linux64/chrome`); change it on another machine.

## Holiday packages (flight + hotel), monthly package sheet
1. `CHECKIN=2026-11-01 CHECKOUT=2026-11-05 python3 dnata_packages.py targets_nov.json res.json`
   per hotel: Bed & Breakfast if offered (else cheapest board) + cheapest Emirates non-stop flight -> calculated price.
2. `CHECKIN=... CHECKOUT=... SHOTDIR=shots python3 shots.py res.json shots.json`
   opens each hotel page, ticks Direct + Emirates, selects the cheapest, answers the "extra night" notice (NIGHTS=4 to force 4 nights),
   records the page's "Total holiday" and saves a screenshot. The page price is the final number.
3. `CHECKIN=... CHECKOUT=... python3 verify.py res.json` - checks no cheaper room of the same board and no cheaper Emirates direct fare.
4. `shots_next.py` - same as shots.py but goes one step further (Continue to book) to read mandatory transfers (Maldives).
5. `write_pkg_nov4n.py res_shown.json out.xlsx` - fills the sheet (copy of the input workbook) + details, method and screenshot sheets.
   Needs the input workbook at `up/pkg.xlsx`.

Rule learned from the manual comparison: when the Emirates flight lands the next day, extend the trip one day so the hotel keeps 4 full
nights (Kuala Lumpur, Bangkok); Maldives prices must include the mandatory resort transfer (shown after "Continue to book").

## Air tickets, monthly ticket sheet
1. `python3 tickets.py tickets_jobs.json tickets_res.json` - flight-only searches: one-way out, one-way back, return; direct flights;
   lowest/highest fare per airline.
2. `python3 write_tickets.py` - fills the domestic (flydubai / Emirates) and foreign (national carrier) sheets of `up3/tickets.xlsx`.

`queries.json` holds the site's GraphQL query texts; `res_*.json` / `tickets_res.json` are the results of the runs already delivered.

## Emirates from emirates.com (run on a PC, not a cloud server)
emirates.com refuses the search from cloud servers ("access restricted" after Search flights, then the whole site). From a normal
home or office connection:
- Windows: double-click `run_ek_windows.cmd` (installs Scrapling and its browser, then runs the 6 -> 13 Nov routes).
- Any system: `python ek_fares.py 2026-11-06 2026-11-13 runs_6_13/ek_res.json [AP ...]` (add `--real-chrome` to use installed Chrome).

One one-way economy search per leg; per flight the first economy price on its card, lowest / highest over the day's flights.
A visible browser opens: if Emirates shows a human check, do it yourself in the window; the script waits and never solves checks.
Each search leaves `ek_debug/<AP>_<leg>_form.png` (filled form) and `.png/.html/.txt` (results). The results-page reader (`fares()`)
was written without seeing that page (the cloud run was refused there): check the first route's numbers against its screenshot.
Re-running skips the legs already in `ek_res.json`. `write_tickets_week.py` then fills the Emirates columns (F-H) from it.
