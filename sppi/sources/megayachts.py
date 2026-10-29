"""Mega Yachts (megayachts.ae): one card per yacht with a 'from X AED/hr' charter price.

The card price is the lowest hourly rate ('from'); the actual quote depends on date and duration (dynamic
availability chart), so this is a list 'from' price, not a transaction price.
"""
from scrapling.parser import Selector

from ..parse import first_text, money_values


def parse(html: str) -> list[dict]:
    out = []
    for card in Selector(html).css(".item-loop"):
        name = first_text(card, ".item-title a")
        price_text = first_text(card, ".text-price")
        values = money_values(price_text)
        if not name or not values:
            continue
        spec = []
        for cls, label in (("total", "max guests"), ("bed", "cabins"), ("bath", "length")):
            value = first_text(card, f".amenity.{cls} .text")
            if value:
                spec.append(f"{label} {value}")
        prefix = first_text(card, ".g-price .prefix")
        out.append(dict(item=f"Yacht charter - {name}", spec="; ".join(spec), price=values[0], currency="AED",
                        unit="per hour", price_type=f"list price ({prefix or 'as shown'})",
                        price_text=f"{prefix} {price_text}".strip(), vat="not stated", effective_date="", note=""))
    return out
