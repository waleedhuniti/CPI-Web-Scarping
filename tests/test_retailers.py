import json
from pathlib import Path

import pytest

from cpi.matcher import (BARCODE_QTY_UNVERIFIED, BARCODE_SEARCH_MATCH, QTY_MISMATCH, REVIEW, Listing, match)
from cpi.quantity import find_quantity
from cpi.retailers import carrefour, lulu

FX = Path(__file__).parent / "fixtures"
TILDA = "8901144311002"


def read(name):
    return (FX / name).read_text(encoding="utf-8")


class Item:  # minimal stand-in for cpi.basket.BasketItem
    def __init__(self, **kw):
        base = dict(name_ar="أرز بسمتي هندي", brand_ar="تلدا", gtin="0" + TILDA, qty_raw="1 كغ",
                    qty_unit="g", qty_total=1000.0, qty_count=1, qty_flag="")
        base.update(kw)
        self.__dict__.update(base)


# ---- find_quantity (titles as printed by the retailers in the pilot) -----------------------------------
@pytest.mark.parametrize("title,unit,total,count", [
    ("Tilda Pure Original Basmati Rice 1 kg", "g", 1000, 1),
    ("Tilda Pure Basmati Rice, 1kg", "g", 1000, 1),
    ("Almarai Full Fat Fresh Milk, 1L", "ml", 1000, 1),
    ("RS Refined Olive Pomace Oil Blended with Extra Virgin Olive Oil 4 Litres", "ml", 4000, 1),
    ("Indomie Special Chicken Instant Noodles, 75g Pack of 5", "g", 375, 5),
    ("Almarai Full Fat Long Life Milk 4 x 1 Litre", "ml", 4000, 4),
    ("SIS Fine Grain Granulated White Sugar, 2kg", "g", 2000, 1),
])
def test_find_quantity_in_titles(title, unit, total, count):
    q = find_quantity(title)
    assert (q.unit, q.total, q.count) == (unit, total, count)


# ---- Lulu ----------------------------------------------------------------------------------------------
def test_lulu_search_url():
    assert lulu.search_url(TILDA) == "https://gcc.luluhypermarket.com/en-ae/list/?search_text=8901144311002"


def test_lulu_barcode_hit_parsed():
    (lst,) = lulu.parse_search_markdown(read("lulu_hit_tilda.md"), TILDA)
    assert lst.title == "Tilda Pure Original Basmati Rice 1 kg"
    assert (lst.price, lst.regular_price) == (16.75, 16.75)
    assert lst.url == "https://gcc.luluhypermarket.com/en-ae/tilda-pure-original-basmati-rice-1-kg/p/10962/"
    assert lst.searched_barcode == TILDA and lst.result_count == 1 and lst.barcode == ""


def test_lulu_promo_keeps_both_prices():
    (lst,) = lulu.parse_search_markdown(read("lulu_hit_discount_rs_oil.md"), "8420701103077")
    assert lst.price == 105.00 and lst.regular_price == 238.95 and lst.extra["discount_pct"] == 56


def test_lulu_no_results_is_empty_not_error():
    assert lulu.parse_search_markdown(read("lulu_no_results.md"), "6291038010008") == []


def test_lulu_actor_item_splits_multiple_eans_and_ignores_origin_in_content():
    item = json.loads(read("lulu_actor_item.json"))
    lst = lulu.from_actor_item(item)
    assert lst.barcode == "6281007032391" and lst.extra["all_eans"] == ["6281007032391", "6281007054652"]
    assert (lst.price, lst.regular_price) == (16.5, 19.25)
    assert lulu.from_actor_item({**item, "content": "Jordan", "title": "Choco 450 g"}).quantity_text == ""


# ---- Carrefour -----------------------------------------------------------------------------------------
def test_carrefour_search_url_and_actor_input():
    assert carrefour.search_url(TILDA).endswith("search?keyword=8901144311002")
    inp = carrefour.actor_input([TILDA, "6291038010008"])
    assert inp["market"] == "mafuae" and json.loads(inp["query"]) == [TILDA, "6291038010008"]


def test_carrefour_search_page_parsed():
    (lst,) = carrefour.parse_search_markdown(read("carrefour_search_tilda.md"), TILDA)
    assert lst.title == "Tilda Pure Basmati Rice, 1kg" and lst.price == 17.79
    assert lst.url.endswith("/p/79241") and lst.extra["product_id"] == "79241" and lst.result_count == 1


def test_carrefour_internal_id_is_never_used_as_barcode():
    lst = carrefour.from_actor_item(json.loads(read("carrefour_actor_item.json")))
    assert lst.barcode == ""                      # item['gtin'] == '79241' is Carrefour's own product id
    assert lst.searched_barcode == TILDA


def test_carrefour_result_counts_per_barcode():
    a = carrefour.from_actor_item({"title": "A 1kg", "searchQuery": TILDA, "price": 1})
    b = carrefour.from_actor_item({"title": "B 1kg", "searchQuery": TILDA, "price": 1})
    c = carrefour.from_actor_item({"title": "C 1kg", "searchQuery": "6291038010008", "price": 1})
    carrefour.mark_result_counts([a, b, c])
    assert (a.result_count, b.result_count, c.result_count) == (2, 2, 1)


# ---- end to end: basket item vs what the retailers returned --------------------------------------------
def test_tilda_matches_at_both_retailers_by_barcode_search():
    (lulu_l,) = lulu.parse_search_markdown(read("lulu_hit_tilda.md"), TILDA)
    (carr_l,) = carrefour.parse_search_markdown(read("carrefour_search_tilda.md"), TILDA)
    for lst in (lulu_l, carr_l):
        res = match(Item(), lst)
        assert res.status == BARCODE_SEARCH_MATCH and res.accepted


def test_search_hit_with_other_size_is_rejected():
    lst = Listing("carrefour", "Tilda Pure Basmati Rice, 5kg", searched_barcode=TILDA, result_count=1)
    assert match(Item(), lst).status == QTY_MISMATCH


def test_search_returning_several_products_goes_to_review():
    lst = Listing("carrefour", "Tilda Pure Basmati Rice, 1kg", searched_barcode=TILDA, result_count=3)
    assert match(Item(), lst).status == REVIEW


def test_search_hit_without_readable_size_is_not_silently_accepted():
    lst = Listing("lulu", "Tilda Pure Basmati Rice", searched_barcode=TILDA, result_count=1)
    res = match(Item(), lst)
    assert res.status == BARCODE_QTY_UNVERIFIED and not res.accepted


# ---- found in the 2026-10-05 full Carrefour run ---------------------------------------------------------
def test_same_number_different_unit_label_is_accepted_on_its_own_status():
    from cpi.matcher import BARCODE_UNIT_LABEL
    item = Item(gtin="0" + TILDA, qty_raw="946غ", qty_unit="g", qty_total=946.0)        # basket: mayonnaise 946 g
    lst = Listing("carrefour", "Noor Original Thick & Creamy Mayonnaise Jar, 946ml", searched_barcode=TILDA, result_count=1)
    res = match(item, lst)
    assert res.status == BARCODE_UNIT_LABEL and res.accepted and "same number" in res.reasons[0]


def test_title_with_pieces_and_weight_matches_on_the_weight():
    item = Item(qty_raw="400g", qty_unit="g", qty_total=400.0)                          # Lulu 2026-10-05
    lst = Listing("lulu", "Switz Puff Pastry Squares 10pcs 400 g", searched_barcode=TILDA, result_count=1)
    res = match(item, lst)
    assert res.accepted and "also states 400g" in res.reasons[-1]


def test_basket_piece_count_times_piece_size_equals_the_box():
    item = Item(name_ar="علبة 24 حبة دجاج مكعبات", qty_raw="18 جم", qty_unit="g", qty_total=18.0)
    lst = Listing("lulu", "Maggi Chicken Stock 24 x 18 g", searched_barcode=TILDA, result_count=1)
    res = match(item, lst)
    assert res.accepted and "24 pieces" in res.reasons[-1]


def test_second_size_in_title_is_only_a_lead_without_barcode():
    from cpi.matcher import NO_MATCH
    item = Item(gtin="", qty_raw="200 مل", qty_unit="ml", qty_total=200.0)
    lst = Listing("lulu", "Mai Dubai Water 1.5 L 6 pcs")                                # no barcode, sizes differ
    assert match(item, lst).status in (NO_MATCH, REVIEW) and not match(item, lst).accepted


def test_pieces_vs_grams_cannot_be_compared():
    from cpi.matcher import QTY_UNIT_DIFFERS
    item = Item(qty_raw="4 حبة", qty_unit="pc", qty_total=4.0)
    lst = Listing("carrefour", "Modern Bakery Sandwich Roll Sesame, 330g", searched_barcode=TILDA, result_count=1)
    res = match(item, lst)
    assert res.status == QTY_UNIT_DIFFERS and "not comparable" in res.reasons[0]


def test_title_and_url_disagree_on_size_goes_to_review():
    from cpi.matcher import QTY_TITLE_URL_CONFLICT
    item = Item(qty_raw="900غ", qty_unit="g", qty_total=900.0)
    lst = Listing("carrefour", "President Natural Mozzarella Cheese Shredded, 1.1kg", searched_barcode=TILDA, result_count=1,
                  url="https://www.carrefouruae.com/mafuae/en/shredded-grated-cheese/president-shrded-mozrela-900gr-200g/p/871986")
    res = match(item, lst)
    assert res.status == QTY_TITLE_URL_CONFLICT and not res.accepted


def test_genuine_size_change_is_still_rejected():
    item = Item(qty_raw="170جم", qty_unit="g", qty_total=170.0)                          # shrinkflation: 170 g -> 165 g
    lst = Listing("carrefour", "Lay’s Salt Potato Chips 165g", searched_barcode=TILDA, result_count=1,
                  url="https://www.carrefouruae.com/mafuae/en/chips/lay-s-chips-salt-155g/p/6498")
    assert match(item, lst).status == QTY_MISMATCH


# ---- cheap-mode (cheerio) pages captured 2026-10-05 -------------------------------------------------------
def test_carrefour_unit_price_is_not_taken_as_regular_price():
    ls = carrefour.parse_search_markdown(read("carrefour_search_en_tilda_cheerio.md"), "tilda basmati rice")
    first = ls[0]
    assert (first.title, first.price, first.regular_price) == ("Tilda Pure Basmati Rice, 1kg", 17.79, 17.79)
    steamed = next(l for l in ls if "Steamed" in l.title)
    assert steamed.price == 11.99 and steamed.regular_price == 11.99          # was wrongly 47.96 (= AED per kg)
    assert steamed.extra["unit_price"] == 47.96 and steamed.extra["unit_basis"] == "Kilo"
    assert first.searched_barcode == ""                                         # a text search is not barcode evidence


def test_carrefour_offer_price_and_was_price_in_arabic_page():
    ls = carrefour.parse_search_markdown(read("carrefour_search_ar_rice_cheerio.md"), "تلدا ارز بسمتي")
    pharoes = ls[0]
    assert pharoes.title == "فاروس أرز مصري، 5 كلغ"
    assert (pharoes.price, pharoes.regular_price, pharoes.extra["unit_price"]) == (21.99, 28.99, 4.40)
    assert find_quantity(pharoes.title).total == 5000


def test_carrefour_product_page_price_size_origin():
    import json as _j
    info = carrefour.parse_product_page(read("carrefour_product_tilda_cheerio.md"),
                                        _j.loads(read("carrefour_product_tilda_jsonld.json")))
    assert (info["price"], info["in_stock"], info["sku"]) == (17.79, True, "79241")
    assert info["pack_size"] == "1kg" and info["origin"] == "India"


def test_lulu_name_search_page():
    ls = lulu.parse_search_markdown(read("lulu_search_name_tilda_cheerio.md"), "tilda basmati")
    assert len(ls) == 20 and ls[0].result_count == 61
    assert ("Tilda Pure Original Basmati Rice 1 kg", 16.75) in [(l.title, l.price) for l in ls]


def test_lulu_product_page_gives_real_eans_price_and_size():
    p = lulu.parse_product_page(read("lulu_product_tilda_record.txt"),
                                json.loads(read("lulu_product_tilda_jsonld.json")))
    assert TILDA in p["eans"] and p["main_ean"] == TILDA and len(p["eans"]) == 3
    assert p["price"] == 16.75 and p["in_stock"] is True and p["pack_size"] == "1 kg" and p["origin"] == "India"


def test_fresh_search_cards_give_price_per_kg():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    from name_search import page_listings
    ls = {x["title"]: x for x in page_listings("carrefour", read("carrefour_search_lamb_leg_cheerio.md"), "lamb leg")}
    leg = ls["Australian Lamb Leg Import"]                       # 'AED181.97 2.60KG Min Order: 2 kg'
    assert leg["price"] == 181.97 and leg["priced_size"] == "2600g" and leg["price_per_kg"] == 69.99
    assert ls["Australian Lamb Leg Deboned Import"]["price_per_kg"] == 88.0   # 'AED44.00 500g - Approx 2 pieces/KG'


def test_lulu_weighed_items_without_slug_are_read():
    # fresh meat cards link to '.../en-ae/p/154716-ea/?convtobuom=500' (no product name in the URL)
    ls = lulu.parse_search_markdown(read("lulu_search_mutton_cheerio.md"), "mutton pakistan")
    first = ls[0]
    assert first.title == "Pakistani Mutton Cuts Bone In 500 g" and first.price == 27.25
    assert first.url == "https://gcc.luluhypermarket.com/en-ae/p/154716-ea/"


def test_scrapling_card_parsers():
    """Search-page HTML in the shape Carrefour and Lulu serve (trimmed to one card each)."""
    import importlib.util
    if importlib.util.find_spec("scrapling") is None:
        import pytest
        pytest.skip("scrapling not installed")
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    from scrapling.parser import Selector
    import scrapling_search as ss

    c = Selector('<div><div><a href="/mafuae/en/rice/tilda-basmati-rice-1kg/p/79241?offer=x">Tilda Pure Basmati Rice, 1kg</a></div>'
                 '<div><span>AED</span><span>17.79</span></div><span>1kg</span></div>')
    rows = ss.parse_carrefour(c, "8901144311002")
    assert rows == [dict(searched_barcode="8901144311002", product_id="79241", title="Tilda Pure Basmati Rice, 1kg",
                         price=17.79, regular_price=17.79, in_stock=None,
                         url="https://www.carrefouruae.com/mafuae/en/rice/tilda-basmati-rice-1kg/p/79241",
                         unit_price=0.0, size_text="1kg")]
    lu = Selector('<div><a href="/en-ae/sinnara-rice-5-kg/p/123-ch1/?">Sinnara Rice 5 kg</a>'
                  '<span data-testid="product-price">38.90 </span><span class="line-through">43.95</span></div>')
    rows = ss.parse_lulu(lu, "6294000201053")
    assert rows[0]["price"] == 38.9 and rows[0]["regular_price"] == 43.95
    assert rows[0]["url"] == "https://gcc.luluhypermarket.com/en-ae/sinnara-rice-5-kg/p/123-ch1/"
