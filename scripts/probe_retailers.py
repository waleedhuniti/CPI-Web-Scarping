"""Can this machine read Union Coop, Spinneys and Nesto? Run it from a network in the UAE (Dataiku server, office PC, a UAE VPS).

    pip install "scrapling[fetchers]"
    python scripts/probe_retailers.py

Prints the HTTP status of a few pages per retailer and saves what came back to probe_out/<retailer>_<n>.html, so the
readers (product cards, prices) can be written from real pages. Send the printed table and the probe_out folder.
Plain requests first (Chrome TLS fingerprint); if a page answers 403/405/5xx it is tried again with the stealth browser.
"""
import re
import sys
from pathlib import Path

PAGES = {
    "unioncoop": ["https://www.unioncoop.ae/", "https://www.unioncoop.ae/en/", "https://www.unioncoop.ae/robots.txt"],
    "spinneys": ["https://www.spinneys.com/en-ae/", "https://www.spinneys.com/en-ae/sitemap.xml",
                 "https://www.spinneys.com/en-ae/catalogue/"],
    "nesto": ["https://www.nestoonline.com/", "https://nestogroup.com/", "https://nestogroup.com/stores/"],
}


def main():
    from scrapling.fetchers import FetcherSession, StealthyFetcher
    out = Path("probe_out")
    out.mkdir(exist_ok=True)
    print(f"{'retailer':10} {'plain':>6} {'browser':>8}  {'bytes':>8}  title / url")
    with FetcherSession(impersonate="chrome", timeout=30, retries=0) as s:
        for name, urls in PAGES.items():
            for n, u in enumerate(urls):
                status, body, via = "ERR", "", "-"
                try:
                    r = s.get(u)
                    status, body = r.status, r.body.decode("utf-8", "ignore")
                except Exception as e:
                    body = str(e)[:80]
                if status != 200:
                    try:
                        p = StealthyFetcher.fetch(u, headless=True, solve_cloudflare=True, timeout=60000)
                        via, body = p.status, p.html_content
                    except Exception as e:
                        via = "ERR"
                t = re.search(r"<title>(.*?)</title>", body, re.S)
                (out / f"{name}_{n}.html").write_text(body, encoding="utf-8")
                print(f"{name:10} {status!s:>6} {via!s:>8}  {len(body):>8}  {(t.group(1).strip()[:50] if t else '')} | {u}")


if __name__ == "__main__":
    sys.exit(main())
