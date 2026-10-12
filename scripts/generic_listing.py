"""Product cards from any store's listing or search page: link, name, price in AED, picture.

A card is the smallest element that holds one product link, one price ("AED 12.50", "12.50 AED", "د.إ 12.50") and,
usually, a picture. Used for stores without a dedicated parser (Sharaf DG, Jumbo, Emax, Zara, H&M, Centrepoint ...).

    python scripts/generic_listing.py page.html https://store.example     # prints what it finds
"""
import re
import sys
from urllib.parse import urljoin

PRICE = re.compile(r"(?:AED|د\.إ|Dhs?\.?)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)|([0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*(?:AED|د\.إ)", re.I)
SKIP_LINK = re.compile(r"/(cart|account|login|wishlist|help|stores?|search|brands?|category|categories|c)/?$|javascript:|^#|mailto:", re.I)


def _price(text):
    vals = []
    for m in PRICE.finditer(text):
        v = (m.group(1) or m.group(2) or "").replace(",", "")
        try:
            f = float(v)
        except ValueError:
            continue
        if 0 < f < 1_000_000:
            vals.append(f)
    return vals


def parse(page_html, base_url, category=""):
    from scrapling.parser import Selector
    page = Selector(page_html, url=base_url) if isinstance(page_html, str) else page_html
    out, seen = [], set()
    for a in page.css("a[href]"):
        href = a.attrib.get("href", "")
        if not href or SKIP_LINK.search(href):
            continue
        url = urljoin(base_url, href).split("#")[0]
        if url in seen or url.rstrip("/") == base_url.rstrip("/"):
            continue
        # climb to the smallest ancestor that shows a price; stop when it holds several product links
        node, card = a, None
        for _ in range(7):
            text = node.get_all_text(separator=" ", strip=True) if hasattr(node, "get_all_text") else ""
            if _price(text):
                links = {urljoin(base_url, x.attrib.get("href", "")).split("#")[0] for x in node.css("a[href]")}
                links = {l for l in links if not SKIP_LINK.search(l)}
                if len(links) <= 3:
                    card = node
                break
            node = node.parent
            if node is None:
                break
        if card is None:
            continue
        text = card.get_all_text(separator=" ", strip=True)
        prices = _price(text)
        img = card.css("img")
        src = ""
        title = ""
        for im in img:
            s = im.attrib.get("src") or im.attrib.get("data-src") or (im.attrib.get("srcset") or "").split(" ")[0]
            if s and not s.startswith("data:") and not s.endswith(".svg"):
                src = urljoin(base_url, s)
                title = title or (im.attrib.get("alt") or "").strip()
                break
        name = (a.attrib.get("title") or a.get_all_text(separator=" ", strip=True) or title).strip()
        if len(name) < 4:
            name = title or re.sub(PRICE, "", text)[:120].strip()
        name = re.sub(r"\s+", " ", name)[:200]
        if not name or not prices:
            continue
        seen.add(url)
        price = min(prices)          # the selling price when an old price is shown next to it
        out.append(dict(code=category, title=name, price=price, regular_price=max(prices), size_text="", url=url,
                        photo=src, in_stock=None))
    return out


if __name__ == "__main__":
    rows = parse(open(sys.argv[1], encoding="utf-8", errors="ignore").read(), sys.argv[2])
    print(len(rows), "products")
    for r in rows[:8]:
        print(r["price"], "|", r["title"][:70], "|", r["url"][:80], "|", bool(r["photo"]))


def parse_sharafdg(page_html, base_url, category=""):
    """Sharaf DG category / search grid: div.product-wrapper[data-sku] with the name in title=, the price in
    .product-price .price (the dirham sign is a font glyph, so the number is read from the text)."""
    from scrapling.parser import Selector
    page = Selector(page_html, url=base_url) if isinstance(page_html, str) else page_html
    out, seen = [], set()
    for card in page.css("div.product-wrapper[data-sku]"):
        sku = card.attrib.get("data-original-sku") or card.attrib.get("data-sku", "").split("_")[0]
        a = card.css("a[href]")
        if not sku or sku in seen or not a:
            continue
        price_el = card.css(".product-price .price")
        nums = re.findall(r"[0-9][0-9,]*\.?[0-9]*", price_el[0].get_all_text(separator=" ", strip=True)) if price_el else []
        if not nums:
            continue
        price = float(nums[-1].replace(",", ""))
        try:
            regular = float(card.attrib.get("data-originalprice") or price)
        except ValueError:
            regular = price
        img = card.css("img")
        seen.add(sku)
        out.append(dict(code=category, title=(card.attrib.get("title") or a[0].attrib.get("title", "")).strip(),
                        price=price, regular_price=max(price, regular), size_text="",
                        url=a[0].attrib["href"].split("?")[0], photo=img[0].attrib.get("src", "") if img else "",
                        in_stock=None, retailer_id=sku))
    return out
