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


def search_url(ean) -> str:
    return SEARCH_URL.format(gtin=gtin.digits_only(ean))


def actor_input(eans, max_results: int = 200) -> dict:
    """Input for one batch run of the Store actor over many barcodes."""
    return {"market": "mafuae", "language": "en", "query": json.dumps([gtin.digits_only(e) for e in eans]),
            "maxResults": max_results}


# Card text right after the product link, e.g.
#   'AED17.79 1kg'                                   price only
#   'AED72.29 AED 14.46 per Kilo5kg'                 price + unit price (per kg) + size
#   'AED21.99 28.99 AED 4.40 per Kilo5kg'            offer price + price before the offer + unit price + size
# The unit price ('AED x per Kilo') is NOT the regular price.
_CARD = re.compile(
    r"\s*AED\s?(?P<price>\d[\d,]*\.\d{2})"
    r"(?:\s+(?P<was>\d[\d,]*\.\d{2})(?=\s|$))?"
    r"(?:\s*AED\s?(?P<unit>\d[\d,]*\.\d{2})\s*per\s*(?P<per>[A-Za-z]+))?"
    r"(?P<size>[^\n\[]{0,40})"
)


def _f(s):
    return float(s.replace(",", "")) if s else 0.0


def parse_search_markdown(markdown: str, searched: str) -> list:
    """Listings on a Carrefour search page (English or Arabic). `searched` is the barcode or text that was searched."""
    links = list(_LINK.finditer(markdown))
    out = []
    for m in links:
        c = _CARD.match(markdown, m.end())
        if not c:                                   # a link without a price card (breadcrumb, banner): not a listing
            continue
        price, was = _f(c["price"]), _f(c["was"])
        digits = gtin.digits_only(searched)
        out.append(Listing(
            retailer="carrefour", title=m.group(1).strip(), price=price,
            regular_price=was if was > price else price,
            searched_barcode=digits if digits == str(searched).strip() else "",
            url=m.group(2).split("?")[0],
            extra={"product_id": m.group(3), "unit_price": _f(c["unit"]), "unit_basis": c["per"] or "",
                   "size_text": (c["size"] or "").strip(), "query": searched},
        ))
    for lst in out:
        lst.result_count = len(out)
    return out


def parse_product_page(markdown: str, json_ld) -> dict:
    """Price, availability, pack size and origin from a Carrefour product page (JSON-LD offer + 'Pack Size' / 'Origin')."""
    offer = {}
    for block in (json_ld if isinstance(json_ld, list) else [json_ld]):
        if isinstance(block, dict) and block.get("@type") == "Product":
            offer = dict(block.get("offers") or {}, sku=block.get("sku"), name=block.get("name"))
    size = re.search(r"Pack Size\s*\n*\s*([^\n]+?)\s*(?:Sold|Origin|\n|$)", markdown)
    # 'Origin' is followed by a flag image whose alt text is the country: 'Origin\n\n![India](...)' (or plain text)
    origin = re.search(r"Origin\s*(?:!\[([^\]]+)\]|([A-Za-z][A-Za-z .'-]+?)\s*(?:\n|$))", markdown)
    return {
        "sku": offer.get("sku"), "name": offer.get("name"),
        "price": _f(str(offer.get("price") or "")) if offer.get("price") else 0.0,
        "in_stock": ("InStock" in str(offer.get("availability"))) if offer.get("availability") else None,
        "pack_size": size.group(1).strip() if size else "",
        "origin": ((origin.group(1) or origin.group(2) or "").strip()) if origin else "",
    }


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
