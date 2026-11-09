"""Prepare a bounded, validated URL batch for the Scrapling GitHub Actions workflow."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_HOSTS = {
    "carrefour": {"www.carrefouruae.com", "carrefouruae.com"},
    "lulu": {"gcc.luluhypermarket.com"},
}
MAX_BATCH_SIZE = 200


def extract_urls(payload: object) -> list[str]:
    if isinstance(payload, dict):
        payload = payload.get("items", payload.get("urls"))
    if not isinstance(payload, list):
        raise ValueError("Input must be a JSON list, or an object containing an 'items' or 'urls' list.")

    urls: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(payload):
        if isinstance(item, str):
            url = item.strip()
        elif isinstance(item, dict) and isinstance(item.get("url"), str):
            url = item["url"].strip()
        else:
            raise ValueError(f"Item {index} must be a URL string or an object with a string 'url' field.")
        if not url:
            continue
        if url not in seen:
            urls.append(url)
            seen.add(url)
    return urls


def prepare_batch(retailer: str, urls: list[str], offset: int, limit: int) -> list[str]:
    if retailer not in ALLOWED_HOSTS:
        raise ValueError("Retailer must be carrefour or lulu.")
    if offset < 0:
        raise ValueError("Offset must be zero or greater.")
    if not 1 <= limit <= MAX_BATCH_SIZE:
        raise ValueError(f"Batch size must be between 1 and {MAX_BATCH_SIZE}.")

    for url in urls:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or host not in ALLOWED_HOSTS[retailer]:
            raise ValueError(f"URL is not an approved HTTPS {retailer} product URL: {url}")

    batch = urls[offset : offset + limit]
    if not batch:
        raise ValueError(f"No URLs at offset {offset}; the input contains {len(urls)} unique URLs.")
    return batch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--retailer", required=True, choices=sorted(ALLOWED_HOSTS))
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    payload = json.loads(args.input_json.read_text(encoding="utf-8"))
    urls = extract_urls(payload)
    batch = prepare_batch(args.retailer, urls, args.offset, args.limit)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prepared {len(batch)} unique {args.retailer} URLs (offset {args.offset}; {len(urls)} total).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
