"""Small product thumbnails (about 2-3 KB each) for embedding photos in the Excel files.

    python scripts/fetch_thumbs.py data/runs/2026-10-12_full data/runs/2026-10-08_catalogue
    python scripts/fetch_thumbs.py data/runs/<run> --found-only      # only the products found for the basket

Collects every photo link of the given runs (catalog.csv photo_url, data/photos.json, panel rows) and saves each
picture once as data/thumbs/<sha1 of the link>.jpg, at most 96 px, JPEG. Carrefour's image server answers only a
browser-like request, so pictures are fetched with Scrapling's Chrome fingerprint; Carrefour links get ?im=Resize=300
(JPEG instead of AVIF). data/thumbs/ is a local cache (not committed).
"""
import csv
import glob
import hashlib
import io
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THUMBS = ROOT / "data/thumbs"
SIZE = 96


def thumb_path(url):
    return THUMBS / (hashlib.sha1(url.encode()).hexdigest() + ".jpg")


def photo_links(run_dirs, found_only=False):  # noqa: C901
    cache = json.loads((ROOT / "data/photos.json").read_text()) if (ROOT / "data/photos.json").exists() else {}
    urls = set()
    for d in run_dirs:
        if found_only:                                   # only the products found for the basket (panel rows)
            for f in glob.glob(str(Path(d) / "panel/c*.json")):
                urls.update(r["photo"] for r in json.load(open(f))["rows"] if r.get("photo") and r.get("accepted") == "yes")
            continue
        for r in csv.DictReader(open(Path(d) / "catalog.csv", encoding="utf-8-sig")) if (Path(d) / "catalog.csv").exists() else []:
            u = r.get("photo_url") or cache.get(r["url"], "")
            if u:
                urls.add(u)
        for f in glob.glob(str(Path(d) / "panel/c*.json")):
            urls.update(r["photo"] for r in json.load(open(f))["rows"] if r.get("photo"))
        for f in glob.glob(str(Path(d) / "*_matched.csv")):
            urls.update(cache[r["url"]] for r in csv.DictReader(open(f, encoding="utf-8-sig")) if cache.get(r.get("url", "")))
    return urls


def fetch_url(url):
    if "mafrservices.com" in url and "im=" not in url:
        return url + ("&" if "?" in url else "?") + "im=Resize=300"
    return url


_local = threading.local()
CF = {}   # Cloudflare pass for Sharaf DG's image server: {"cookies": {...}, "ua": "..."}


def cloudflare_pass(sample_url):
    """One stealth-browser visit (Scrapling) to Sharaf DG's image server; its cookies and user agent then let the
    fast fetcher download the rest."""
    from scrapling.fetchers import StealthyFetcher
    p = StealthyFetcher.fetch(sample_url, headless=True, solve_cloudflare=True, timeout=90000)
    CF["cookies"] = {c["name"]: c["value"] for c in (p.cookies or [])}
    CF["ua"] = (getattr(p, "request_headers", None) or {}).get("user-agent")


def session():
    if not hasattr(_local, "s"):
        from scrapling.fetchers import FetcherSession
        _local.s = FetcherSession(impersonate="chrome", timeout=30, retries=2).__enter__()
    return _local.s


def get_one(url):
    from PIL import Image
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()      # some Carrefour pictures come as AVIF
    except ImportError:
        pass
    out = thumb_path(url)
    if out.exists():
        return True
    try:
        if "sharafdg.com" in url and CF:
            hdr = {"Referer": "https://uae.sharafdg.com/", **({"User-Agent": CF["ua"]} if CF.get("ua") else {})}
            p = session().get(url, cookies=CF["cookies"], headers=hdr)
        else:
            p = session().get(fetch_url(url), headers={"Referer": "https://www.carrefouruae.com/"} if "mafrservices" in url else None)
        body = p.body if isinstance(p.body, bytes) else bytes(p.body)
        if p.status != 200 or len(body) < 200:
            return False
        im = Image.open(io.BytesIO(body)).convert("RGB")
        im.thumbnail((SIZE, SIZE))
        im.save(out, "JPEG", quality=70, optimize=True)
        return True
    except Exception:
        return False


def main(run_dirs, workers=8, found_only=False):
    THUMBS.mkdir(parents=True, exist_ok=True)
    urls = sorted(u for u in photo_links(run_dirs, found_only) if not thumb_path(u).exists())
    print(f"{len(urls)} pictures to fetch", flush=True)
    sdg = [u for u in urls if "sharafdg.com" in u]
    if sdg:
        try:
            cloudflare_pass(sdg[0])
        except Exception as e:
            print("Sharaf DG pictures: no Cloudflare pass", str(e)[:100])
    ok = 0
    with ThreadPoolExecutor(workers) as ex:
        for n, res in enumerate(ex.map(get_one, urls), 1):
            ok += res
            if n % 500 == 0:
                print(f"{n}/{len(urls)} done, {ok} saved", flush=True)
    print(f"{ok} of {len(urls)} saved in {THUMBS.relative_to(ROOT)}")


if __name__ == "__main__":
    main([a for a in sys.argv[1:] if not a.startswith("--")], found_only="--found-only" in sys.argv)
