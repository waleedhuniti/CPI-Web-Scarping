"""Generic price extraction from an HTML page: every element that prints a money amount, with its context.

For each amount the record keeps:
  * price_text - the full text of the element that prints it (what an officer sees on the page),
  * context    - the nearest heading above it and the text just before its list/table/block,
  * label      - the words in front of the amount inside the element ('Per KM Rate:', 'Daily:' ...),
  * after      - the short text right after it ('/Month 5% VAT Excluded 12 Month Contract').
Which product of the sample a page's prices belong to is decided in data/sppi/config/sppi_pages.json, not guessed here.
Amounts inside <header>, <nav> and <footer> are site chrome and are skipped unless the page config says the site
lists its prices there; the run also drops price texts that repeat on most pages of the same site (banners such as
'Trade in and save up to AED 4,500'). Table cells get their row label and column header as context.
"""
import re

from scrapling.parser import Selector

from ..parse import clean

CURRENCY = r"(?:AED|USD|EUR|GBP|SAR|Dhs?|درهم|US\$|\$|€|£)"
AMOUNT = r"\d[\d,]*(?:\.\d+)?"
MONEY = re.compile(rf"(?P<c1>{CURRENCY})\s?(?P<a1>{AMOUNT})|(?P<a2>{AMOUNT})\s?(?P<c2>AED|USD|EUR|SAR|درهم|dirhams?)\b")
CODES = {"DH": "AED", "DHS": "AED", "درهم": "AED", "DIRHAM": "AED", "DIRHAMS": "AED", "$": "USD", "US$": "USD",
         "€": "EUR", "£": "GBP"}
HEADINGS = "self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6"
CHROME = {"header", "nav", "footer"}
NEVER = {"head", "title", "script", "style", "noscript", "option", "select"}
UNIT_RE = re.compile(r"^\s*(/\s*(?:month|mo|year|yr|day|hour|hr|km|kg|min|minute|sms|user|person|pax|night|trip|week)"
                     r"[^\s,.;)]*|per\s+\w+)", re.I)


def _money(text: str):
    for m in MONEY.finditer(text):
        cur = (m.group("c1") or m.group("c2") or "").upper()
        amount = float((m.group("a1") or m.group("a2")).replace(",", ""))
        yield m, CODES.get(cur, cur), amount


def _ancestor_tags(el) -> set[str]:
    tags, node = set(), el
    for _ in range(60):
        if node is None:
            break
        tags.add(node.tag)
        node = node.parent
    return tags


def _first_text(nodes) -> str:
    for n in nodes:
        t = clean(n.get_all_text(strip=True) if hasattr(n, "get_all_text") else n)
        if t:
            return t[:120]
    return ""


def _short(text: str, limit: int) -> str:
    return text if len(text) <= limit else ""


def _table_context(el) -> list[str]:
    """Row label and column header of a table cell (only short ones: layout tables are ignored)."""
    cell = el if el.tag in ("td", "th") else (el.xpath("ancestor::td[1] | ancestor::th[1]") or [None])[0]
    if cell is None:
        return []
    row = cell.parent
    cells = list(row.css("th,td"))
    idx = next((i for i, c in enumerate(cells) if c.get_all_text(strip=True) == cell.get_all_text(strip=True)), 0)
    table = (cell.xpath("ancestor::table[1]") or [None])[0]
    head = ""
    if table is not None:
        first = table.css("tr")
        if first:
            hcells = list(first[0].css("th,td"))
            if len(hcells) == len(cells) and idx < len(hcells) and first[0] != row:
                head = clean(hcells[idx].get_all_text(strip=True))
    row_label = clean(cells[0].get_all_text(strip=True)) if cells and idx > 0 else ""
    return [t for t in (_short(row_label, 60), _short(head, 60)) if t and not MONEY.search(t)]


def _own_text(el) -> str:
    return clean(" ".join(str(t) for t in el.xpath("text()")))


def _siblings_before(node, n: int = 2) -> list[str]:
    texts = []
    for sib in node.xpath("preceding-sibling::*[not(self::ul or self::ol)][normalize-space()]")[::-1][:n]:
        t = clean(sib.get_all_text(separator=" ", strip=True))
        if MONEY.search(t):
            break
        texts.append(t)
    return texts


def context_of(el) -> list[str]:
    """Nearest heading, the short text(s) just before the element or its outermost list ('Mobile Application',
    a card title), labels of enclosing list items ('All Weekdays', 'Friday') and, for table cells, the row label
    and column header."""
    heading = _short(_first_text(el.xpath(f"preceding::*[{HEADINGS}][1]")), 80)
    outer_list = el.xpath("ancestor::ul[last()] | ancestor::ol[last()]")
    candidates = [el] + outer_list[:1]
    node = el.parent
    for _ in range(4):
        if node is None:
            break
        candidates.append(node)
        node = node.parent
    before = []
    for node in candidates:
        before = _siblings_before(node)
        if before:
            break
    before = [t[:100] for t in before[::-1] if len(t) <= 160]
    items = [_short(_own_text(li), 60) for li in el.xpath("ancestor::li")]
    out = []
    for t in [heading] + before + items + _table_context(el):
        if t and t not in out and not MONEY.search(t):
            out.append(t)
    return out


TAGS = "div,span,p,li,td,th,a,strong,b,em,label,h1,h2,h3,h4,h5,h6,dd,dt,small,button"


def price_elements(page, include_chrome: bool):
    """The smallest elements whose combined text shows a money amount (so '1,095' + 'AED/Month' in two spans is
    still one price), skipping the page head and, unless asked, header/nav/footer."""
    for el in page.css(TAGS):
        text = clean(el.get_all_text(separator=" ", strip=True))
        if not text or len(text) > 400 or not MONEY.search(text):
            continue
        if any(MONEY.search(clean(c.get_all_text(separator=" ", strip=True))) for c in el.children):
            continue
        tags = _ancestor_tags(el)
        if tags & NEVER or (not include_chrome and tags & CHROME):
            continue
        yield el, text


def text_after(el) -> str:
    """Short text right after the price element inside the same block ('/Month 5% VAT Excluded'): its next sibling,
    when that is not a heading or a list item (those start the next entry)."""
    node, text = el, clean(el.get_all_text(separator=" ", strip=True))
    # climb through wrappers that hold nothing but the price (<div><span>AED 88</span></div>)
    while not node.xpath("following-sibling::*[normalize-space()]") and node.parent is not None and \
            clean(node.parent.get_all_text(separator=" ", strip=True)) == text:
        node = node.parent
    for sib in node.xpath("following-sibling::*[normalize-space()][position() <= 1]"):
        if sib.tag in ("h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol", "table"):
            return ""
        t = clean(sib.get_all_text(separator=" ", strip=True))
        if t and len(t) <= 100 and not MONEY.search(t):
            return t
    return ""


def extract(html: str, include_chrome: bool = False) -> list[dict]:
    """include_chrome: also read <header>/<nav>/<footer> (some sites list their prices in the menu)."""
    page = Selector(html)
    out, seen = [], set()
    for el, text in price_elements(page, include_chrome):
        ctx = context_of(el)
        after = text_after(el)
        prev_end = 0
        for m, cur, amount in _money(text):
            label = clean(text[prev_end:m.start()]).strip("-–→:|•()/ ")
            unit = UNIT_RE.match(text[m.end():]) or UNIT_RE.match(after)
            prev_end = m.end()
            key = (tuple(ctx), text, m.start())
            if key in seen:
                continue
            seen.add(key)
            out.append(dict(context=" > ".join(ctx), label=label[-120:], after=after, price=amount, currency=cur,
                            unit=clean(unit.group(1)) if unit else "", price_text=text[:400]))
    return out
