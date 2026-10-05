"""Turn a Lulu crawl (apify/website-content-crawler dataset saved as JSON) into raw barcode-search rows.

    python scripts/ingest_lulu.py <dataset.json> data/runs/2026-10-05/lulu

Writes <prefix>_raw.jsonl (one row per product found), <prefix>_searched.json (barcodes whose search page was read:
a page that says 'No results found' is a real 'not carried', a barcode missing from this list was never searched)
and prints a summary. The dataset items need `url` (the search URL) and `markdown`.
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cpi.retailers import lulu  # noqa: E402


def main(dataset_path, prefix):
    data = json.load(open(dataset_path, encoding="utf-8"))
    items = data["items"] if isinstance(data, dict) else data
    rows, searched, odd = [], set(), []
    for it in items:
        q = parse_qs(urlparse(it["url"]).query).get("search_text", [""])[0]
        md = it.get("markdown") or ""
        if not q or len(md) < 200 or ("All Products" not in md and "No results found" not in md):
            odd.append(q or it["url"])                      # page did not render a result list: do not trust it
            continue
        searched.add(q)
        for lst in lulu.parse_search_markdown(md, q):
            rows.append(dict(searched_barcode=q, product_id=re.sub(r".*/p/([^/]+)/?$", r"\1", lst.url), title=lst.title,
                             price=lst.price, regular_price=lst.regular_price, in_stock=None, url=lst.url,
                             discount_pct=lst.extra.get("discount_pct", 0), result_count=lst.result_count))
    prefix = Path(prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    with open(f"{prefix}_raw.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    json.dump(sorted(searched), open(f"{prefix}_searched.json", "w"))
    with_hit = {r["searched_barcode"] for r in rows}
    print(f"pages read {len(searched)} | with products {len(with_hit)} | 'No results' {len(searched) - len(with_hit)} "
          f"| unusable pages {len(odd)} {odd[:5]}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
