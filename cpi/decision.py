"""Shared acceptance policy. Discovery and review are not CPI approval.

Keep the single_line argument for existing consumers; a unique basket line does
not verify an unknown origin. Quantity-unverified barcode hits stay in review.
"""
from .matcher import ACCEPTED

NAME_MATCH = "name_match"
FOUND_BARCODE = set(ACCEPTED) | {NAME_MATCH}
FOUND_CATEGORY = {"match"}


def barcode_found(status: str) -> bool:
    return status in FOUND_BARCODE


def category_found(status: str, single_line: bool = False) -> bool:
    return status in FOUND_CATEGORY
