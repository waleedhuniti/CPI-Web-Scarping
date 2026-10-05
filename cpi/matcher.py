"""Match a scraped retailer listing to a basket item.

Order of evidence (as agreed): 1) barcode, 2) quantity (hard rule - never allowed to differ), 3) name/brand.
A changed name never rejects a barcode match; a changed quantity always does.
"""
from dataclasses import dataclass, field
import re

from . import gtin
from .quantity import Quantity, find_quantity, parse_quantity, same_quantity
from .text import norm_text

NAME_ACCEPT = 0.60   # fuzzy name+brand score needed to auto-accept when there is no barcode on both sides
NAME_REVIEW = 0.35   # between REVIEW and ACCEPT goes to the human review queue

# status values
BARCODE_MATCH = "barcode_match"
BARCODE_QTY_UNVERIFIED = "barcode_match_qty_unverified"
BARCODE_NAME_CHANGED = "barcode_match_name_changed"
BARCODE_SEARCH_MATCH = "barcode_search_match"   # retailer search for the barcode returned exactly this product
QTY_MISMATCH = "qty_mismatch"
FUZZY_MATCH = "fuzzy_match"
REVIEW = "review"
NO_MATCH = "no_match"
ACCEPTED = {BARCODE_MATCH, BARCODE_NAME_CHANGED, BARCODE_SEARCH_MATCH, FUZZY_MATCH}


@dataclass
class Listing:
    """One product row scraped from a retailer, already mapped to a common schema."""
    retailer: str
    title: str
    price: float = 0.0           # price the shopper pays now (promo price when on offer)
    regular_price: float = 0.0   # list price before discount; equals `price` when no offer
    barcode: str = ""            # barcode printed on the retailer's own page/data. NEVER an internal product id
    searched_barcode: str = ""   # barcode we typed into the retailer's search box to find this listing
    result_count: int = 0        # how many products that search returned (a barcode hit should be exactly 1)
    brand: str = ""
    quantity_text: str = ""      # e.g. '500 g' as printed by the retailer
    url: str = ""
    in_stock: object = None      # True / False / None when unknown
    extra: dict = field(default_factory=dict)


@dataclass
class MatchResult:
    status: str
    score: float = 0.0
    reasons: list = field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return self.status in ACCEPTED


_TOKEN = re.compile(r"[\w؀-ۿ]+")


def _tokens(*texts) -> set:
    out = set()
    for t in texts:
        for tok in _TOKEN.findall(norm_text(t)):
            if len(tok) > 1 and not tok.isdigit():
                out.add(tok)
    return out


def name_score(item_name, item_brand, listing: Listing, aliases=None) -> float:
    """Share of basket name+brand words found in the listing title+brand. A word counts as found when it, or its
    alias (Arabic -> English, from data/aliases), appears in the listing - so each basket word is counted once."""
    a = _tokens(item_name, item_brand)
    b = _tokens(listing.title, listing.brand)
    if not a or not b:
        return 0.0
    aliases = aliases or {}
    hits = sum(1 for tok in a if tok in b or norm_text(aliases.get(tok, "")) in b)
    return hits / len(a)


def listing_quantity(listing: Listing) -> Quantity:
    q = parse_quantity(listing.quantity_text)
    return q if q.ok else find_quantity(listing.title)


def match(item, listing: Listing, aliases=None, qty_tol: float = 0.005) -> MatchResult:
    """`item` is a cpi.basket.BasketItem (or any object with the same attributes)."""
    item_q = Quantity(item.qty_raw, item.qty_unit, item.qty_total, item.qty_count, item.qty_flag)
    list_q = listing_quantity(listing)
    score = name_score(item.name_ar, item.brand_ar, listing, aliases)

    search_hit = bool(item.gtin and not listing.barcode and listing.searched_barcode
                      and gtin.same_gtin(item.gtin, listing.searched_barcode))
    if search_hit and listing.result_count != 1:
        return MatchResult(REVIEW, score, [f"barcode search returned {listing.result_count} products, expected 1"])
    if (item.gtin and listing.barcode) or search_hit:
        if listing.barcode and not gtin.same_gtin(item.gtin, listing.barcode):
            return MatchResult(NO_MATCH, score, ["barcode differs"])
        via_search = search_hit
        if list_q.ok and item_q.ok:
            if not same_quantity(item_q, list_q, qty_tol):
                return MatchResult(QTY_MISMATCH, score, [f"basket {item_q.total:g}{item_q.unit} vs listing {list_q.total:g}{list_q.unit}"])
            if via_search:
                return MatchResult(BARCODE_SEARCH_MATCH, score, ["barcode found via retailer search + quantity equal"])
            status = BARCODE_MATCH if score >= NAME_REVIEW else BARCODE_NAME_CHANGED
            return MatchResult(status, score, ["barcode + quantity equal"])
        return MatchResult(BARCODE_QTY_UNVERIFIED, score, ["barcode equal, quantity not readable on listing"])

    # no barcode on one side: quantity is still a hard rule, name has to carry the match
    if item_q.ok and list_q.ok and not same_quantity(item_q, list_q, qty_tol):
        return MatchResult(NO_MATCH, score, ["quantity differs"])
    if not (item_q.ok and list_q.ok):
        return MatchResult(REVIEW if score >= NAME_REVIEW else NO_MATCH, score, ["quantity not comparable"])
    if score >= NAME_ACCEPT:
        return MatchResult(FUZZY_MATCH, score, ["name+brand similar, quantity equal"])
    return MatchResult(REVIEW if score >= NAME_REVIEW else NO_MATCH, score, ["weak name match"])


def best_match(item, listings, aliases=None, qty_tol: float = 0.005):
    """Return (listing, result) for the best accepted/reviewable listing, or (None, MatchResult(NO_MATCH))."""
    rank = {BARCODE_MATCH: 6, BARCODE_SEARCH_MATCH: 5, BARCODE_NAME_CHANGED: 4, FUZZY_MATCH: 3, BARCODE_QTY_UNVERIFIED: 2, REVIEW: 1}
    best = (None, MatchResult(NO_MATCH))
    for lst in listings:
        res = match(item, lst, aliases, qty_tol)
        if rank.get(res.status, 0) > rank.get(best[1].status, 0) or (
            rank.get(res.status, 0) == rank.get(best[1].status, 0) and rank.get(res.status, 0) and res.score > best[1].score
        ):
            best = (lst, res)
    return best
