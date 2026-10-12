"""Every priced product gets a photo: fills the gaps of a catalogue day (or a run folder).

    python scripts/fill_photos.py data/catalogue/2026-10-12

For each row with a price whose picture is missing (no photo link, or the picture could not be downloaded), opens the
product page (Scrapling; stealth browser for Cloudflare stores) and takes its main image (og:image / JSON-LD), saves the
thumbnail (scripts/fetch_thumbs.py) and writes the link back into catalog.csv. Prints the coverage at the end.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_thumbs as ft  # noqa: E402
from collect_photos import page_photo  # noqa: E402

STEALTH = ("sharafdg.com", "centrepointstores.com", "maxfashion.com")


def product_photo(url, session):
    try:
        if any(h in url for h in STEALTH):
            from scrapling.fetchers import StealthyFetcher
            p = StealthyFetcher.fetch(url, headless=True, solve_cloudflare=True, timeout=90000)
            html = p.html_content
        else:
            p = session.get(url)
            html = p.body.decode("utf-8", "ignore") if isinstance(p.body, bytes) else str(p.body)
        return page_photo(html)
    except Exception:
        return ""


def main(cat_dir):
    from scrapling.fetchers import FetcherSession
    path = Path(cat_dir) / "catalog.csv"
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    fields = list(rows[0])
    priced = [r for r in rows if r.get("price")]
    missing = [r for r in priced if not r.get("photo_url") or not ft.thumb_path(r["photo_url"]).exists()]
    print(f"{len(priced)} priced products, {len(missing)} without a photo", flush=True)
    # 1) links we have but whose picture is not saved yet
    sdg = [r["photo_url"] for r in missing if "sharafdg.com" in (r.get("photo_url") or "")]
    if sdg:
        try:
            ft.cloudflare_pass(sdg[0])
        except Exception as e:
            print("Sharaf DG pictures: no Cloudflare pass", str(e)[:100])
    for r in missing:
        if r.get("photo_url"):
            ft.get_one(r["photo_url"])
    # 2) no link, or the link failed: the product page
    still = [r for r in missing if not r.get("photo_url") or not ft.thumb_path(r["photo_url"]).exists()]
    with FetcherSession(impersonate="chrome", timeout=30, retries=2) as s:
        for n, r in enumerate(still, 1):
            u = product_photo(r["url"], s)
            if u and ft.get_one(u):
                r["photo_url"] = u
            if n % 25 == 0:
                print(f"product pages {n}/{len(still)}", flush=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    ok = sum(1 for r in priced if r.get("photo_url") and ft.thumb_path(r["photo_url"]).exists())
    print(f"photos: {ok} of {len(priced)} priced products ({100 * ok / max(1, len(priced)):.1f}%)")
    for r in [r for r in priced if not (r.get("photo_url") and ft.thumb_path(r["photo_url"]).exists())][:10]:
        print("  still without photo:", r["outlet"], "|", r["title"][:60], "|", r["url"])


if __name__ == "__main__":
    main(sys.argv[1])
