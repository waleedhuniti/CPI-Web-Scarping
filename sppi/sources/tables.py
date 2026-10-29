"""Price matrices published as HTML tables (row label x column header), e.g. flydubai's excess-baggage rates by
'from' zone (rows) and 'to' zone (columns). Only tables with at least three columns are read; single-column
duplicates of the same data (mobile layout) are skipped."""
from scrapling.parser import Selector

from ..parse import money_values, table_grid, text_before


def parse(html: str, unit: str = "") -> list[dict]:
    out = []
    for table in Selector(html).css("table"):
        grid = table_grid(table)
        if len(grid) < 2 or len(grid[0]) < 3:
            continue
        head = grid[0]
        caption = " | ".join(text_before(table, 1))
        for row in grid[1:]:
            if len(set(row)) == 1:      # a footnote spanning the whole row, not a cell of the matrix
                continue
            for c in range(1, min(len(row), len(head))):
                for v in money_values(row[c]):
                    out.append(dict(item=f"{row[0]} -> {head[c]}", spec=caption, price=v, currency="AED", unit=unit,
                                    price_type="as published", price_text=f"{row[0]} | {head[c]} | {row[c]}",
                                    vat="as published", effective_date="", note=""))
    return out
