# Routine: Daily CPI scrape (Scrapling: barcode + bulk categories) → Scraping Projects panel

- Scheduled task id: `trig_018GydPXyp4MkLmnMj8dAoqY`
- Schedule: `CRON_TZ=Asia/Dubai 47 6 * * *` (06:47 Dubai, every day)
- Fresh cloud session each run; the code comes from the panel's `system_bundle` documents (same files as this branch).

Prompt, as stored on 9 Nov 2026 (barcode searches now paced at 2.5 s and stopped after 5 refused pages):

````text
Daily job: price the whole CPI basket (Carrefour and Lulu, Dubai; the 1,301 lines) with the Scrapling Python library and store the run in the user's "Scraping Projects" panel artifact: https://claude.ai/artifact/FSURninVx3TmNCeFYDyxUn . Basket lines WITH a barcode are searched by barcode (then by name); lines WITHOUT a barcode are priced from bulk category listings as a PRODUCT SET: every listing that fits the line, any origin and brand, tracked product by product and chained from day to day (scripts/product_panel.py), so a product going out of stock or a new one appearing does not make the price jump. Food lines named in Latin letters are searched by name on the shop sites (scripts/name_live.py). Whatever the searches cannot price is then filled from the latest catalogue of the catalogue routine (barcoded lines by name with exact pack size, goods with a Latin model name, goods with an Arabic-only name by English specs), so the Dataiku download shows them. No Apify. Work unattended; do not ask questions. S below is the scratchpad directory; R is S/repo.

1. Install: `python3 -m pip install -q "scrapling[fetchers]" openpyxl pillow --break-system-packages`.

2. Load the ArtifactData tool (ToolSearch "select:ArtifactData"). With the url above, read with out_dir S/w:
   - action "list", collection "system_bundle", query {"limit": 50}   (the code)
   - action "list", collection "projects/cpi/basket", query {"limit": 100}   (the basket, with the user's edits)
   - action "get", collection "projects/cpi/pins", doc_id "current"   (PINS; remember its version)
   - action "get", collection "projects/cpi/products", doc_id "latest"   (the product history: fields history_asset, panel_asset, days; remember its version)
   - action "get", collection "projects/cpi/catalogue", doc_id "latest"   (the catalogue pointer: field rows_asset, field date)
   Then rebuild the code, the basket and the pins file (use the real scratchpad path for S):
   python3 -c "import json,glob,os
S='<S>'
for f in sorted(glob.glob(S+'/w/system_bundle/*.json')):
    d=json.load(open(f)); d=d.get('data',d)
    for p,t in d['files'].items():
        os.makedirs(os.path.dirname(S+'/repo/'+p) or '.',exist_ok=True); open(S+'/repo/'+p,'w',encoding='utf-8').write(t)
items=[]
for f in sorted(glob.glob(S+'/w/projects/cpi/basket/*.json')):
    d=json.load(open(f)); d=d.get('data',d); items+=d['items']
os.makedirs(S+'/repo/data/basket',exist_ok=True); json.dump(items,open(S+'/repo/data/basket/basket.json','w'),ensure_ascii=False); print(len(items),'basket lines')
pf=glob.glob(S+'/w/projects/cpi/pins/current.json')
pins=(json.load(open(pf[0])).get('data',{}).get('pins',{}) if pf else {})
json.dump(pins,open(S+'/pins.json','w'),ensure_ascii=False); print(len(pins),'pins')"
   If the products doc has a history_asset id, download that file with the Artifact tool (action "read", url above, path = the id) and call its local path PREV; otherwise PREV is "-".
   If the catalogue doc has a rows_asset id, download that file the same way (action "read", url above, path = the id) and call its local path CAT (a catalogue.json file); if there is none or the download fails, CAT stays empty and step 4 runs without it.
   Save the current UTC time (ISO 8601, e.g. 2026-10-12T04:00:05+00:00) as STARTED and today's date as D.

3. From R, with the environment variable CPI_PINS=S/pins.json set for the category crawl and for combine_run, start these three in the background at the same time (Bash run_in_background, timeout 3 hours each), all writing into data/runs/D_daily:
   - `python3 -I scripts/scrapling_search.py carrefour data/runs/D_daily --delay 2.5 --stop-after 5`
   - `python3 -I scripts/scrapling_search.py lulu data/runs/D_daily --delay 2.5 --stop-after 5`
   - `CPI_PINS=S/pins.json python3 -I scripts/scrapling_category.py data/runs/D_daily`
   (--delay 2.5: at least 2.5 s between requests to a shop; --stop-after 5: after 5 refused pages in a row the shop is not asked again this run, the rest stays unread. Do not remove them and do not retry a refused shop.)
   Wait for all three to finish (about 60-100 minutes; wait on their background task notifications or their PIDs, not on a pgrep pattern that matches your own watcher). Never invent or type prices.

4. From R, in this order (CPI_PINS=S/pins.json set for the first command):
   - `CPI_PINS=S/pins.json python3 -I scripts/combine_run.py data/runs/D_daily` (gives barcoded lines the searches missed a last chance in the category listings; it also leaves the full day's listings in data/runs/D_daily/catalog.csv)
   - `python3 -I scripts/name_live.py data/runs/D_daily` (about 1-2 minutes: searches the food lines named in Latin letters on Carrefour and Lulu; writes name_live.csv; if it fails, go on without it)
   - `python3 -I scripts/product_panel.py update PREV data/runs/D_daily/catalog.csv D data/runs/D_daily/history.json` (adds today's products to the history; PREV or -)
   - `python3 -I scripts/product_panel.py series data/runs/D_daily/history.json data/runs/D_daily` (writes line_prices.csv and product_panel.csv in the run folder; panel_run.py uses line_prices.csv for the no-barcode lines)
   - `CPI_CATALOGUE_JSON=CAT python3 -I scripts/panel_run.py data/runs/D_daily STARTED` (first pass, to know the found products; leave the variable out when CAT is empty). With CAT it takes 3-5 minutes longer: it fills the barcoded lines the searches missed from the catalogue, then prices the named goods and the Arabic-only goods, and prints `catalogue <date>: N rows for M lines`.
   - `python3 -I scripts/fetch_thumbs.py data/runs/D_daily --found-only` (small pictures of the found products; failures only leave a photo empty)
   - `CPI_CATALOGUE_JSON=CAT python3 -I scripts/panel_run.py data/runs/D_daily STARTED` again (the catalogue part is cached, so this one is fast). It prints `RUN_ID <id> chunks <n> thumbs <m> ...` and writes data/runs/D_daily/panel/run.json, c000.json ..., t000.json ... and last.json.

5. Store the run in the panel (url above) with ArtifactData "batch" calls (at most 50 writes and about 900 KB of files per call; split into several calls if needed, run.json in the last one): op "set", collection "projects/cpi/runs/<RUN_ID>/rows", doc_id "cNNN", file_path each panel/cNNN.json; op "set", collection "projects/cpi/runs/<RUN_ID>/thumbs", doc_id "tNNN", file_path each panel/tNNN.json; and op "set", collection "projects/cpi/runs", doc_id <RUN_ID>, file_path R/data/runs/D_daily/panel/run.json. Then ArtifactData "get" collection "projects" doc_id "cpi" (no out_dir) for its version, and "update" collection "projects" doc_id "cpi" with file_path R/data/runs/D_daily/panel/last.json and if_version = that version.

6. Save the pins and the product history (they carry the reference listings and the day-to-day chain; never delete them):
   a) python3 -c "import json;p=json.load(open('S/pins.json'));json.dump({'pins':p},open('S/pins_doc.json','w'),ensure_ascii=False)" then ArtifactData "set" collection "projects/cpi/pins" doc_id "current" with file_path S/pins_doc.json and if_version = the version read in step 2 (re-read it if it changed).
   b) With the Artifact tool upload R/data/runs/D_daily/history.json and R/data/runs/D_daily/product_panel.csv as assets, ONE call per file (action publish, url above, asset true, file_path). Then ArtifactData "set" collection "projects/cpi/products" doc_id "latest" with data {history_asset: <new id>, panel_asset: <new id>, days: <the list of days in history.json>, products: <number of products in history.json>} and if_version = the version read in step 2. Afterwards delete the OLD history_asset and panel_asset (the ids in the document you read in step 2) with the Artifact tool action delete, path = the asset id. Delete nothing else.

7. Finish with one line: RUN_ID, status, accepted/lines for each retailer for barcode and category, how many no-barcode lines have a product-set price, how many lines were filled from the catalogue (and its date), how many lines came from the live name search, and the number of products in the history.
````

## Carrefour category crawl through search pages (deployed 6 Nov 2026)
Carrefour refuses its category pages (`/mafuae/en/c/F...`, HTTP 403 since 30 Oct). `scripts/scrapling_category.py` now reads
Carrefour through its search pages instead: one query per basket spec line of the crawled groups (the first word of each
`must_have` term, ~167 queries, at most 2 pages each), and keeps a product in a section only when the `productCategory`
codes Carrefour embeds in the page contain that section's code (e.g. `f1670000` Meat & Poultry, `bakery`), so frozen or
tinned goods found by a "beef" search never enter the fresh sections. Lulu keeps its category pages.
- At least 2.5 s between requests (+0-1 s random); 429/503 wait for Retry-After (else 30/90/180 s).
- A refused page (403, challenge, empty shell) is logged `REFUSED ... - not read` and counted, never "0 products";
  after 5 refused pages in a row the shop is not asked again that run (the rest is "not asked", not "not found").
- `crawl_status.json` in the run folder: pages read / refused and state (ok, partial, blocked) per retailer; the log ends
  with `carrefour category: N pages read, M refused`.
- The panel bundle (`system_bundle`/b0) carries this crawl on top of the deployed matching code (the GPT fix is still not
  deployed), so only the crawl part differs from what ran before.
