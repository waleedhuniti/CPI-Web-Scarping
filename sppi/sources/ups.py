"""UPS United Arab Emirates tariff guide (PDF): AED rates by service, direction, zone and weight.

Rate pages are laid out as text lines, e.g.

    UPS Express Plus                      <- service (the next line is an ALL-CAPS tagline)
    EARLY MORNING DELIVERY FOR ...
    UPS Express Envelopes                 <- product
    Zone 1 2 3 4 5 6 7                    <- zones of the following rows ('Zone 99' = domestic)
    AED 614 675 719 788 889 938 991       <- envelope rate
    0.5 kg 614 675 ...                    <- weight rows
    Price per kg 72 96 ...  /  Min rate 5,060 ...   (over 70 kg and Worldwide Express Freight bands)

A row is accepted only when it has exactly one value per zone; anything else is reported back as unparsed so a
layout change in a new guide is noticed instead of silently mis-read. Rates exclude VAT and the monthly fuel
surcharge (published separately on ups.com).
"""
import io
import re
from datetime import datetime

import pdfplumber

SERVICE_RE = re.compile(r"^UPS (Express Plus|Express Saver|Express|Expedited|Worldwide Express Freight(?: Midday)?)$")
DIRECTION_RE = re.compile(r"(SENDING|RECIVEING|RECEIVING) RATES\s*$")
ZONE_RE = re.compile(r"^Zone((?: \d+)+)$")
VALUES = r"((?:\s+[\d,]+(?:\.\d+)?)+)$"
WEIGHT_ROW = re.compile(r"^(\d+(?:\.\d+)? kg)" + VALUES)
ENVELOPE_ROW = re.compile(r"^AED" + VALUES)
BOX_ROW = re.compile(r"^(Up to \d+ kg)" + VALUES)
PER_KG_ROW = re.compile(r"^Price per kg" + VALUES)
MIN_ROW = re.compile(r"^Min rate" + VALUES)
BAND = re.compile(r"^(Over \d+ kg|\d+ - \d+ kg|\d+ kg or more)$")
PRODUCT = re.compile(r"^(UPS Express Envelopes|Documents .*|Packages|UPS \d+ kg Express Box.*)$")
EFFECTIVE_RE = re.compile(r"Effective from (\d{1,2} \w+ \d{4})")


def _values(text: str) -> list[float]:
    return [float(v.replace(",", "")) for v in text.split()]


def effective_date(first_page_text: str) -> str:
    m = EFFECTIVE_RE.search(first_page_text or "")
    return datetime.strptime(m.group(1), "%d %B %Y").date().isoformat() if m else ""


def parse_rate_lines(lines: list[str], effective: str = "") -> tuple[list[dict], list[str]]:
    """Rate records from the text lines of the rate pages, plus the lines that looked like rates but did not fit."""
    out, unparsed = [], []
    direction = service = product = band = ""
    zones: list[str] = []
    for i, raw in enumerate(lines):
        line = raw.strip()
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if m := DIRECTION_RE.search(line):
            direction = ("sending (export, billed in UAE)" if m.group(1) == "SENDING"
                         else "receiving (import, billed in UAE)")
            continue
        if (m := SERVICE_RE.match(line)) and nxt.isupper():
            service, product, band, zones = f"UPS {m.group(1)}", "", "", []
            continue
        if PRODUCT.match(line):
            product, band = line, ""
            continue
        if m := ZONE_RE.match(line):
            zones = m.group(1).split()
            continue
        if m := BAND.match(line):
            band = m.group(1)
            continue
        row = None
        if m := ENVELOPE_ROW.match(line):
            row = ("envelope", "per envelope", m.group(1))
        elif m := WEIGHT_ROW.match(line):
            row = (m.group(1), "per shipment", m.group(2))
        elif m := BOX_ROW.match(line):
            row = (m.group(1), "per box", m.group(2))
        elif m := PER_KG_ROW.match(line):
            row = (band or "per kg band", "per kg", m.group(1))
        elif m := MIN_ROW.match(line):
            row = (f"minimum charge{' ' + band if band else ''}", "per shipment (minimum)", m.group(1))
        if row is None:
            continue
        weight, unit, raw_values = row
        values = _values(raw_values)
        if not service or not zones or len(values) != len(zones):
            unparsed.append(f"{service or '?'} | {product or '?'} | {line}")
            continue
        for zone, v in zip(zones, values):
            zone_label = "domestic (zone 99)" if zone == "99" else f"zone {zone}"
            out.append(dict(item=f"{service} - {product or 'all'} - {weight}",
                            spec=f"{direction}; {zone_label}", price=v, currency="AED", unit=unit,
                            price_type="published tariff", price_text=line, vat="excl. VAT, excl. fuel surcharge",
                            effective_date=effective, note=""))
    return out, unparsed


# Charges on the 'ADDITIONAL SERVICES AND CHARGES' pages. Each line starts with the charge name, then the description
# and the fee run together (two-column layout), so only these names at the start of a line are read.
FEE_NAMES = ["UPS 1 Attempt Returns Plus", "UPS 3 Attempt Returns Plus", "UPS Prints and Posts Return Label",
             "UPS Print Return Label", "UPS Electronic Return Label", "Print Label", "Electronic Label",
             "Prints and Posts Label", "Proof of delivery (POD)", "Directly Delivery Only", "Freight Residential Delivery",
             "UPS Collect on Delivery (COD)", "Address Correction", "Special Handling of Undeliverable",
             "Receiver/Third Party Refuses", "Duty and Tax Forwarding Charge", "Additional Handling Charge",
             "Large Package Surcharge", "Over Maximum Limits", "Oversize Pallet Charge"]
FEE_RE = re.compile(r"(?:AED\s*(\d[\d,]*(?:\.\d+)?)|(\d[\d,]*(?:\.\d+)?)\s*AED)(.{0,40})")
FEE_UNIT = re.compile(r"per (package|shipment|pallet|undeliverable shipment|letter)")


def parse_fee_lines(lines: list[str], effective: str = "") -> list[dict]:
    out, seen = [], set()
    for line in lines:
        name = next((n for n in FEE_NAMES if line.startswith(n + " ")), None)
        m = FEE_RE.search(line) if name else None
        if not m:
            continue
        value = float((m.group(1) or m.group(2)).replace(",", ""))
        unit = FEE_UNIT.search(m.group(3) or "")
        if (name, value) in seen:
            continue
        seen.add((name, value))
        out.append(dict(item=f"UPS fee - {name}", spec="additional service / surcharge", price=value, currency="AED",
                        unit=f"per {unit.group(1)}" if unit else "", price_type="published tariff", price_text=line,
                        vat="excl. VAT", effective_date=effective, note=""))
    return out


def parse(pdf_bytes: bytes) -> tuple[list[dict], list[str], str]:
    """(records, unparsed lines, effective date) for the whole guide: rate tables plus additional charges."""
    lines, fee_lines, effective = [], [], ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        effective = effective_date(pdf.pages[0].extract_text() or "")
        for page in pdf.pages:
            text = page.extract_text() or ""
            first = text.splitlines()[0] if text else ""
            if DIRECTION_RE.search(first):
                lines.extend(text.splitlines())
            elif "ADDITIONAL SERVICES AND CHARGES" in first:
                fee_lines.extend(text.splitlines())
    records, unparsed = parse_rate_lines(lines, effective)
    return records + parse_fee_lines(fee_lines, effective), unparsed, effective
