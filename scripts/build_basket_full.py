"""The complete CPI basket (all divisions) from the office's item list.

    python scripts/build_basket_full.py data/basket/CPI_Item_Basket_2026-01.xlsx

Input: workbook with columns code, official_name, unit, month (one row per item, 9-digit COICOP code).
Writes data/basket/basket.json: every item with its group / division names (config/cpi_groups.json), cpi_group, kind
(goods | service | market) and match_mode:
  barcode  an item we already hold a GTIN for (unchanged)
  spec     an existing food line without barcode (category crawl + pinned product)
  name     a new goods item (matched on the product name / model in the daily catalogue)
  service  a service (restaurant, laundry, repair, hotel, haircut): no online shelf price
  market   priced from a market rate (gold per gram)
Existing items keep their barcode, brand and origin; name and unit are taken from the new list.
"""
import json
import sys
from dataclasses import asdict
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cpi.basket import item_from_fields  # noqa: E402


def main(xlsx):
    cfg = json.load(open(ROOT / "config/cpi_groups.json", encoding="utf-8"))
    old = {b["item_code"]: b for b in json.load(open(ROOT / "data/basket/basket_food_637.json", encoding="utf-8"))}
    ws = openpyxl.load_workbook(xlsx, read_only=True, data_only=True).worksheets[0]
    out, changed = [], 0
    for code, name, unit, month in (r[:4] for r in ws.iter_rows(min_row=2, values_only=True)):
        if code is None:
            continue
        code = str(code).strip()
        g = code[:4]
        gi = cfg["groups"][g]
        fields = dict(old.get(code, {}))
        if code in old and (fields["name_ar"] != str(name).strip() or fields["qty_raw"] != str(unit).strip()):
            changed += 1
        fields.update(item_code=code, name_ar=str(name).strip(), qty_raw=str(unit).strip() if unit is not None else "")
        fields.setdefault("brand_ar", "")
        fields.setdefault("barcode_raw", "")
        fields.setdefault("origin_raw", "")
        fields["group_code"], fields["group_name"] = g, f"{g} - {gi['ar']}"
        fields["class_code"] = code[:7]
        fields.setdefault("class_name", f"{code[:7]} - {fields['name_ar']}" if code not in old else "")
        it = asdict(item_from_fields(fields))
        mode = it["match_mode"]
        if code not in old:
            mode = "service" if gi["kind"] == "service" else "name"
            if g == "1321" and fields["name_ar"].startswith("ذهب"):
                mode = "market"
        it.update(division_code=code[:2], division_name=cfg["divisions"][code[:2]]["ar"], cpi_group=gi["ar"],
                  kind={"service": "service", "market": "market"}.get(mode, "goods"), match_mode=mode, basket_month=str(month or ""))
        out.append(it)
    (ROOT / "data/basket/basket.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    import collections
    c = collections.Counter(i["match_mode"] for i in out)
    print(len(out), "items;", dict(c), f"; {changed} existing items with a changed name/unit")


if __name__ == "__main__":
    main(sys.argv[1])
