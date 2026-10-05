"""Match a scraped retailer listing to a basket item.

Order of evidence (as agreed): 1) barcode, 2) quantity (hard rule - never allowed to differ), 3) name/brand.
A changed name never rejects a barcode match; a changed quantity always does.
"""
from dataclasses import dataclass, field
import re

from . import gtin
from .quantity import Quantity, all_quantities, find_quantity, pack_count, parse_quantity, same_quantity
from .text import norm_text

NAME_ACCEPT = 0.60   # fuzzy name+brand score needed to auto-accept when there is no barcode on both sides
NAME_REVIEW = 0.35   # between REVIEW and ACCEPT goes to the human review queue

# status values
BARCODE_MATCH = "barcode_match"
BARCODE_QTY_UNVERIFIED = "barcode_match_qty_unverified"
BARCODE_NAME_CHANGED = "barcode_match_name_changed"
BARCODE_SEARCH_MATCH = "barcode_search_match"   # retailer search for the barcode returned exactly this product
BARCODE_UNIT_LABEL = "barcode_match_unit_label"  # barcode equal, same number in another unit (basket 946 g, jar says 946 ml)
QTY_MISMATCH = "qty_mismatch"
QTY_UNIT_DIFFERS = "qty_unit_differs"             # barcode equal, size in a unit that cannot be compared (4 pcs vs 330 g): officer confirms
QTY_TITLE_URL_CONFLICT = "qty_title_url_conflict"  # barcode equal, retailer title says another size than its own URL: officer confirms
FUZZY_MATCH = "fuzzy_match"
REVIEW = "review"
NO_MATCH = "no_match"
ACCEPTED = {BARCODE_MATCH, BARCODE_NAME_CHANGED, BARCODE_SEARCH_MATCH, BARCODE_UNIT_LABEL, FUZZY_MATCH}


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


def listing_quantities(listing: Listing) -> list:
    """Every size the listing states: the retailer's size field when present, else all sizes in the title."""
    q = parse_quantity(listing.quantity_text)
    if q.ok:
        return [q]
    main = find_quantity(listing.title)
    return [main] + [x for x in all_quantities(listing.title) if x != main] if main.ok else []


def url_quantity(listing: Listing) -> Quantity:
    """Size written in the product URL slug ('.../president-shrded-mozrela-900gr-200g/p/871986' -> 900 g)."""
    m = re.search(r"/([^/]+)/p/[^/]+/?$", (listing.url or "").split("?")[0])
    return find_quantity(m.group(1).replace("-", " ")) if m else Quantity(raw="", flag="empty")


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
            note = ""
            if not same_quantity(item_q, list_q, qty_tol):
                why = f"basket {item_q.total:g}{item_q.unit} vs listing {list_q.total:g}{list_q.unit}"
                # same barcode, so the same pack: the title may state the size twice ('10pcs 400 g'), or the basket may
                # give the size of one piece and the piece count in the name ('علبة 24 حبة ...' 18 g -> 24 x 18 g)
                alt = next((q for q in listing_quantities(listing)[1:] if same_quantity(item_q, q, qty_tol)), None)
                n = pack_count(item.name_ar)
                if alt:
                    note = f"title also states {alt.total:g}{alt.unit}"
                elif n > 1 and item_q.unit == list_q.unit and \
                        abs(n * item_q.total - list_q.total) <= qty_tol * list_q.total:
                    note = f"basket name says {n} pieces x {item_q.total:g}{item_q.unit}"
                elif item_q.unit != list_q.unit:
                    same_no = item_q.unit in ("g", "ml") and list_q.unit in ("g", "ml") and \
                        abs(item_q.total - list_q.total) <= qty_tol * max(item_q.total, list_q.total)
                    if same_no:      # 946 g in the basket, 946 ml on the shelf: the barcode says it is the same jar
                        return MatchResult(BARCODE_UNIT_LABEL, score,
                                           [why + " - same number, different unit label; barcode identifies the pack"])
                    return MatchResult(QTY_UNIT_DIFFERS, score, [why + " - units not comparable"])
                else:
                    uq = url_quantity(listing)
                    if uq.ok and same_quantity(item_q, uq, qty_tol):
                        return MatchResult(QTY_TITLE_URL_CONFLICT, score, [why, f"but the product URL says {uq.total:g}{uq.unit}"])
                    return MatchResult(QTY_MISMATCH, score, [why])
            reasons = ["barcode found via retailer search + quantity equal" if via_search else "barcode + quantity equal"]
            reasons += [note] if note else []
            if via_search:
                return MatchResult(BARCODE_SEARCH_MATCH, score, reasons)
            return MatchResult(BARCODE_MATCH if score >= NAME_REVIEW else BARCODE_NAME_CHANGED, score, reasons)
        return MatchResult(BARCODE_QTY_UNVERIFIED, score, ["barcode equal, quantity not readable on listing"])

    # no barcode on one side: quantity is still a hard rule, name has to carry the match
    if item_q.ok and list_q.ok and not same_quantity(item_q, list_q, qty_tol):
        # without a barcode, '200ml 6 pcs' could be six 200 ml packs or one: a second size in the title is only a lead
        if any(same_quantity(item_q, q, qty_tol) for q in listing_quantities(listing)[1:]) and score >= NAME_REVIEW:
            return MatchResult(REVIEW, score, ["title gives several sizes; one equals the basket size"])
        return MatchResult(NO_MATCH, score, ["quantity differs"])
    if not (item_q.ok and list_q.ok):
        return MatchResult(REVIEW if score >= NAME_REVIEW else NO_MATCH, score, ["quantity not comparable"])
    if score >= NAME_ACCEPT:
        return MatchResult(FUZZY_MATCH, score, ["name+brand similar, quantity equal"])
    return MatchResult(REVIEW if score >= NAME_REVIEW else NO_MATCH, score, ["weak name match"])


def best_match(item, listings, aliases=None, qty_tol: float = 0.005):
    """Return (listing, result) for the best accepted/reviewable listing, or (None, MatchResult(NO_MATCH))."""
    rank = {BARCODE_MATCH: 6, BARCODE_SEARCH_MATCH: 5, BARCODE_UNIT_LABEL: 4, BARCODE_NAME_CHANGED: 4, FUZZY_MATCH: 3, BARCODE_QTY_UNVERIFIED: 2, REVIEW: 1}
    best = (None, MatchResult(NO_MATCH))
    for lst in listings:
        res = match(item, lst, aliases, qty_tol)
        if rank.get(res.status, 0) > rank.get(best[1].status, 0) or (
            rank.get(res.status, 0) == rank.get(best[1].status, 0) and rank.get(res.status, 0) and res.score > best[1].score
        ):
            best = (lst, res)
    return best
