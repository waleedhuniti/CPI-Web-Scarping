# te_<date>.json + the panel's TrendX basket -> panel run documents in out/
import glob, json, os, sys
from datetime import datetime, timezone

src = sys.argv[1]
doc = json.load(open(src))
rows = [dict(zip(doc["cols"], r)) for r in doc["rows"]]
basket = []
for f in sorted(glob.glob("panel/projects/te/basket/*.json")):
    d = json.load(open(f)); d = d.get("data", d); basket += d.get("items", [])
want = [b for b in basket if b.get("enabled") not in (False, "no")]
norm = lambda s: str(s or "").strip().lower()
by = {norm(r["commodity"]): r for r in rows}
label = "Trading Economics"
if want:
    res = [dict(actor=label, **by[norm(b["commodity"])], status="ok", accepted="yes") if norm(b["commodity"]) in by
           else dict(actor=label, commodity=b["commodity"], category=b.get("category", ""), status="missing", accepted="no") for b in want]
else:
    res = [dict(actor=label, **r, status="ok", accepted="yes") for r in rows]
st = {}
for r in res: st[r["status"]] = st.get(r["status"], 0) + 1
acc = sum(r["accepted"] == "yes" for r in res)
os.makedirs("out", exist_ok=True)
rid = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M") + "-auto"
json.dump({"rows": res, "i": 0}, open("out/c000.json", "w"), ensure_ascii=False)
json.dump(dict(startedAt=doc["scraped_at"], finishedAt=datetime.now(timezone.utc).isoformat(timespec="seconds"), status="done",
               summary={"te": dict(label=label, lines=len(res), accepted=acc, statuses=st)}, chunks=1, count=len(res), accepted=acc,
               log=[f"scheduled run {doc['run_date']} via {doc['method']}: {len(rows)} rows on the page"]), open("out/run.json", "w"), ensure_ascii=False)
json.dump({"lastRun": {"at": doc["scraped_at"], "status": "done", "accepted": acc}}, open("out/last.json", "w"))
print("RUN_ID", rid, "rows", len(res), "accepted", acc, st)
