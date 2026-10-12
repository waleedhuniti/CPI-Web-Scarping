"""Pack the code the daily routine runs into documents for the panel's database (the repository is private).

    python scripts/bundle_for_panel.py <out_dir>      # -> <out_dir>/bundle_0.json, bundle_1.json ...

Each document is {"files": {repo path: text}, "i": n}, at most ~150 KB. The daily routine reads every document of the
panel's `system_bundle` collection and writes the files back under one folder, then runs:
  scripts/scrapling_search.py (barcoded lines), scripts/scrapling_category.py (lines without a barcode),
  scripts/combine_run.py (barcoded lines found in the listings), scripts/panel_run.py (the panel documents).
After changing any of these files here, run this script and write the documents to the panel again.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "cpi").rglob("*.py")) + [
    "scripts/scrapling_search.py", "scripts/scrapling_category.py", "scripts/match_run.py", "scripts/panel_run.py",
    "scripts/name_fallback.py", "scripts/combine_run.py", "config/categories.json", "data/basket/specs_en.json",
]


def main(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = {f: (ROOT / f).read_text(encoding="utf-8") for f in FILES}
    docs, cur, size = [], {}, 0
    for path, text in files.items():
        n = len(text.encode("utf-8"))
        if size + n > 150_000 and cur:
            docs.append(cur)
            cur, size = {}, 0
        cur[path] = text
        size += n
    docs.append(cur)
    for i, d in enumerate(docs):
        (out / f"bundle_{i}.json").write_text(json.dumps({"files": d, "i": i}, ensure_ascii=False), encoding="utf-8")
    print(len(files), "files in", len(docs), "documents ->", out)


if __name__ == "__main__":
    main(sys.argv[1])
