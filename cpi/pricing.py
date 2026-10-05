"""Price normalisation and the 'same range' rule for fresh items.

Fresh items are priced per kg (or per piece / bunch). A listing from a substitute origin (e.g. South Africa when the
basket says Egypt) is only accepted as equivalent when its unit price sits inside a band around the anchor price.
"""
from dataclasses import dataclass
from statistics import median

from .quantity import Quantity

DEFAULT_TOLERANCE = 0.30   # +/-30% around the anchor; a placeholder until the statistical officers confirm


def unit_price(price: float, qty: Quantity) -> float:
    """Price per kg for weight items, per litre for volume items, per piece/bunch otherwise."""
    if not qty.ok or price <= 0:
        return 0.0
    if qty.unit == "g":
        return price / (qty.total / 1000)
    if qty.unit == "ml":
        return price / (qty.total / 1000)
    return price / qty.total


def anchor_price(history) -> float:
    """Robust anchor: median of recent accepted unit prices for the basket origin (0 if there is no history)."""
    vals = [v for v in history if v and v > 0]
    return median(vals) if vals else 0.0


@dataclass
class BandResult:
    ok: bool
    low: float
    high: float
    ratio: float
    reason: str


def in_price_band(candidate: float, anchor: float, tolerance: float = DEFAULT_TOLERANCE) -> BandResult:
    if anchor <= 0:
        return BandResult(False, 0, 0, 0, "no anchor price - send to review")
    if candidate <= 0:
        return BandResult(False, 0, 0, 0, "no candidate price")
    low, high = anchor * (1 - tolerance), anchor * (1 + tolerance)
    ratio = candidate / anchor
    if low <= candidate <= high:
        return BandResult(True, low, high, ratio, "inside band")
    side = "above" if candidate > high else "below"
    return BandResult(False, low, high, ratio, f"{side} band ({ratio:.2f}x anchor) - different quality tier or bad parse")
