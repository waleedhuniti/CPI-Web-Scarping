"""Carrefour collection from an office PC (a normal home or office connection), polite and stoppable.

    python scripts/pc/carrefour_pc.py --test      # 20 barcode pages only: does Carrefour answer this PC at all?
    python scripts/pc/carrefour_pc.py             # the day's collection: barcode search (363 pages), then the category crawl

Same code as the daily cloud routine (scripts/scrapling_search.py, scripts/scrapling_category.py), with the same rules:
one request at a time, at least 2.5 s apart, Retry-After honoured, a refused page stays unread (never "not found"),
and after 5 refused pages in a row the shop is not asked again that run. No proxy, no changed identity, no human-check solving.

Output: data/runs/<date>_carrefour_pc/ (barcode/, category/, summary.txt) and a zip next to it to hand over for the panel.
"""
import argparse
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PY = sys.executable
DELAY = "2.5"


def run(cmd, dry):
    print("\n>", " ".join(str(c) for c in cmd), flush=True)
    if dry:
        return 0
    return subprocess.run([str(c) for c in cmd], cwd=ROOT).returncode


def status(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", action="store_true", help="20 barcode pages only")
    ap.add_argument("--dry-run", action="store_true", help="print the commands, send nothing")
    a = ap.parse_args()
    day = (datetime.now(timezone.utc) + timedelta(hours=4)).strftime("%Y-%m-%d")        # Dubai date
    out = ROOT / "data" / "runs" / f"{day}_carrefour_pc{'_test' if a.test else ''}"
    out.mkdir(parents=True, exist_ok=True)
    lines = [f"Carrefour from the office PC, {day}{' (test: 20 pages)' if a.test else ''}"]

    cmd = [PY, "scripts/scrapling_search.py", "carrefour", out / "barcode", "--delay", DELAY, "--no-names", "--stop-after", "5"]
    if a.test:
        cmd += ["--limit", "20"]
    run(cmd, a.dry_run)
    b = status(out / "barcode" / "carrefour_status.json")
    lines.append(f"barcode search: {b.get('read', 0)} pages read, {b.get('failed', 0)} refused/failed, "
                 f"{b.get('not_asked', 0)} not asked -> {b.get('state', 'not run')}")

    if not a.test and b.get("state") in ("ok", "partial"):
        cats = json.load(open(ROOT / "config" / "categories.json", encoding="utf-8"))["carrefour"]
        cmd = [PY, "scripts/scrapling_category.py", out / "category", "--crawl-only", "--delay", DELAY,
               "--only", ";".join(c["name"] for c in cats)]
        run(cmd, a.dry_run)
        c = status(out / "category" / "crawl_status.json").get("carrefour", {})
        lines.append(f"category crawl (search pages): {c.get('read', 0)} pages read, {c.get('refused', 0)} refused -> {c.get('state', 'not run')}")
    elif not a.test:
        lines.append("category crawl: not started (the barcode search did not get through)")

    (out / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + "\n".join(lines))
    if not a.dry_run:
        z = out.with_suffix(".zip")
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(out.rglob("*")):
                if f.is_file():
                    zf.write(f, f.relative_to(out.parent))
        print("\nResults to hand over:", z)


if __name__ == "__main__":
    main()
