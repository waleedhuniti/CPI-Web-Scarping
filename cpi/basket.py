"""Load the CPI basket workbook (Arabic, COICOP-coded) into flat, machine-friendly rows.

The sheet interleaves hierarchy rows (codes of 1-7 digits, no brand/barcode/origin/qty) with priced item rows
(9-digit code). We keep the 4-digit group and 7-digit class on every item so retailers can be searched per class.
"""
from dataclasses import dataclass, asdict
import csv
import json
from pathlib import Path

import openpyxl

from . import gtin
from .origin import origin_iso
from .quantity import parse_quantity

# 4-digit COICOP groups that are sold fresh / by weight and mostly carry no barcode
FRESH_GROUPS = {"0112": "meat", "0113": "seafood", "0116": "fruit", "0117": "vegetable"}


def _s(v) -> str:
    return "" if v is None else str(v).strip()


@dataclass
class BasketItem:
    item_code: str       # 9-digit code from the sheet
    class_code: str      # 7-digit COICOP class
    class_name: str
    group_code: str      # 4-digit COICOP group
    group_name: str
    name_ar: str
    brand_ar: str
    barcode_raw: str
    gtin: str            # canonical 14-digit GTIN, '' unless barcode_kind == 'gtin'
    barcode_kind: str    # 'gtin' | 'store_code' | 'none'
    origin_raw: str
    origin_iso: str
    qty_raw: str
    qty_unit: str        # g | ml | pc | bunch | ''
    qty_total: float
    qty_count: int
    qty_flag: str
    match_mode: str      # 'barcode' | 'spec' (no usable barcode: match on name+brand+qty / commodity spec)
    fresh_type: str      # meat | seafood | fruit | vegetable | ''


def load_basket(path) -> list:
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    names, items = {}, []
    group = klass = ""
    for _, code, name, brand, barcode, origin, qty in ws.iter_rows(min_row=3, values_only=True):
        code = _s(code)
        if not code:
            continue
        if brand is None and barcode is None and origin is None and qty is None:  # hierarchy row
            names[code] = _s(name)
            if len(code) == 4:
                group = code
            elif len(code) == 7:
                klass = code
            continue
        q = parse_quantity(qty)
        kind = gtin.classify_barcode(barcode)
        items.append(BasketItem(
            item_code=code, class_code=klass, class_name=names.get(klass, ""),
            group_code=group, group_name=names.get(group, ""),
            name_ar=_s(name), brand_ar=_s(brand),
            barcode_raw=_s(barcode), gtin=gtin.canonical(barcode) if kind == "gtin" else "", barcode_kind=kind,
            origin_raw=_s(origin), origin_iso=origin_iso(origin),
            qty_raw=_s(qty), qty_unit=q.unit, qty_total=q.total, qty_count=q.count, qty_flag=q.flag,
            match_mode="barcode" if kind == "gtin" else "spec",
            fresh_type=FRESH_GROUPS.get(group, "") if kind != "gtin" else "",
        ))
    return items


def write_csv(items, path):
    rows = [asdict(i) for i in items]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # BOM so Excel shows Arabic correctly
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def write_json(items, path):
    Path(path).write_text(json.dumps([asdict(i) for i in items], ensure_ascii=False, indent=1), encoding="utf-8")
