"""RTA (Dubai Roads & Transport Authority) public fare pages.

  * nol fares  - single-journey fares by card and zone, Red Ticket fares, and the 7/30/90/365-day passes.
  * taxi fares - starting fare (flag fall) by booking channel, day and time. The page does NOT publish the per-km
                 rate or the waiting charge (it only gives the formula), so a full trip price cannot be built from it.
"""
import re

from scrapling.parser import Selector

from ..parse import clean, money_values, table_grid, text_before, to_number


def _rec(item, spec, price, unit, price_text, note=""):
    return dict(item=item, spec=spec, price=price, currency="AED", unit=unit, price_type="regulated fare",
                price_text=price_text, vat="as published", effective_date="", note=note)


def parse_nol(html: str) -> list[dict]:
    out = []
    for table in Selector(html).css("table"):
        grid = table_grid(table)
        if not grid:
            continue
        title = grid[0][0]
        if title.lower().startswith("nol red tickets"):
            # [title] / [Type, Regular, Gold] / rows
            head = [re.sub(r"\s*\(AED\)$", "", h) for h in grid[1]]
            for row in grid[2:]:
                for c in range(1, len(row)):
                    v = to_number(row[c])
                    if v is not None:
                        out.append(_rec(f"nol Red Ticket - {head[c]} - {row[0]}", "single journey", v, "per journey",
                                        f"{row[0]} | {head[c]} | {row[c]}"))
        elif title.lower().startswith("compare cards"):
            head = next(r for r in grid if r and r[0] == "Type")
            for row in grid:
                if row[0] in ("Type", title) or len(row) != len(head) or row[0].startswith("Fares"):
                    continue
                for c in range(1, len(row)):
                    v = to_number(row[c])
                    if v is not None:       # N/A, Free and 50% are concessions, not prices
                        out.append(_rec(f"nol single journey - {head[c]} - {row[0]}", "single journey", v,
                                        "per journey", f"{row[0]} | {head[c]} | {row[c]}"))
        elif title == "Product Type":
            card, zone = grid[0], grid[1]
            for row in grid[2:]:
                for c in range(1, len(row)):
                    v = to_number(row[c])
                    if v is not None:
                        out.append(_rec(f"nol pass - {card[c]} - {zone[c]} - {row[0]}", f"period pass {row[0]}", v,
                                        "per pass", f"{row[0]} | {card[c]} | {zone[c]} | {row[c]}"))
    return out


_HOUR_RE = re.compile(r"^(\d{1,2})\s*(am|pm)$", re.I)


def _hour(text: str) -> int | None:
    m = _HOUR_RE.match(clean(text))
    if not m:
        return None
    h = int(m.group(1)) % 12
    return h + 12 if m.group(2).lower() == "pm" else h


def parse_taxi(html: str) -> list[dict]:
    out = []
    for table in Selector(html).css("table"):
        grid = table_grid(table)
        if not grid or "Starting Fare" not in grid[0]:
            continue
        day, applies = (text_before(table, 2) + ["", ""])[:2]
        timed = grid[0][0] == "Start Time"
        prev_end = None
        for row in grid[1:]:
            fare = row[-1]
            when = f"{row[0]}-{row[1]}" if timed else row[0]
            note = ""
            if timed:
                start = _hour(row[0])
                if prev_end is not None and start is not None and start != prev_end:
                    note = (f"page inconsistency: previous band ends {grid[grid.index(row) - 1][1]}, "
                            f"this band starts {row[0]} - recorded as published")
                prev_end = _hour(row[1])
            parts = [p for p in fare.split("/") if money_values(p)]
            for part in parts:
                label = re.search(r"\(([^)]+)\)", part)
                kind = f" ({label.group(1)})" if label else ""
                out.append(_rec(f"Taxi starting fare{kind} - {day} - {when}", applies, money_values(part)[0],
                                "per trip (flag fall only)", f"{day} | {when} | {fare}", note))
    return out
