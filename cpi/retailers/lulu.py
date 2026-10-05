"""Lulu Hypermarket UAE (gcc.luluhypermarket.com/en-ae).

Barcode lookup: the site's own search page takes an EAN and returns exactly the products carrying it
(or 'No results found'), so a hit is strong barcode evidence:

    https://gcc.luluhypermarket.com/en-ae/list/?search_text=<EAN>

The page is fetched with Apify's `apify/web-fetch` actor (markdown output); `parse_search_markdown` reads it.
The Store actor `boring_internet_explorer/lulu-scraper` returns real EANs for product / category URLs only (it
returns nothing for search URLs) - `from_actor_item` maps its rows.
"""
import re

from .. import gtin
from ..matcher import Listing
from ..quantity import all_quantities, parse_quantity

SEARCH_URL = "https://gcc.luluhypermarket.com/en-ae/list/?search_text={gtin}"

# '[Title](https://gcc.luluhypermarket.com/en-ae/<slug>/p/<id>/?)'  then  price  [was-price]  ['NN% OFF']
# Weighed fresh items have no slug and carry the weight the price is for: '.../en-ae/p/154716-ea/?convtobuom=500'
_CARD = re.compile(
    r"\[([^\]\n]+)\]\((https://gcc\.luluhypermarket\.com/en-ae/(?:[^)\s]*?/)?p/[^)\s]*?)\)"
    r"\s*\n\s*\n([\d,]+(?:\.\d+)?)"
    r"(?:\s*\n\s*\n([\d,]+(?:\.\d+)?))?"
    r"(?:\s*\n\s*\n(\d+)% OFF)?"
)
_COUNT = re.compile(r"All Products \((\d+)\)")


def search_url(ean) -> str:
    return SEARCH_URL.format(gtin=gtin.digits_only(ean))


def _num(s):
    return float(s.replace(",", "")) if s else 0.0


def parse_search_markdown(markdown: str, searched_ean: str) -> list:
    """Listings found on a Lulu search page; [] when Lulu says 'No results found'."""
    if "No results found" in markdown:
        return []
    m = _COUNT.search(markdown)
    cards = list(_CARD.finditer(markdown))
    count = int(m.group(1)) if m else len(cards)
    out = []
    for c in cards:
        price, other = _num(c.group(3)), _num(c.group(4))
        # '105.00 / 238.95 / 56% OFF' -> current price first, then the price before the offer
        regular = other if other > price else price
        out.append(Listing(
            retailer="lulu", title=c.group(1).strip(), price=price, regular_price=regular,
            searched_barcode=gtin.digits_only(searched_ean), result_count=count,
            url=c.group(2).split("?")[0], in_stock=None,
            extra={"discount_pct": int(c.group(5)) if c.group(5) else 0},
        ))
    return out


def _field(blob: str, key: str) -> str:
    """Value of `"key":"value"` inside the page's escaped Next.js data (quotes appear as \\")."""
    m = re.search(r'\\?"' + re.escape(key) + r'\\?"\s*:\s*\\?"([^"\\]*)\\?"', blob)
    return m.group(1) if m else ""


def parse_product_page(html: str, json_ld) -> dict:
    """Barcodes, price, stock and pack size from a Lulu product page (raw HTML + JSON-LD).

    The page embeds one product record: '"ean":"0000000109628,5011157030920,8901144311002", ... "main_ean":"8901144311002",
    "content":"1 kg", "product_name":"Tilda Pure Original Basmati Rice 1 kg"'. These are Lulu's real EANs (several per
    product is normal: old and new packaging, importer codes).
    """
    offer, name = {}, ""
    for block in (json_ld if isinstance(json_ld, list) else [json_ld]):
        if isinstance(block, dict) and block.get("@type") == "Product":
            offer, name = block.get("offers") or {}, block.get("name") or ""
    records = []
    for m in re.finditer(r'\\?"ean\\?"\s*:\s*\\?"([\d,]*)\\?"', html or ""):
        blob = html[m.start(): m.start() + 6000]
        records.append((m.group(1), blob))
    # the record of THIS product (a page could also carry related products): same product_name as the JSON-LD
    own = [r for r in records if name and _field(r[1], "product_name") == name] or records[:1]
    eans, blob = (own[0] if own else ("", ""))
    price = offer.get("price")
    return {
        "name": name, "price": float(price) if price not in (None, "") else 0.0,
        "in_stock": ("InStock" in str(offer.get("availability"))) if offer.get("availability") else None,
        "eans": [e for e in eans.split(",") if e], "main_ean": _field(blob, "main_ean"),
        "pack_size": _field(blob, "content"), "origin": _field(blob, "country_of_origin") or _field(blob, "origin"),
        "records": len({r[0] for r in records}),
    }


def parse_product_markdown(markdown: str, json_ld) -> dict:
    """Price, stock, size and origin from a Lulu product page crawled as markdown (no HTML): JSON-LD offer for price and
    stock, the '# <title>' heading for the size ('Orange Navel South Africa 1 kg'), 'Country of origin: X' for origin.
    The barcodes are not in the markdown (see parse_product_page for that)."""
    offer, name = {}, ""
    for block in (json_ld if isinstance(json_ld, list) else [json_ld]):
        if isinstance(block, dict) and block.get("@type") == "Product":
            offer, name = block.get("offers") or {}, block.get("name") or ""
    h1 = re.search(r"^# (.+)$", markdown or "", re.M)
    origin = re.search(r"Country of origin:\s*([A-Za-z][A-Za-z .'-]+)", markdown or "")
    price = offer.get("price")
    title = name or (h1.group(1).strip() if h1 else "")
    size = all_quantities(title)
    return {
        "name": title, "price": float(price) if price not in (None, "") else 0.0,
        "in_stock": ("InStock" in str(offer.get("availability"))) if offer.get("availability") else None,
        "eans": None, "main_ean": "", "pack_size": f"{size[0].total:g} {size[0].unit}" if size else "",
        "origin": origin.group(1).strip() if origin else "",
    }


def from_actor_item(item: dict) -> Listing:
    """Row from `boring_internet_explorer/lulu-scraper`. `ean` can hold several comma-separated barcodes."""
    eans = [e.strip() for e in str(item.get("ean") or "").split(",") if e.strip()]
    main = str(item.get("mainEan") or (eans[0] if eans else "")).strip()
    content = item.get("content") or ""
    return Listing(
        retailer="lulu", title=item.get("title") or "", brand=item.get("brand") or "",
        price=float(item.get("price") or 0), regular_price=float(item.get("retailPrice") or item.get("price") or 0),
        barcode=main, quantity_text=content if parse_quantity(content).ok else "",   # 'content' is sometimes an origin
        url=item.get("url") or "", in_stock=item.get("inStock"),
        extra={"all_eans": eans, "sku": item.get("sku")},
    )
