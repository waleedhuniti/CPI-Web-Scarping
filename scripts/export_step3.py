"""Dataiku-ready input for the team's pipeline: Step3_prices_clean (plain CSV, no photos, no styling).

    python scripts/export_step3.py                 # -> data/exports/dataiku/Step3_prices_clean.csv (+ .schema.txt)

One row per found price: month, obs_date, item_code, retailer, observed_price (per unit: kg / l / pc / bunch),
unit, pack_price, quality_flag ('ok' or 'outlier_check'), source_type, product_title, product_url.
Built from data/exports/cpi_prices_long.csv (scripts/export_for_dataiku.py) and data/basket/basket.json.
"""
import csv
import json
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/exports/dataiku"
COLS = ["month", "obs_date", "item_code", "retailer", "observed_price", "unit", "pack_price", "quality_flag",
        "source_type", "product_title", "product_url"]
UNIT = {"g": ("kg", 1000.0), "ml": ("l", 1000.0), "pc": ("pc", 1.0), "bunch": ("bunch", 1.0)}


def main():
    subprocess.run([sys.executable, str(ROOT / "scripts/export_for_dataiku.py")], check=True, stdout=subprocess.DEVNULL)
    basket = {b["item_code"]: b for b in json.load(open(ROOT / "data/basket/basket.json", encoding="utf-8"))}
    rows = []
    for r in csv.DictReader(open(ROOT / "data/exports/cpi_prices_long.csv", encoding="utf-8-sig")):
        if r["accepted"] != "yes" or not r["price"] or float(r["price"]) <= 0:
            continue
        b = basket.get(r["item_code"], {})
        unit, div = UNIT.get(b.get("qty_unit", ""), ("", 1.0))
        price = float(r["price"])
        flag = "ok"
        if r["price_basis"]:                                   # bulk category line: the store's per-unit price
            obs, u = float(r["unit_price"] or price), {"kg": "kg", "l": "l", "pc": "pc", "bunch": "bunch"}.get(r["price_basis"], r["price_basis"])
            if unit and u != unit:
                flag = "outlier_check"                         # different unit than the basket line
            unit = unit or u
            kind = "category"
        else:                                                  # barcode match: same pack as the basket line
            qty = float(b.get("qty_total") or 0)
            obs = round(price / (qty / div), 4) if unit and qty else price
            kind = "barcode"
        rows.append(dict(month=r["run_date"][:7], obs_date=r["run_date"], item_code=r["item_code"], retailer=r["retailer"],
                         observed_price=round(obs, 4), unit=unit, pack_price=price, quality_flag=flag, source_type=kind,
                         product_title=r["title"], product_url=r["url"]))
    med = {}
    for k in {(x["month"], x["item_code"]) for x in rows}:
        med[k] = statistics.median(x["observed_price"] for x in rows if (x["month"], x["item_code"]) == k)
    for x in rows:
        m = med[(x["month"], x["item_code"])]
        if m and not 0.4 <= x["observed_price"] / m <= 2.5:
            x["quality_flag"] = "outlier_check"
    rows.sort(key=lambda x: (x["obs_date"], x["item_code"], x["retailer"]))
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "Step3_prices_clean.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, quoting=csv.QUOTE_NONNUMERIC)
        w.writeheader()
        w.writerows(rows)
    (OUT / "Step3_prices_clean.schema.txt").write_text(
        "month text (YYYY-MM) | obs_date text (YYYY-MM-DD) | item_code text (9 digits, keep leading zero) | retailer text | "
        "observed_price double (per unit) | unit text | pack_price double | quality_flag text | source_type text | "
        "product_title text | product_url text\nUTF-8, comma, header row, quoted text.\n", encoding="utf-8")
    bad = sum(x["quality_flag"] != "ok" for x in rows)
    print(f"{len(rows)} rows, {len({x['item_code'] for x in rows})} items, {bad} flagged outlier_check -> {OUT / 'Step3_prices_clean.csv'}")


if __name__ == "__main__":
    main()
