"""Reject prices that cannot be the basket line: a price far from the official price of the same line is a wrong product
(AirPods for a pair of headphones, a tomato sharing box for a kilo of tomatoes, a coconut for a pineapple).

    official_prices.json: item_code -> official price (July file), in the line's own unit (the one 'price' is stored in)
A price below 0.4x or above 2.5x of it is rejected; rows keep the rejected price in 'price_rejected'.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOW, HIGH = 0.4, 2.5


def load():
    f = ROOT / "data/basket/official_prices.json"
    return json.load(open(f)) if f.exists() else {}


def apply(rows, official=None):
    """Blanks price / unit_price of implausible rows (status 'implausible', accepted 'no'); returns how many."""
    off = official if official is not None else load()
    n = 0
    for r in rows:
        try:
            p = float(r.get("price") or 0)
        except ValueError:
            continue
        o = off.get(str(r.get("item_code")))
        if p <= 0 or not o or o <= 0 or LOW <= p / o <= HIGH:
            continue
        r["price_rejected"] = r["price"]
        r["price"] = ""
        r["unit_price"] = ""
        r["status"] = "implausible"
        r["accepted"] = "no"
        r["note"] = (str(r.get("note") or "") + f" · price {p:g} is {p / o:.1f}x the official {o:g}: rejected").strip(" ·")
        n += 1
    return n
