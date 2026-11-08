# Routine on the office laptop: Carrefour only (catalogue crawl + barcode search) → the day's cloud results

The cloud routines keep running at 06:47 (CPI) and 06:52 (catalogue) for everything Carrefour does not block. This task runs on the
office laptop once a day, AFTER them, reads Carrefour from the office connection and puts only Carrefour's part into the day's results:
- the Carrefour rows of the day's catalogue (replaces that store in the published catalogue, its price history and pictures);
- the Carrefour barcode rows of the day's CPI run (replaces only those rows; scripts/pc/merge_carrefour_barcode.py).
Not restored by this task: Carrefour's category / product-set rows of the CPI run (they stay "not observed" while the cloud is refused).
If the laptop is refused too, nothing is changed and the refusal is reported; the day's Carrefour gap stays a gap.

Schedule: daily 09:00 Asia/Dubai (the cloud runs are done by about 08:15). Takes about 35-45 minutes.

Prompt:

````text
Daily job on the office laptop (Windows, Claude Code, folder Desktop/cpi): read Carrefour UAE and add it to today's results in the user's "Scraping Projects" panel artifact: https://claude.ai/artifact/FSURninVx3TmNCeFYDyxUn . Work unattended; do not ask questions. Rules that never bend: never type, invent or carry forward a price; no VPN, proxy, changed browser identity or any other way around a block; a page Carrefour refuses stays unread and is reported as refused/blocked, never as "not found" or "0 products"; the scripts keep at least 2.5 s between requests and stop after 5 refused pages in a row, do not change that; one process at a time against Carrefour; if Carrefour refuses this laptop, change nothing in the panel and say so. Use `python` (not python3) and forward slashes in every path. Environment variables: in Git Bash prefix the command; in PowerShell set `$env:NAME='...'` first.

0. Setup.
   - B = Desktop/cpi under the user's profile (USERPROFILE). H = B/repo (git clone holding the helper scripts). D = today's Dubai date. S = B/work/D (create S/w). STARTED = the current UTC time in ISO 8601.
   - If H does not exist: `git clone --branch claude/sleepy-lamport-dwu4iw https://github.com/waleedhuniti/CPI-Web-Scarping.git H`; else in H `git pull origin claude/sleepy-lamport-dwu4iw`.
   - `python -m pip install -q "scrapling[fetchers]" openpyxl pillow pillow-heif`.
   - Load ArtifactData (ToolSearch "select:ArtifactData") and check the Artifact tool works; if either is missing, stop and report it.
   - With the panel url, read with out_dir S/w: action "list", collection "system_bundle", query {"limit": 50}; action "list", collection "projects/cpi/basket", query {"limit": 100} (the basket, with the user's edits: the barcode search needs it); action "get", collection "projects/cpi/pins", doc_id "current" (only so the rebuild finds it; this task does not use or change the pins); action "get", collection "projects/cpi/catalogue", doc_id "latest" (remember its version and fields date, rows_asset, thumbs_assets, history_asset).
   - From H: `python scripts/pc/rebuild_code.py S` (code to S/repo = R, basket to R/data/basket/basket.json). If it prints an error, stop and report it.
   - Check that the cloud routines of today have finished: the catalogue doc's `date` must be D, and ArtifactData "list" collection "projects/cpi/runs" (query {"limit": 100}, out_dir S/runs) must show a run whose id starts with D without hyphens (e.g. 20261109T0247-auto). If one of them is missing, wait 10 minutes and look again, up to 6 times; if still missing, do Part 1 and Part 2 up to the point where they need it (crawl and search), then report that the merge was not done.

PART 1, Carrefour catalogue (about 8 minutes). Work in R.
   1.1 `python -I scripts/catalogue_crawl.py data/catalogue/D --stores=carrefour --part-only`. Read the end of its output and the log: if data/catalogue/D/part_carrefour.csv is missing, empty or has fewer than 3,000 rows, Carrefour refused us: skip 1.2-1.5 and say so.
   1.2 Download with the Artifact tool (action "read", panel url, path = the id) the day's catalogue.json (rows_asset) as CATJSON, the history (history_asset) as HISTJSON, and the six thumbs files (thumbs_assets: food, household, personal, electronics, clothing, other).
   1.3 `python -I scripts/catalogue_patch_store.py build CATJSON data/catalogue/D/part_carrefour.csv data/catalogue/D` (the panel catalogue without Carrefour + the new Carrefour rows -> data/catalogue/D/catalog.csv). Then make the folder data/catalogue/D_part with only part_carrefour.csv copied there as catalog.csv, and `python -I scripts/fetch_thumbs.py data/catalogue/D_part` (pictures of the new rows only).
   1.4 `python -I scripts/catalogue_assets.py data/catalogue/D` then `python -I scripts/catalogue_patch_store.py thumbs data/catalogue/D <the six downloaded thumbs files>` then `python -I scripts/catalogue_history.py update data/catalogue/D HISTJSON data/catalogue/D/history.json` (this replaces today's day in the history, so Carrefour's "skipped" mark for today goes away).
   1.5 Upload with the Artifact tool, ONE call per file (action publish, panel url, asset true, file_path): catalogue.json, the six thumbs_<group>.json, history.json. Put the new ids into data/catalogue/D/latest.json (rows_asset, thumbs_assets {food, household, personal, electronics, clothing, other}, history_asset). Then ArtifactData "set" collection "projects/cpi/catalogue" doc_id "latest" with file_path data/catalogue/D/latest.json and if_version = the version from step 0 (re-read it if it changed, and if the date is no longer D, stop and report). Afterwards delete the OLD assets of the previous doc (old rows_asset, old thumbs_assets, old history_asset) with the Artifact tool action delete, path = the id. Delete nothing else.

PART 2, Carrefour barcode search (about 25-35 minutes). Work in R.
   2.1 `python -I scripts/scrapling_search.py carrefour data/runs/D_carrefour --delay 2.5 --stop-after 5` (it also searches by name the barcodes not found). Then read data/runs/D_carrefour/carrefour_status.json: state "blocked" or 0 pages read means Carrefour refused this laptop; skip the rest of Part 2 and say so. Do not retry.
   2.2 `python -I scripts/panel_run.py data/runs/D_carrefour STARTED` (writes data/runs/D_carrefour/panel/run.json and c000.json ...).
   2.3 Today's cloud run: its id is RUN_ID. ArtifactData "get" collection "projects/cpi/runs" doc_id RUN_ID with out_dir S/cloud (saves the run document) and "list" collection "projects/cpi/runs/RUN_ID/rows" query {"limit": 100} out_dir S/cloud (saves every cNNN.json; the output shows each document's version, keep them).
   2.4 From H (not R): `python scripts/pc/merge_carrefour_barcode.py S/cloud/projects/cpi/runs/RUN_ID.json S/cloud/projects/cpi/runs/RUN_ID/rows R/data/runs/D_carrefour/panel S/merged`. It prints a JSON result. If action is "skipped", report its reason and stop (nothing is written).
   2.5 If action is "merged": write back with ArtifactData "batch" calls (at most 50 writes per call, files at most about 900 KB per call): for each S/merged/cNNN.json op "set", collection "projects/cpi/runs/RUN_ID/rows", doc_id cNNN, file_path that file, if_version = the version of that document read in 2.3 (omit if_version for a chunk id that did not exist). Then op "delete" for every id in the result's "delete" list (with its if_version). Last, op "set" collection "projects/cpi/runs" doc_id RUN_ID file_path S/merged/run.json with if_version = the run document's version from 2.3. If any version no longer matches, stop and report (do not overwrite).
   2.6 ArtifactData "get" collection "projects" doc_id "cpi" for its version and its lastRun; then "update" it with data {"lastRun": {"at": <the same "at">, "status": <status of S/merged/run.json>, "accepted": <accepted of S/merged/run.json>}} and if_version.

Finish with two lines. Part 1: Carrefour rows in today's catalogue (or "refused"), history day number. Part 2: pages read / refused, how many Carrefour barcode lines were found, the merge result (rows, accepted before -> after) or why it was not done.
````
