"""CPI scraping portal: one page to run the scrape, edit the basket and edit the Apify actors.

    pip install -r requirements.txt
    python portal/app.py            # then open http://127.0.0.1:5000

The Apify token is read from APIFY_TOKEN or from .env (the Settings tab writes it there; .env is not committed).
"""
import collections
import datetime as dt
import io
import json
import subprocess
import sys
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from flask import Flask, abort, jsonify, request, send_file, send_from_directory  # noqa: E402

from portal import scraper  # noqa: E402

app = Flask(__name__, static_folder=None)
app.json.sort_keys = False                # keep actor input keys in the order they were written
STATIC = Path(__file__).resolve().parent / "static"
PAGE_FUNCTION = ROOT / "actors/lulu_search/page_function.js"


# ---------------------------------------------------------------- scrape job (one at a time)

class Job:
    def __init__(self):
        self.lock = threading.Lock()
        self.state = {"status": "idle", "log": [], "progress": {}, "run_dir": None, "summary": None}
        self.stop_flag = False

    def log(self, msg):
        with self.lock:
            self.state["log"].append(f"{dt.datetime.now():%H:%M:%S}  {msg}")

    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps(self.state, default=str))

    def running(self):
        return self.state["status"] == "running"


JOB = Job()
CLIENT_FACTORY = scraper.ApifyClient      # tests swap this for a fake


def run_job(retailers, items, run_dir, token):
    actors = scraper.load_actors()
    client = CLIENT_FACTORY(token)
    all_results, summary = [], {}
    try:
        for key in retailers:
            cfg = actors[key]
            runs = scraper.build_runs(cfg, items)
            JOB.log(f"{key}: {sum(len(b) for b, _ in runs)} barcodes in {len(runs)} runs of {cfg['actor']}")
            with JOB.lock:
                JOB.state["progress"][key] = {"done": 0, "total": len(runs), "failed": 0}
            rows, searched, failed, raw = [], set(), set(), []

            def one(batch, actor_input):
                if JOB.stop_flag:
                    raise scraper.ApifyError("stopped by user")
                run_id, data = client.run(cfg["actor"], actor_input, stop=lambda: JOB.stop_flag)
                return run_id, data

            with ThreadPoolExecutor(max_workers=cfg.get("parallel_runs", 1)) as pool:
                futs = {pool.submit(one, b, inp): b for b, inp in runs}
                for fut in as_completed(futs):
                    batch = futs[fut]
                    try:
                        run_id, data = fut.result()
                        r, s = scraper.PARSERS[cfg["parser"]](data, batch, cfg)
                        rows += r
                        searched |= s
                        raw += data
                        JOB.log(f"{key}: run {run_id} - {len(data)} items, {len(r)} listings")
                    except Exception as e:                       # one failed batch must not lose the others
                        failed |= set(batch)
                        with JOB.lock:
                            JOB.state["progress"][key]["failed"] += 1
                        JOB.log(f"{key}: batch {batch[0]}... failed: {e}")
                    with JOB.lock:
                        JOB.state["progress"][key]["done"] += 1

            with open(run_dir / f"{key}_raw.jsonl", "w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            (run_dir / f"{key}_dataset.json").write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            res = scraper.match_rows(key, items, rows, searched, failed)
            all_results += res
            counts = collections.Counter(r["status"] for r in res)
            summary[key] = {"lines": len(res), "accepted": sum(r["accepted"] == "yes" for r in res),
                            "statuses": dict(counts.most_common())}
            JOB.log(f"{key}: {summary[key]['accepted']} of {len(res)} lines accepted")
        scraper.write_results(run_dir / "results.csv", all_results)
        (run_dir / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
        with JOB.lock:
            JOB.state.update(status="stopped" if JOB.stop_flag else "done", summary=summary)
        JOB.log(f"done - data/runs/{run_dir.name}/results.csv")
    except Exception as e:
        JOB.log("ERROR: " + str(e))
        traceback.print_exc()
        with JOB.lock:
            JOB.state["status"] = "error"


# ---------------------------------------------------------------- routes

@app.get("/")
def index():
    return send_from_directory(STATIC, "index.html")


@app.get("/static/<path:name>")
def static_file(name):
    return send_from_directory(STATIC, name)


@app.get("/api/basket")
def get_basket():
    return jsonify(scraper.load_basket())


@app.put("/api/basket")
def put_basket():
    try:
        return jsonify({"ok": True, "items": scraper.save_basket(request.get_json())})
    except (ValueError, KeyError, TypeError) as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.post("/api/basket/preview")
def preview_item():
    """Derived fields for one edited line (GTIN, parsed quantity, origin) without saving."""
    try:
        return jsonify({"ok": True, "item": scraper.normalize_item(request.get_json())})
    except (ValueError, KeyError, TypeError) as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.post("/api/basket/upload")
def upload_basket():
    """Replace the basket with a workbook in the office's format (same layout as basket_source.xlsx)."""
    f = request.files.get("file")
    if not f or not f.filename.lower().endswith(".xlsx"):
        return jsonify({"ok": False, "error": "choose an .xlsx file"}), 400
    from dataclasses import asdict
    from cpi.basket import load_basket as load_xlsx
    data = f.read()
    try:
        items = [asdict(i) for i in load_xlsx(io.BytesIO(data))]
    except Exception as e:
        return jsonify({"ok": False, "error": f"could not read the workbook: {e}"}), 400
    if not items:
        return jsonify({"ok": False, "error": "no priced items found in the workbook"}), 400
    (ROOT / "data/basket/basket_source.xlsx").write_bytes(data)
    return jsonify({"ok": True, "items": scraper.save_basket(items)})


@app.get("/api/basket/download")
def download_basket():
    return send_file(scraper.BASKET_CSV, as_attachment=True, download_name="basket.csv")


@app.get("/api/actors")
def get_actors():
    return jsonify({"actors": scraper.load_actors(), "parsers": scraper.PARSER_NAMES, "modes": scraper.MODES,
                    "page_function": PAGE_FUNCTION.read_text(encoding="utf-8") if PAGE_FUNCTION.exists() else ""})


@app.put("/api/actors")
def put_actors():
    body = request.get_json()
    try:
        actors = scraper.save_actors(body["actors"])
        if "page_function" in body:
            PAGE_FUNCTION.parent.mkdir(parents=True, exist_ok=True)
            PAGE_FUNCTION.write_text(body["page_function"], encoding="utf-8")
        return jsonify({"ok": True, "actors": actors})
    except (ValueError, KeyError, TypeError) as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.get("/api/settings")
def get_settings():
    t = scraper.get_token()
    return jsonify({"token_set": bool(t), "token_hint": (t[:6] + "…" + t[-4:]) if len(t) > 12 else ""})


@app.put("/api/settings")
def put_settings():
    token = (request.get_json() or {}).get("token", "").strip()
    if not token:
        return jsonify({"ok": False, "error": "empty token"}), 400
    scraper.set_token(token)
    return get_settings()


@app.post("/api/scrape")
def start_scrape():
    if JOB.running():
        return jsonify({"ok": False, "error": "a scrape is already running"}), 409
    body = request.get_json() or {}
    actors = scraper.load_actors()
    retailers = [r for r in body.get("retailers", []) if r in actors]
    if not retailers:
        return jsonify({"ok": False, "error": "choose at least one retailer"}), 400
    items = scraper.load_basket()
    groups, codes = set(body.get("groups") or []), set(body.get("item_codes") or [])
    if groups:
        items = [i for i in items if i["group_code"] in groups]
    if codes:
        items = [i for i in items if i["item_code"] in codes]
    items = [i for i in items if i["barcode_kind"] == "gtin"]
    if not items:
        return jsonify({"ok": False, "error": "no basket lines with a barcode in this selection"}), 400
    token = scraper.get_token()
    if not token:
        return jsonify({"ok": False, "error": "set the Apify token in Settings first"}), 400
    run_dir = scraper.RUNS_DIR / f"{dt.datetime.now():%Y-%m-%d_%H%M}_portal"
    run_dir.mkdir(parents=True, exist_ok=True)
    JOB.stop_flag = False
    with JOB.lock:
        JOB.state = {"status": "running", "log": [], "progress": {}, "run_dir": run_dir.name, "summary": None}
    JOB.log(f"{len(items)} barcoded basket lines, retailers: {', '.join(retailers)}")
    threading.Thread(target=run_job, args=(retailers, items, run_dir, token), daemon=True).start()
    return jsonify({"ok": True, "run_dir": run_dir.name})


@app.post("/api/scrape/stop")
def stop_scrape():
    JOB.stop_flag = True
    JOB.log("stop requested")
    return jsonify({"ok": True})


@app.get("/api/scrape/status")
def scrape_status():
    return jsonify(JOB.snapshot())


@app.get("/api/runs")
def list_runs():
    out = []
    for d in sorted(scraper.RUNS_DIR.glob("*_portal"), reverse=True):
        s = d / "summary.json"
        out.append({"name": d.name, "summary": json.loads(s.read_text()) if s.exists() else None,
                    "has_results": (d / "results.csv").exists()})
    return jsonify(out)


def _run_dir(name):
    d = (scraper.RUNS_DIR / name).resolve()
    if d.parent != scraper.RUNS_DIR.resolve() or not d.name.endswith("_portal") or not d.is_dir():
        abort(404)
    return d


@app.get("/api/runs/<name>/results")
def run_results(name):
    p = _run_dir(name) / "results.csv"
    if not p.exists():
        abort(404)
    if request.args.get("download"):
        return send_file(p, as_attachment=True, download_name=f"{name}_results.csv")
    import csv
    with open(p, encoding="utf-8-sig") as f:
        return jsonify(list(csv.DictReader(f)))


@app.post("/api/git/push")
def git_push():
    """Commit the basket, actor settings and portal runs, then push the current branch to GitHub."""
    msg = (request.get_json() or {}).get("message") or "Portal: update basket / actors / runs"

    def git(*a):
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, timeout=120)

    git("add", "data/basket", "config/actors.json", "actors", *[str(p.relative_to(ROOT)) for p in scraper.RUNS_DIR.glob("*_portal")])
    c = git("commit", "-m", msg)
    if c.returncode and "nothing to commit" not in (c.stdout + c.stderr):
        return jsonify({"ok": False, "error": c.stderr or c.stdout}), 500
    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    p = git("push", "-u", "origin", branch)
    if p.returncode:
        return jsonify({"ok": False, "error": p.stderr}), 500
    return jsonify({"ok": True, "branch": branch, "output": (c.stdout + p.stderr).strip()[-800:]})


if __name__ == "__main__":
    import os
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)), debug=False)
