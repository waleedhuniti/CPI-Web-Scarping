"""One yes/no answer per basket line and retailer: the price is there (found) or it is not (not_found).

Barcoded lines (scripts/match_run.py statuses + the name search fallback):
  found     - the barcode search returned the product with the basket size (barcode_search_match, barcode_match,
              barcode_match_name_changed, barcode_match_unit_label, fuzzy_match), the barcode is exact but the title
              states no size (barcode_match_qty_unverified), or the name search found the same brand, product and
              exact size (name_match)
  not_found - nothing for the barcode, or another size (qty_mismatch, qty_unit_differs, qty_title_url_conflict ...)

Lines without a barcode (scripts/scrapling_category.py statuses):
  found     - the product from the basket origin (match; review_multiple takes the median listing), or the site states
              no origin and the basket has only one line for that product (review_origin)
  not_found - only another origin on sale (substitute_origin), or nothing fits (no_match)
"""
from .matcher import ACCEPTED, BARCODE_QTY_UNVERIFIED

NAME_MATCH = "name_match"
FOUND_BARCODE = set(ACCEPTED) | {BARCODE_QTY_UNVERIFIED, NAME_MATCH}
FOUND_CATEGORY = {"match", "review_multiple"}


def barcode_found(status: str) -> bool:
    return status in FOUND_BARCODE


def category_found(status: str, single_line: bool) -> bool:
    return status in FOUND_CATEGORY or (status == "review_origin" and single_line)
