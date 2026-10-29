"""Published 'from' air fares on the airlines' own marketing pages (no booking engine, no search requests).

* Emirates 'Flights from ...' page (emirates.com/<country>/english/flights-from-dubai/): one card per offer. The
  card link carries a code such as 'Y:DXB-BOM:AED 874*' (cabin : origin-destination : currency price); cards also say
  'Book until <date>' and the cabin / trip type. The page is built for the visitor's country: from a non-UAE network
  it lists departures from that country, so only cards whose departure is the configured airport (DXB) are kept.
  The card links themselves (featured-fares/?...airport=...) are disallowed by robots.txt and are never followed.
* flydubai route pages (flydubai.com/en-ae/flights-from-dubai-to-<city>/): 'Route information' block with
  'Lowest fare (One way)' and 'Lowest fare (Return)' in AED. The route list comes from the 'Lowest fares' page
  (flydubai.com/en-ae/flights/).
These are lowest advertised fares, not the price of a fixed flight: usable as an indicator, not a transaction price.
"""
import re
from urllib.parse import parse_qs, urlsplit

from scrapling.parser import Selector

from ..parse import clean
from . import generic

CABINS = {"F": "First Class", "J": "Business Class", "W": "Premium Economy", "Y": "Economy Class"}
EK_CODE = re.compile(r"^(?P<cabin>[A-Z]):(?P<orig>[A-Z]{3})-(?P<dest>[A-Z]{3}):(?P<cur>[A-Z]{3})\s*(?P<price>[\d,.]+)")


def emirates_featured(html: str, departure: str = "DXB") -> tuple[list[dict], set[str]]:
    """(records for cards departing from `departure`, all departure airports seen on the page)."""
    out, seen_dep = [], set()
    for li in Selector(html).css("li[data-departure]"):
        dep = li.attrib.get("data-departure", "")
        seen_dep.add(dep)
        links = li.css("a[href]")
        if not links:
            continue
        codes = parse_qs(urlsplit(links[0].attrib["href"]).query).get("intc_name", [])
        m = EK_CODE.match(codes[0]) if codes else None
        if not m or (departure and dep != departure):
            continue
        text = clean(li.get_all_text(separator=" | ", strip=True))
        parts = [p.strip() for p in text.split("|")]
        city = parts[1] if len(parts) > 1 else m.group("dest")
        until = next((p for p in parts if p.startswith("Book until")), "")
        trip = next((p for p in parts if re.search(r"Class (Return|One way)", p)), CABINS.get(m.group("cabin"), ""))
        out.append(dict(item=f"Emirates fare {m.group('orig')}-{m.group('dest')} ({city}) - {trip}",
                        spec=until, price=float(m.group("price").replace(",", "")), currency=m.group("cur"),
                        unit="per passenger, " + ("return" if "Return" in trip else "one way"),
                        price_type="lowest advertised fare ('from')", price_text=text[:300], vat="as published",
                        effective_date="", note=""))
    return out, seen_dep


def flydubai_route_links(html: str, origin: str = "dubai") -> list[str]:
    """Route pages from the 'Lowest fares' page, departures from `origin` only, in page order."""
    links = []
    for a in Selector(html).css("a[href]"):
        href = a.attrib["href"]
        if re.match(rf"^/en-ae/flights-from-{origin}-to-[a-z0-9-]+/?$", href) and href not in links:
            links.append(href)
    return links


ROUTE_RE = re.compile(r"Route information for (?P<route>.+?) Flights > Lowest fare \((?P<trip>One way|Return)\)$")


def flydubai_route(html: str) -> list[dict]:
    out = []
    for g in generic.extract(html):
        m = ROUTE_RE.search(g["context"])
        if not m:
            continue
        out.append(dict(item=f"flydubai fare {m.group('route')} - lowest fare ({m.group('trip')})", spec="",
                        price=g["price"], currency=g["currency"],
                        unit="per passenger, " + ("return" if m.group("trip") == "Return" else "one way"),
                        price_type="lowest advertised fare", price_text=g["price_text"], vat="as published",
                        effective_date="", note=""))
    return out
