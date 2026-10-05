"""GTIN (EAN/UPC) helpers.

Excel often drops leading zeros (a 12-digit UPC-A becomes 11 digits), so every code is compared in its
canonical 14-digit zero-padded form.
"""
import re

SUPPORTED_LENGTHS = (8, 12, 13, 14)


def digits_only(value) -> str:
    return re.sub(r"\D", "", "" if value is None else str(value))


def _checksum_ok(d14: str) -> bool:
    total = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(d14[:-1]))
    return (10 - total % 10) % 10 == int(d14[-1])


def canonical(value) -> str:
    """Return the zero-padded 14-digit GTIN, or '' if the value is empty."""
    d = digits_only(value)
    return d.zfill(14) if d else ""


def is_valid_gtin(value) -> bool:
    """True if the value is a GTIN with a correct check digit (after restoring dropped leading zeros)."""
    d = digits_only(value)
    if len(d) < 8 or len(d) > 14:
        return False
    return _checksum_ok(d.zfill(14))


def classify_barcode(value) -> str:
    """'gtin' | 'store_code' (PLU / internal code / bad check digit) | 'none'."""
    d = digits_only(value)
    if not d:
        return "none"
    return "gtin" if is_valid_gtin(d) else "store_code"


def same_gtin(a, b) -> bool:
    ca, cb = canonical(a), canonical(b)
    return bool(ca) and ca == cb
