# Routine: the panel's own scrapers (Scrapling engine) → Scraping Projects panel

- Scheduled task id: `trig_01R9twPVtUNPjnTS2KHhFn4a`, stored in the panel document `system/scrapers_routine`
  (`{trigger_id, mode: "on_demand"}`), so the panel's "Run now" button starts it (fire_trigger).
- Schedule: none. The user runs scrapers on demand only (3 Nov 2026): the task fires only from "Run now", and the
  form's daily auto trigger is hidden. The stored prompt (below, as created) runs only the scrapers with a Run now request.
- Fresh cloud session each run; the code comes from the panel's `system_bundle` documents (same files as this branch),
  which must hold `scripts/custom_scrape.py`.

The scrapers are the panel's `scrapers` collection (the form under الكاشطات). Each run picks the ones that are due
(`scripts/custom_scrape.py due`): active, engine Scrapling, and either a "Run now" request newer than the last run or a
daily auto trigger whose time has passed in its time zone with no run since that time. Apify scrapers run in the
panel itself and are skipped here.

Prompt:

````text
Hourly job: run the user's own Scrapling scrapers that are due and store their results in the user's "Scraping Projects" panel artifact: https://claude.ai/artifact/FSURninVx3TmNCeFYDyxUn (collection "scrapers"). Each scraper document holds its target URLs, a list script and a details script (JavaScript run in the page), a link selector, the browser type (http or chromium), target items, an auto trigger and possibly a "Run now" request. Work unattended; do not ask questions. Never invent or type values: the rows are what the scripts read from the pages. No Apify, no challenge solving, no proxies, no stealth tricks; a page that refuses is reported as not read. S below is the scratchpad directory; R is S/repo.

1. Load the ArtifactData tool (ToolSearch "select:ArtifactData"). With the url above, action "list", collection "scrapers", query {"limit": 100}, out_dir S/w. Save the current UTC time (ISO 8601, e.g. 2026-11-03T04:00:05+00:00) as NOW. Then, from any folder:
   python3 -c "import json,glob,os
S='<the real scratchpad path>'
os.makedirs(S+'/docs',exist_ok=True)
for f in sorted(glob.glob(S+'/w/scrapers/*.json')):
    d=json.load(open(f)); i=d.get('id') or os.path.basename(f)[:-5]; json.dump(d.get('data',d),open(S+'/docs/'+i+'.json','w'),ensure_ascii=False)
print(len(glob.glob(S+'/docs/*.json')),'scrapers')"
   If there are no scrapers, finish with the line "no scrapers" and stop.

2. Rebuild the code: action "list", collection "system_bundle", query {"limit": 50}, out_dir S/w; then
   python3 -c "import json,glob,os
S='<the real scratchpad path>'
for f in sorted(glob.glob(S+'/w/system_bundle/*.json')):
    d=json.load(open(f)); d=d.get('data',d)
    for p,t in d['files'].items():
        os.makedirs(os.path.dirname(S+'/repo/'+p) or '.',exist_ok=True); open(S+'/repo/'+p,'w',encoding='utf-8').write(t)"
   From R: `python3 -I scripts/custom_scrape.py due S/docs NOW`. It prints the ids that are due, one per line (and why, on stderr). If it prints none, finish with the line "nothing due" and stop; do not install anything.

3. Install: `python3 -m pip install -q "scrapling[fetchers]" --break-system-packages` (Playwright comes with it). Check that Chromium starts: `python3 -I -c "from playwright.sync_api import sync_playwright; import sys; sys.path.insert(0,'scripts'); import custom_scrape as c; p=sync_playwright().start(); b=c.launch(p); print(b.version); b.close(); p.stop()"` from R. If it fails, run `python3 -m playwright install chromium` (Chromium may already be at /opt/pw-browsers, PLAYWRIGHT_BROWSERS_PATH) and check again.

4. For each due id, ONE AT A TIME (never two scrapers at once: the script keeps each site to one request every 2 s or more):
   a) Save the current UTC time as STARTED. ArtifactData "update" collection "scrapers" doc_id <id> with data {"last_run": {"at": STARTED, "status": "running", "items": 0, "run_id": null}} (the panel shows it as running).
   b) From R: `python3 -I scripts/custom_scrape.py run S/docs/<id>.json S/out/<id> STARTED` (Bash run_in_background, timeout 2 hours; wait for its task notification). It prints `RUN_ID <run id> status <done|error> items <n> ...` and writes S/out/<id>/run.json, rows/c000.json ..., log.txt and last.json. If it ends without that line (crash), still go to c) if run.json exists; otherwise write last_run {"at": STARTED, "status": "error", "items": 0, "run_id": null} and go on with the next id.
   c) Store the run with ArtifactData "batch" calls (at most 50 writes and about 900 KB of files per call; split into several calls if needed, run.json in the last one): op "set", collection "scrapers/<id>/runs/<RUN_ID>/rows", doc_id "cNNN", file_path each S/out/<id>/rows/cNNN.json; and op "set", collection "scrapers/<id>/runs", doc_id <RUN_ID>, file_path S/out/<id>/run.json.
   d) ArtifactData "get" collection "scrapers" doc_id <id> (no out_dir) for its version and its run_request. If run_request is set and its "at" is later than STARTED (the user pressed "Run now" again during the run), remove the "run_request" key from S/out/<id>/last.json so the request stays for the next hour. Then "update" collection "scrapers" doc_id <id> with file_path S/out/<id>/last.json and if_version = that version (re-read and retry once if it changed). This sets last_run {at, status, items, run_id}, last_scraped and clears run_request.

5. Finish with one line per scraper run: id, RUN_ID, status, items, pages read / not read / script errors (from the RUN_ID line), and the first "NOT READ" or "SCRIPT ERROR" line of its log.txt if there is one.
````
