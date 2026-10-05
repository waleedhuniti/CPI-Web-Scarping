"""Carrefour UAE (carrefouruae.com/mafuae/en).

Barcode lookup: Carrefour's keyword search accepts a barcode and returns the product that carries it:

    https://www.carrefouruae.com/mafuae/en/search?keyword=<EAN>

The Store actor `blackfalcondata/carrefour-maf-scraper` does the same in bulk: `query` takes a JSON array of
barcodes (one run, many items), `market: "mafuae"`.  IMPORTANT: its `gtin` / `sku` / `productId` fields are
Carrefour's internal product id (e.g. 79241), not a barcode, and `barcode` is null.  The barcode evidence is the
search we typed (`searchQuery`), so `from_actor_item` puts it in `searched_barcode` and leaves `barcode` empty.
"""
import json
import re

from .. import gtin
from ..matcher import Listing

SEARCH_URL = "https://www.carrefouruae.com/mafuae/en/search?keyword={gtin}"
ACTOR = "blackfalcondata/carrefour-maf-scraper"

_LINK = re.compile(r"\[([^\]\n]+)\]\((https://www\.carrefouruae\.com/[^)\s]*?/p/(\d+)[^)\s]*)\)")
_AED = re.compile(r"AED\s?([\d,]+(?:\.\d+)?)")


def search_url(ean) -> str:
    return SEARCH_URL.format(gtin=gtin.digits_only(ean))


def actor_input(eans, max_results: int = 200) -> dict:
    """Input for one batch run of the Store actor over many barcodes."""
    return {"market": "mafuae", "language": "en", "query": json.dumps([gtin.digits_only(e) for e in eans]),
            "maxResults": max_results}


def parse_search_markdown(markdown: str, searched_ean: str) -> list:
    """Listings on a Carrefour search page. Price block after each product link: 'AED17.79' (or two amounts on offer)."""
    links = list(_LINK.finditer(markdown))
    out = []
    for i, m in enumerate(links):
        end = links[i + 1].start() if i + 1 < len(links) else len(markdown)
        amounts = [float(a.replace(",", "")) for a in _AED.findall(markdown[m.end():end])]
        price = amounts[0] if amounts else 0.0
        out.append(Listing(
            retailer="carrefour", title=m.group(1).strip(), price=price,
            regular_price=max(amounts) if amounts else 0.0,
            searched_barcode=gtin.digits_only(searched_ean), result_count=len(links),
            url=m.group(2).split("?")[0],
            extra={"product_id": m.group(3), "price_amounts_seen": amounts},
        ))
    return out


def from_actor_item(item: dict) -> Listing:
    """Row from the Store actor. Never use item['gtin'] as a barcode - it is Carrefour's own product id."""
    query = gtin.digits_only(item.get("searchQuery"))
    return Listing(
        retailer="carrefour", title=item.get("title") or "", brand=item.get("brand") or "",
        price=float(item.get("price") or 0), regular_price=float(item.get("regularPrice") or item.get("price") or 0),
        barcode="", searched_barcode=query if len(query) >= 8 else "",
        url=item.get("url") or "", in_stock=item.get("in_stock"),
        extra={"product_id": item.get("productId"), "sold_by_weight": (item.get("attributes") or {}).get("isSoldByWeight")},
    )


def mark_result_counts(listings) -> list:
    """The actor returns a flat list: set result_count per searched barcode (a clean barcode hit has exactly 1)."""
    counts = {}
    for lst in listings:
        counts[lst.searched_barcode] = counts.get(lst.searched_barcode, 0) + 1
    for lst in listings:
        lst.result_count = counts[lst.searched_barcode] if lst.searched_barcode else 0
    return listings
