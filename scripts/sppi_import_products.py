"""Import the SPPI H & J sample (companies + products/services) from the officer's workbook.

    python scripts/sppi_import_products.py <sample workbook>.xlsx

Writes data/sppi/sample/companies.csv, products.csv and activities.csv (all git-ignored). Only identifying,
classification and production columns are copied (no contact names, phones or e-mails).
  companies:  ser, section (H/J), name_ar, name_en, isic (registered activity), isic_name, red, website,
              production_adjusted, weight (% of the full frame), scraping_rating, scraping_reason
  activities: the frame's summary rows - code (SPPI, H/J, 2-, 3- and 4-digit ISIC), level, names,
              production_adjusted, weight
  products:  product_id (ser-NN), ser, section, company, isic_registered, red, type (منتج/خدمة), product,
             isic_product, isic_product_name, source_url, certainty
"""
import csv
import sys
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/sppi/sample"


def main(path):
    wb = load_workbook(path, data_only=True)
    companies, activities = {}, []
    for r in wb["اطار المصادر - H و J (الأحمر)"].iter_rows(min_row=2, values_only=True):
        if not r[0]:
            # frame summary rows: SPPI total, section (H/J), division (2 digits), group (3), class (4)
            code = str(r[5] if r[5] is not None else (r[4] or "")).strip()
            if code:
                level = {"SPPI": "total"}.get(code, "section" if code.isalpha() else f"{len(code)}-digit")
                activities.append(dict(code=code, level=level, name_en=r[6] or "", name_ar=r[7] or "",
                                       production_adjusted=r[12] or 0, weight=r[19] or 0))
            continue
        companies[r[0]] = dict(ser=r[0], section=r[4] or "", name_ar=r[2] or "", name_en=r[3] or "",
                               isic=r[5] or "", isic_name=r[6] or "", red=r[20] or "", website=r[17] or "",
                               production_adjusted=r[12] or 0, weight=r[19] or 0,
                               scraping_rating="", scraping_reason="")
    for r in wb["تقييم Scraping"].iter_rows(min_row=2, values_only=True):
        if r[0] in companies:
            companies[r[0]].update(scraping_rating=r[8] or "", scraping_reason=r[9] or "",
                                   website=companies[r[0]]["website"] or r[5] or "")
    products, counter = [], {}
    for r in wb["المنتجات والخدمات"].iter_rows(min_row=2, values_only=True):
        if not r[0]:
            continue
        counter[r[0]] = counter.get(r[0], 0) + 1
        c = companies.get(r[0], {})
        products.append(dict(product_id=f"{r[0]}-{counter[r[0]]:02d}", ser=r[0], section=c.get("section", ""),
                             company=r[1] or "", isic_registered=r[2] or "", red=r[3] or "", type=r[4] or "",
                             product=r[5] or "", isic_product=r[6] or "", isic_product_name=r[7] or "",
                             source_url=r[11] or "", certainty=r[12] or ""))
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in (("companies", list(companies.values())), ("products", products), ("activities", activities)):
        with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(f"{len(companies)} companies, {len(products)} products, {len(activities)} activity rows -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
