"""Put the Carrefour barcode rows read on the office laptop into the day's cloud run of the panel, replacing only those rows.

    python scripts/pc/merge_carrefour_barcode.py <cloud run.json> <cloud rows dir> <laptop panel dir> <out dir>

cloud run.json     the run document the cloud routine stored (projects/cpi/runs/<RUN_ID>) saved with ArtifactData out_dir
cloud rows dir     its row documents c000.json, ... (projects/cpi/runs/<RUN_ID>/rows)
laptop panel dir   <laptop run folder>/panel written by scripts/panel_run.py from a folder that holds only the Carrefour barcode files
out dir            run.json + cNNN.json to write back with ArtifactData "set" (same ids), summary.json says which old chunks to delete

Fails closed: nothing is changed (summary.json action = "skipped") unless the laptop read pages of the same day and more of them
than the cloud run did. Only the rows of source "barcode" and retailer "carrefour" are replaced; the Carrefour catalogue/name-search
rows of items the laptop now found by barcode are dropped (so an item has one Carrefour row); everything else stays as the routine left it.
A refused page stays unread: it is never turned into a price or a "not found".
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

LINE = re.compile(r"^Carrefour UAE barcode: (\d+) pages read, (\d+) failed")
BARCODE = re.compile(r"barcode: (\d+) pages read, (\d+) failed")


def doc(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return d["data"] if isinstance(d.get("data"), dict) else d


def read_failed(log):
    for line in log:
        m = LINE.match(line)
        if m:
            return int(m.group(1)), int(m.group(2))
    return 0, 0


def rows_of(folder):
    out = []
    for f in sorted(Path(folder).glob("c*.json")):
        out += doc(f)["rows"]
    return out


def chunk(rows, limit=40_000):
    chunks, cur, size = [], [], 0
    for r in rows:
        s = len(json.dumps(r, ensure_ascii=False))
        if size + s > limit and cur:
            chunks.append(cur)
            cur, size = [], 0
        cur.append(r)
        size += s
    if cur:
        chunks.append(cur)
    return chunks


def merge(cloud_run, cloud_rows_dir, laptop_dir, out_dir, now=None):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    run, lrun = doc(cloud_run), doc(Path(laptop_dir) / "run.json")
    rows, lrows = rows_of(cloud_rows_dir), rows_of(laptop_dir)
    mine = [r for r in lrows if r.get("source") == "barcode" and r.get("retailer") == "carrefour"]
    c_read, c_fail = read_failed(run.get("log", []))
    l_read, l_fail = read_failed(lrun.get("log", []))
    day = {r.get("run_date") for r in rows}
    result = dict(action="skipped", cloud_pages_read=c_read, laptop_pages_read=l_read, laptop_pages_failed=l_fail, delete=[])
    if not mine or l_read <= 0:
        result["reason"] = "the laptop read no Carrefour barcode page: nothing is changed"
    elif {r.get("run_date") for r in mine} != day:
        result["reason"] = f"the laptop rows are of another day ({sorted({r.get('run_date') for r in mine})} vs {sorted(day)}): nothing is changed"
    elif l_read <= c_read:
        result["reason"] = f"the cloud run already read as many Carrefour barcode pages ({c_read}) as the laptop ({l_read}): nothing is changed"
    if "reason" in result:
        (out / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        return result
    found = {r["item_code"] for r in mine if r.get("accepted") == "yes"}
    at = next((i for i, r in enumerate(rows) if r.get("source") == "barcode" and r.get("retailer") == "carrefour"), 0)
    kept, pos = [], None
    for i, r in enumerate(rows):
        if i == at:
            pos = len(kept)
        if r.get("source") == "barcode" and r.get("retailer") == "carrefour":
            continue
        if r.get("retailer") == "carrefour" and r.get("source") in ("catalogue", "name_search") and r.get("item_code") in found:
            continue
        kept.append(r)
    pos = len(kept) if pos is None else min(pos, len(kept))
    new = kept[:pos] + mine + kept[pos:]
    chunks = chunk(new)
    for i, c in enumerate(chunks):
        (out / f"c{i:03d}.json").write_text(json.dumps({"rows": c, "i": i}, ensure_ascii=False), encoding="utf-8")
    old_ids = sorted(f.stem for f in Path(cloud_rows_dir).glob("c*.json"))
    result["delete"] = [i for i in old_ids if int(i[1:]) >= len(chunks)]
    log = [ln for ln in run.get("log", []) if not LINE.match(ln)]
    at_log = next((i for i, ln in enumerate(run.get("log", [])) if LINE.match(ln)), len(log))
    stamp = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    new_log = [f"Carrefour UAE barcode: {l_read} pages read, {l_fail} failed"]
    log = log[:at_log] + new_log + log[at_log:]
    log.append(f"Carrefour barcode rows replaced at {stamp} with the ones read on the office laptop ({l_read} pages read, {l_fail} failed); "
               f"the cloud run read {c_read} (refused: {c_fail}).")
    summary = dict(run.get("summary", {}))
    summary["carrefour_barcode"] = lrun["summary"]["carrefour_barcode"]
    bad = sum(1 for ln in log for m in [BARCODE.search(ln)] if m and int(m.group(2)) > 0.05 * (int(m.group(1)) + int(m.group(2))))
    new_run = dict(run, summary=summary, log=log, chunks=len(chunks), count=len(new),
                   accepted=sum(r.get("accepted") == "yes" for r in new), status="error" if bad else "done",
                   carrefour_from_laptop=dict(at=stamp, pages_read=l_read, pages_failed=l_fail))
    (out / "run.json").write_text(json.dumps(new_run, ensure_ascii=False), encoding="utf-8")
    result.update(action="merged", rows=len(new), chunks=len(chunks), accepted=new_run["accepted"], replaced=len(rows) - len(kept),
                  added=len(mine), dropped_other_carrefour_rows=len(rows) - len(kept) - sum(1 for r in rows if r.get("source") == "barcode" and r.get("retailer") == "carrefour"))
    (out / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    print(json.dumps(merge(*sys.argv[1:5]), ensure_ascii=False, indent=1))
