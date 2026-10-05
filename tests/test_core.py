import pytest

from cpi import gtin
from cpi.origin import origin_iso
from cpi.pricing import anchor_price, in_price_band, unit_price
from cpi.quantity import parse_quantity, same_quantity
from cpi.matcher import (BARCODE_MATCH, BARCODE_NAME_CHANGED, BARCODE_QTY_UNVERIFIED, FUZZY_MATCH, NO_MATCH,
                         QTY_MISMATCH, REVIEW, Listing, best_match, match)


# ---- GTIN ----------------------------------------------------------------------------------------------
def test_valid_ean13_and_checksum():
    assert gtin.is_valid_gtin("8901144311002")
    assert not gtin.is_valid_gtin("8901144311003")


def test_upca_with_dropped_leading_zero_is_still_valid_and_equal():
    # Excel turned 012345678905 (UPC-A) into 11 digits
    assert gtin.is_valid_gtin("12345678905")
    assert gtin.same_gtin("12345678905", "0012345678905")


def test_plu_and_internal_codes_are_not_gtins():
    assert gtin.classify_barcode("3161") == "store_code"        # Waitrose pork PLU in the basket
    assert gtin.classify_barcode("995098000006") == "store_code"  # fresh squid, bad check digit
    assert gtin.classify_barcode(None) == "none"


# ---- quantity ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("raw,unit,total,count", [
    ("1 كغ", "g", 1000, 1), ("5 كغ", "g", 5000, 1), ("280غ", "g", 280, 1), ("1100 غ", "g", 1100, 1),
    ("500 g", "g", 500, 1), ("1 kg", "g", 1000, 1), ("1كيلو", "g", 1000, 1), ("750 مل", "ml", 750, 1),
    ("ا لتر", "ml", 1000, 1), ("1 لتر", "ml", 1000, 1), ("4*1لتر", "ml", 4000, 4), ("5 x 75 g", "g", 375, 5),
    ("30gx18", "g", 540, 18), ("30oz", "g", pytest.approx(850.485), 1), ("30بيضة", "pc", 30, 1),
    ("عدد 6", "pc", 6, 1), ("6 حبات", "pc", 6, 1), ("حبة", "pc", 1, 1), ("واحدة", "pc", 1, 1),
    ("حزمة", "bunch", 1, 1), ("حزمة 100 جرام", "g", 100, 1), ("144 غرام لكل قطعه", "g", 144, 1),
    ("٥٠٠ غ", "g", 500, 1),
])
def test_parse_quantity(raw, unit, total, count):
    q = parse_quantity(raw)
    assert (q.unit, q.total, q.count) == (unit, total, count)


def test_ambiguous_quantity_is_flagged_not_guessed():
    q = parse_quantity("20*24")
    assert not q.ok and q.flag == "ambiguous"
    assert parse_quantity("").flag == "empty"


def test_same_quantity_ignores_unit_spelling_but_not_size():
    assert same_quantity(parse_quantity("1 كغ"), parse_quantity("1000 g"))
    assert same_quantity(parse_quantity("903غ"), parse_quantity("0.9 kg"), rel_tol=0.01)
    assert not same_quantity(parse_quantity("400غ"), parse_quantity("450 g"))
    assert not same_quantity(parse_quantity("1 لتر"), parse_quantity("1 كغ"))   # volume vs weight


# ---- origin --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("raw,iso", [
    ("الإمارات", "AE"), ("الامارات", "AE"), ("uae", "AE"), ("الامات", "AE"), ("سعودية", "SA"), ("امريكا", "US"),
    ("أمريكا", "US"), ("USA", "US"), ("جنوب أفريقيا", "ZA"), ("جنوب افريقيا", "ZA"), ("المملكة المتحدة", "GB"),
    ("افريقيا", "AFRICA"), ("", ""), ("كوكب المريخ", "UNKNOWN"),
])
def test_origin_iso(raw, iso):
    assert origin_iso(raw) == iso


# ---- matcher -------------------------------------------------------------------------------------------
class Item:  # minimal stand-in for cpi.basket.BasketItem
    def __init__(self, **kw):
        base = dict(name_ar="أرز بسمتي هندي", brand_ar="تلدا", gtin="08901144311002", qty_raw="1 كغ",
                    qty_unit="g", qty_total=1000.0, qty_count=1, qty_flag="")
        base.update(kw)
        self.__dict__.update(base)


ALIASES = {"تلدا": "tilda", "ارز": "rice", "بسمتي": "basmati", "هندي": "indian"}


def test_barcode_match_ignores_changed_name():
    r = match(Item(), Listing("lulu", "Tilda Pure Original Basmati", barcode="8901144311002", quantity_text="1 kg"), ALIASES)
    assert r.status in (BARCODE_MATCH, BARCODE_NAME_CHANGED) and r.accepted


def test_barcode_equal_but_quantity_changed_is_rejected():
    r = match(Item(), Listing("lulu", "Tilda Basmati Rice", barcode="8901144311002", quantity_text="900 g"), ALIASES)
    assert r.status == QTY_MISMATCH and not r.accepted


def test_barcode_equal_quantity_not_readable_is_flagged_not_accepted_silently():
    r = match(Item(), Listing("lulu", "Tilda Basmati Rice", barcode="8901144311002"), ALIASES)
    assert r.status == BARCODE_QTY_UNVERIFIED and not r.accepted


def test_different_barcode_is_no_match():
    r = match(Item(), Listing("lulu", "Tilda Basmati Rice 1kg", barcode="6291100207497", quantity_text="1 kg"), ALIASES)
    assert r.status == NO_MATCH


def test_quantity_read_from_title_when_field_missing():
    r = match(Item(), Listing("lulu", "Tilda Basmati Rice 1kg", barcode="8901144311002"), ALIASES)
    assert r.status in (BARCODE_MATCH, BARCODE_NAME_CHANGED)


def test_no_barcode_needs_name_and_exact_quantity():
    item = Item(gtin="", name_ar="أرز بسمتي هندي", brand_ar="تلدا")
    good = Listing("carrefour", "Tilda Indian Basmati Rice", quantity_text="1 kg")
    wrong_size = Listing("carrefour", "Tilda Indian Basmati Rice", quantity_text="2 kg")
    vague = Listing("carrefour", "Some other grain", quantity_text="1 kg")
    assert match(item, good, ALIASES).status == FUZZY_MATCH
    assert match(item, wrong_size, ALIASES).status == NO_MATCH
    assert match(item, vague, ALIASES).status == NO_MATCH


def test_best_match_prefers_barcode_hit():
    lst = [Listing("a", "Tilda Indian Basmati Rice", quantity_text="1 kg"),
           Listing("a", "Tilda Basmati", barcode="8901144311002", quantity_text="1 kg")]
    chosen, res = best_match(Item(), lst, ALIASES)
    assert chosen is lst[1] and res.accepted
    assert best_match(Item(), [], ALIASES)[1].status == NO_MATCH


# ---- price band (the Egypt vs South Africa orange rule) -----------------------------------------------
def test_unit_price_per_kg():
    assert unit_price(6.0, parse_quantity("500 g")) == pytest.approx(12.0)
    assert unit_price(9.0, parse_quantity("1.5 لتر")) == pytest.approx(6.0)
    assert unit_price(3.0, parse_quantity("حبة")) == 3.0


def test_south_africa_orange_at_same_price_is_accepted_but_ten_times_is_not():
    egypt_anchor = anchor_price([3.0, 3.2, 2.9, 3.1])
    assert in_price_band(3.4, egypt_anchor).ok                 # South Africa, same range -> counts as the Egypt line
    far = in_price_band(30.0, egypt_anchor)
    assert not far.ok and "above band" in far.reason           # 30 AED vs 3 AED -> never enters the index


def test_missing_anchor_goes_to_review_not_accepted():
    assert not in_price_band(3.0, anchor_price([])).ok


def test_english_origin_names_and_africa_rule():
    from cpi.origin import origin_iso_en, same_origin
    assert origin_iso_en("Orange Navel South Africa 1 kg") == "ZA"
    assert origin_iso_en("Lime Egypt 250 g") == "EG" and origin_iso_en("Red Apple 1 kg") == ""
    assert same_origin("AFRICA", "ZA") and not same_origin("AFRICA", "EG") and not same_origin("EG", "ZA")
