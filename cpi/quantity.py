"""Parse pack sizes written in Arabic or English ('1 كغ', '280غ', '4*1لتر', '30gx18', '30بيضة', 'حزمة') into a
comparable form. Quantity is the one attribute that must never change between the basket and a web listing, so
everything is reduced to a base unit: grams (g), millilitres (ml) or pieces (pc / bunch).
"""
from dataclasses import dataclass
import re

from .text import norm_text

# unit token (after norm_text) -> (base unit, factor to base)
_UNITS = {
    "kg": ("g", 1000), "kgs": ("g", 1000), "kilo": ("g", 1000), "kilogram": ("g", 1000),
    "كغ": ("g", 1000), "كلغ": ("g", 1000), "كغم": ("g", 1000), "كجم": ("g", 1000), "كيلو": ("g", 1000),
    "كيلوجرام": ("g", 1000), "كيلوغرام": ("g", 1000),
    "g": ("g", 1), "gm": ("g", 1), "gms": ("g", 1), "gr": ("g", 1), "gram": ("g", 1), "grams": ("g", 1),
    "غ": ("g", 1), "غم": ("g", 1), "جم": ("g", 1), "جرام": ("g", 1), "غرام": ("g", 1),
    "oz": ("g", 28.3495),
    "l": ("ml", 1000), "ltr": ("ml", 1000), "litre": ("ml", 1000), "litres": ("ml", 1000),
    "liter": ("ml", 1000), "liters": ("ml", 1000), "لتر": ("ml", 1000),
    "ml": ("ml", 1), "مل": ("ml", 1), "ملل": ("ml", 1),
    "حبه": ("pc", 1), "حبات": ("pc", 1), "قطعه": ("pc", 1), "بيضه": ("pc", 1), "واحده": ("pc", 1),
    "عدد": ("pc", 1), "pcs": ("pc", 1), "pc": ("pc", 1),
    "حزمه": ("bunch", 1),
}
_UNIT_RE = "|".join(sorted((re.escape(u) for u in _UNITS), key=len, reverse=True))
_NUM = r"(\d+(?:[.,]\d+)?)"


@dataclass(frozen=True)
class Quantity:
    raw: str
    unit: str = ""          # 'g' | 'ml' | 'pc' | 'bunch' | '' when unknown
    total: float = 0.0      # total in the base unit (for multipacks: count * each)
    count: int = 1          # number of units in a multipack
    flag: str = ""          # '' | 'ambiguous' | 'empty'

    @property
    def ok(self) -> bool:
        return bool(self.unit) and self.total > 0


def _f(s: str) -> float:
    return float(s.replace(",", "."))


def parse_quantity(raw) -> Quantity:
    text = norm_text(raw)
    if not text:
        return Quantity(raw="" if raw is None else str(raw), flag="empty")
    t = text.replace("×", "x").replace("*", "x")

    # '20x24' - two bare numbers, no unit -> cannot tell what is being multiplied
    if re.fullmatch(rf"{_NUM}\s*x\s*{_NUM}", t):
        return Quantity(raw=str(raw), flag="ambiguous")

    # multipack: '4x1 لتر', '5 x 75 g', '30gx18'
    m = re.fullmatch(rf"{_NUM}\s*x\s*{_NUM}\s*({_UNIT_RE})", t)
    if m:
        n, each, unit = int(_f(m[1])), _f(m[2]), _UNITS[m[3]]
        return Quantity(str(raw), unit[0], n * each * unit[1], n)
    m = re.fullmatch(rf"{_NUM}\s*({_UNIT_RE})\s*x\s*{_NUM}", t)
    if m:
        each, unit, n = _f(m[1]), _UNITS[m[2]], int(_f(m[3]))
        return Quantity(str(raw), unit[0], n * each * unit[1], n)

    # 'عدد 30' / 'حزمة 100 جرام' / '144 غرام لكل قطعه' / '1 كغ' / '30oz'
    m = re.fullmatch(rf"({_UNIT_RE})\s*{_NUM}", t)
    if m:
        unit = _UNITS[m[1]]
        return Quantity(str(raw), unit[0], _f(m[2]) * unit[1])
    m = re.fullmatch(rf"({_UNIT_RE})\s*{_NUM}\s*({_UNIT_RE})", t)  # 'حزمة 100 جرام'
    if m:
        unit = _UNITS[m[3]]
        return Quantity(str(raw), unit[0], _f(m[2]) * unit[1])
    m = re.match(rf"{_NUM}\s*({_UNIT_RE})(?:\s+لكل\s+\S+)?$", t)
    if m:
        unit = _UNITS[m[2]]
        return Quantity(str(raw), unit[0], _f(m[1]) * unit[1])

    # no number: 'حبة', 'واحدة', 'حزمة', 'ا لتر' (a typo for '1 لتر')
    if t == "ا لتر":
        return Quantity(str(raw), "ml", 1000.0)
    if t in _UNITS:
        unit = _UNITS[t]
        return Quantity(str(raw), unit[0], 1.0)
    return Quantity(str(raw), flag="ambiguous")


def same_quantity(a: Quantity, b: Quantity, rel_tol: float = 0.005) -> bool:
    """Quantities match when units agree and totals are within `rel_tol` (default 0.5%, rounding only)."""
    if not (a.ok and b.ok) or a.unit != b.unit:
        return False
    return abs(a.total - b.total) <= rel_tol * max(a.total, b.total)


_MULTI_EACH_FIRST = re.compile(rf"{_NUM}\s*({_UNIT_RE})\s*(?:pack of|x)\s*{_NUM}(?![\d.])")   # 75g pack of 5 / 30g x 18
_MULTI_COUNT_FIRST = re.compile(rf"{_NUM}\s*x\s*{_NUM}\s*({_UNIT_RE})\b")                   # 5 x 75 g
_SINGLE = re.compile(rf"(?<![\w.]){_NUM}\s*({_UNIT_RE})\b")                                 # 1 kg / 1L / 500ml / 10pcs


def all_quantities(text) -> list:
    """Every size written in a free-text title, in reading order, multipacks counted once as their total.

    'Switz Puff Pastry Squares 10pcs 400 g' -> [10 pc, 400 g];  'Maggi Chicken Stock 24 x 18 g' -> [432 g].
    """
    t = norm_text(text).replace("×", "x").replace("*", "x")
    found, taken = [], []

    def free(span):
        return all(span[1] <= a or span[0] >= b for a, b in taken)

    for m in _MULTI_EACH_FIRST.finditer(t):
        if free(m.span()):
            each, unit, n = _f(m[1]), _UNITS[m[2]], int(_f(m[3]))
            found.append((m.start(), Quantity(str(text), unit[0], n * each * unit[1], n)))
            taken.append(m.span())
    for m in _MULTI_COUNT_FIRST.finditer(t):
        if free(m.span()):
            n, each, unit = int(_f(m[1])), _f(m[2]), _UNITS[m[3]]
            found.append((m.start(), Quantity(str(text), unit[0], n * each * unit[1], n)))
            taken.append(m.span())
    for m in _SINGLE.finditer(t):
        if free(m.span()):
            unit = _UNITS[m[2]]
            found.append((m.start(), Quantity(str(text), unit[0], _f(m[1]) * unit[1])))
            taken.append(m.span())
    return [q for _, q in sorted(found, key=lambda p: p[0])]


def find_quantity(text) -> Quantity:
    """Pull the pack size out of a free-text retailer title ('Indomie ... 75g Pack of 5', 'Oil 4 Litres', 'Milk, 1L').

    A multipack wins over a single size; otherwise the first size in the title.
    """
    qs = all_quantities(text)
    multi = [q for q in qs if q.count > 1]
    return multi[0] if multi else qs[0] if qs else Quantity(str(text), flag="empty")


_PACK_COUNT = re.compile(r"(\d+)\s*(?:حبه|حبات|قطعه|قطع|مكعب|مكعبات|كيس|اكياس|pcs|pieces|cubes)\b")


def pack_count(text) -> int:
    """Number of pieces named in a basket description ('علبة 24 حبة دجاج مكعبات' -> 24), 0 when none."""
    m = _PACK_COUNT.search(norm_text(text))
    return int(m[1]) if m else 0
