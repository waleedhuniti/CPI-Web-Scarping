"""Rebuild the code the daily routines run, from the documents the panel stores (what the cloud routines do with an inline
python -c), for a session on a Windows laptop.

    python scripts/pc/rebuild_code.py <S> [--no-basket]

The laptop runs one office connection, so the pacing is set to the rule of at least 2.5 s per shop: the deployed crawl
defaults (catalogue_crawl 1.0 s, name_live 1.2 s) are raised in the rebuilt copy, and the script fails loudly if a
default is not where it expects it (never silently runs faster).

Reads what ArtifactData saved under <S>/w:
  <S>/w/system_bundle/*.json        -> the code, written under <S>/repo/<repo path>   (the panel's system_bundle: this is what
                                       runs, never the git branch: the branch carries changes that are not deployed)
  <S>/w/projects/cpi/basket/*.json  -> <S>/repo/data/basket/basket.json              (the basket with the user's edits)
  <S>/w/projects/cpi/pins/current.json -> <S>/pins.json                              (the pinned listings)
"""
import glob
import json
import os
import sys


PACE = [("scripts/catalogue_crawl.py", "def main(out_dir, delay=1.0,", "def main(out_dir, delay=2.5,"),
        ("scripts/name_live.py", "def run(run_dir, delay=1.2):", "def run(run_dir, delay=2.5):")]


def rebuild(S, basket=True):
    S = os.path.abspath(S)
    n = 0
    for f in sorted(glob.glob(os.path.join(S, "w", "system_bundle", "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        d = d.get("data", d)
        for p, t in d["files"].items():
            dest = os.path.join(S, "repo", *p.split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "w", encoding="utf-8", newline="\n").write(t)
            n += 1
    print(n, "code files")
    for p, old, new in PACE:
        f = os.path.join(S, "repo", *p.split("/"))
        t = open(f, encoding="utf-8").read()
        if new in t:
            continue
        if old not in t:
            raise SystemExit(f"pacing default not found in {p}: stop and check before running")
        open(f, "w", encoding="utf-8", newline="\n").write(t.replace(old, new, 1))
        print("pacing raised to 2.5 s in", p)
    if not basket:
        return
    items = []
    for f in sorted(glob.glob(os.path.join(S, "w", "projects", "cpi", "basket", "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        d = d.get("data", d)
        items += d["items"]
    os.makedirs(os.path.join(S, "repo", "data", "basket"), exist_ok=True)
    json.dump(items, open(os.path.join(S, "repo", "data", "basket", "basket.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(len(items), "basket lines")
    pf = os.path.join(S, "w", "projects", "cpi", "pins", "current.json")
    pins = json.load(open(pf, encoding="utf-8")).get("data", {}).get("pins", {}) if os.path.exists(pf) else {}
    json.dump(pins, open(os.path.join(S, "pins.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(len(pins), "pins")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    rebuild(sys.argv[1], "--no-basket" not in sys.argv)
