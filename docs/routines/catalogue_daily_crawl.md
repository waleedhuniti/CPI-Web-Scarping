# Routine: Daily CPI catalogue crawl (all divisions, Scrapling) → Scraping Projects panel

- Scheduled task id: `trig_01BKPxvQYZr2sCFEWDEJ9LGk`
- Schedule: `CRON_TZ=Asia/Dubai 52 6 * * *` (06:52 Dubai, every day)
- Fresh cloud session each run; the code comes from the panel's `system_bundle` documents (same files as this branch).

Prompt, as stored on 2 Nov 2026:

````text
Daily job: crawl the whole Dubai product catalogue (all CPI divisions: food, household, personal care, electronics/phones, clothing/shoes, other) with the Scrapling Python library, refresh the catalogue in the user's "Scraping Projects" panel artifact (https://claude.ai/artifact/FSURninVx3TmNCeFYDyxUn) and extend its price history. No Apify. Work unattended; do not ask questions. Never invent or type prices. S is the scratchpad directory; R is S/repo.

1. Install: `python3 -m pip install -q "scrapling[fetchers]" openpyxl pillow pillow-heif --break-system-packages` (use python3 -m pip so the packages land in the same Python). Then test the stealth browser that Centrepoint and Max need: `python3 -I -c "from scrapling.fetchers import StealthyFetcher; p=StealthyFetcher.fetch('https://www.maxfashion.com/ae/en', headless=True, solve_cloudflare=True, timeout=90000); print(p.status, len(p.html_content))"`. If it fails to launch, run `scrapling install` (or `python3 -m playwright install chromium`; Chromium may already be at /opt/pw-browsers, PLAYWRIGHT_BROWSERS_PATH) and test again.

2. Load ArtifactData (ToolSearch "select:ArtifactData"). With the url above, action "list", collection "system_bundle", query {"limit": 50}, out_dir S/w. Rebuild the code:
   python3 -c "import json,glob,os
S='<the real scratchpad path>'
for f in sorted(glob.glob(S+'/w/system_bundle/*.json')):
    d=json.load(open(f)); d=d.get('data',d)
    for p,t in d['files'].items():
        os.makedirs(os.path.dirname(S+'/repo/'+p) or '.',exist_ok=True); open(S+'/repo/'+p,'w',encoding='utf-8').write(t)"
   Set D = today's Dubai date.

3. From R, start six processes in the background at the same time (Bash run_in_background, timeout 3 hours each), one per store, into data/catalogue/D:
   `python3 -I scripts/catalogue_crawl.py data/catalogue/D --stores=carrefour --part-only` and the same for lulu, sharafdg, zara, centrepoint, max. Wait for all six to finish by their background task notifications (not by pgrep). If centrepoint or max finishes with 0 rows, that is a failure: fix the stealth browser (step 1) and run that store again once. If a store hangs for more than 2 hours, stop only that process and use what its part_<store>.csv already holds.

4. From R, in order: `python3 -I scripts/catalogue_crawl.py data/catalogue/D --merge`; `python3 -I scripts/fetch_thumbs.py data/catalogue/D`; `python3 -I scripts/fill_photos.py data/catalogue/D` (every priced product must end up with a photo; it prints the coverage); `python3 -I scripts/catalogue_assets.py data/catalogue/D` (writes catalogue.json, thumbs_<group>.json and latest.json).

5. Price history (never delete it): ArtifactData "get" collection "projects/cpi/catalogue" doc_id "latest" (no out_dir): remember its version and its fields rows_asset, thumbs_assets and history_asset (history_asset is missing the first time). If history_asset exists, download it with the Artifact tool (action "read", url above, path = the history_asset id) to a local file PREV. Then run `python3 -I scripts/catalogue_history.py update data/catalogue/D <PREV or ->  data/catalogue/D/history.json` (use - when there is no previous history). It prints the day number, the new entries and any store skipped because its crawl was incomplete.

6. Upload to the panel with the Artifact tool, ONE call per file (action publish, url above, asset true, file_path): catalogue.json, thumbs_food.json, thumbs_household.json, thumbs_personal.json, thumbs_electronics.json, thumbs_clothing.json, thumbs_other.json, history.json. Each result gives an asset id (32 hex). Put them into data/catalogue/D/latest.json: rows_asset = the catalogue.json id, thumbs_assets = {food, household, personal, electronics, clothing, other: id}, history_asset = the history.json id. Then "set" collection "projects/cpi/catalogue" doc_id "latest" with file_path data/catalogue/D/latest.json and if_version = the version from step 5 (re-read it if it changed). Afterwards delete the OLD assets from that previous doc (the old rows_asset, the old thumbs_assets and the old history_asset) with the Artifact tool action delete, path = the asset id. Do not delete anything else.

7. Finish with one line: date, rows per store, photo coverage, history day number and entries added, and anything that failed.
````
