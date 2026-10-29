"""Small parsing helpers shared by the source parsers: HTML tables -> grids, money strings -> numbers."""
import re

MONEY_RE = re.compile(r"(?:AED|Dhs?\.?|درهم)\s*([\d,]+(?:\.\d+)?)|([\d,]+(?:\.\d+)?)\s*(?:AED|Dhs?\b|درهم)", re.I)
NUMBER_RE = re.compile(r"^\s*([\d,]+(?:\.\d+)?)\s*$")


def to_number(text: str) -> float | None:
    """'1,049' -> 1049.0; anything that is not a plain number (N/A, Free, 50%) -> None."""
    m = NUMBER_RE.match(text or "")
    return float(m.group(1).replace(",", "")) if m else None


def money_values(text: str) -> list[float]:
    """Every AED amount in a string: 'AED 20 (Normal) / AED 25 (Van)' -> [20.0, 25.0]; '8 AED' -> [8.0]."""
    return [float((a or b).replace(",", "")) for a, b in MONEY_RE.findall(text or "")]


def clean(text) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def first_text(element, css: str) -> str:
    """Text of the first match of a CSS selector inside an element ('' when there is none)."""
    found = element.css(css)
    return clean(found[0].get_all_text(strip=True)) if found else ""


def table_grid(table) -> list[list[str]]:
    """A Scrapling <table> element as a rectangular grid of cell texts, with rowspan/colspan expanded."""
    grid, pending = [], {}          # pending: (row, col) -> text carried down by a rowspan
    for r, tr in enumerate(table.css("tr")):
        row, col = [], 0
        cells = list(tr.css("th,td"))
        while cells or (r, col) in pending:
            if (r, col) in pending:
                row.append(pending.pop((r, col)))
                col += 1
                continue
            cell = cells.pop(0)
            text = clean(cell.get_all_text(strip=True))
            rs, cs = int(cell.attrib.get("rowspan") or 1), int(cell.attrib.get("colspan") or 1)
            for k in range(cs):
                row.append(text)
                for d in range(1, rs):
                    pending[(r + d, col + k)] = text
            col += cs
        grid.append(row)
    return grid


def text_before(element, n: int = 2) -> list[str]:
    """The last n non-empty text nodes before an element in document order (its heading / caption lines)."""
    nodes = [clean(t) for t in element.xpath("preceding::text()[normalize-space()]")]
    return [t for t in nodes if t][-n:]
