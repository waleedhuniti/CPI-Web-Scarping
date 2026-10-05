"""One table of prices for the period: every basket item x retailer, with how it was matched and the evidence.

    python scripts/build_price_table.py data/runs/2026-10-05

Inputs in the run folder:
  <retailer>_matched.csv + <retailer>_matched_page_check.csv   barcode matches and their product-page check
  name_matches.csv                                              judged name/brand/size matches (scripts/name_search.py)
Output:
  prices.csv    one row per item and retailer: method, status, price, regular price, stock, price per kg, URL, evidence
  coverage.md   how many basket items have an accepted price, by COICOP group and method
Only rows with use_in_index = yes may go into the index; everything else is for the officer.
"""
import collections
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cpi.basket import load_basket  # noqa: E402
from cpi.matcher import ACCEPTED  # noqa: E402

RETAILERS = ("carrefour", "lulu")


def read_csv(path):
    return list(csv.DictReader(open(path, encoding="utf-8-sig"))) if Path(path).exists() else []


def main(run_dir):
    run_dir = Path(run_dir)
    basket = load_basket(ROOT / "data/basket/basket_source.xlsx")
    rows = {}
    for r in RETAILERS:
        matched = {x["item_code"]: x for x in read_csv(run_dir / f"{r}_matched.csv")}
        checked = {x["item_code"]: x for x in read_csv(run_dir / f"{r}_matched_page_check.csv")}
        for code, m in matched.items():
            c = checked.get(code, {})
            status = c.get("final_status") or m["status"]
            in_stock = c.get("final_in_stock", m.get("in_stock", ""))
            price = c.get("final_price") or m["price"]
            evidence = "barcode searched at retailer, exactly one product"
            if c.get("barcode_on_page") == "True":
                evidence = "basket barcode printed on the product page"
            if c:
                evidence += f"; product page price {c.get('page_price')} size '{c.get('page_pack_size')}'"
            rows[(code, r)] = dict(
                item_code=code, retailer=r, method="barcode", status=status, title=m["title"], url=m["url"],
                price=price, regular_price=m["regular_price"], in_stock=in_stock, price_per_kg="", origin=c.get("page_origin", ""),
                evidence=evidence if m["url"] else m["reasons"],
                use_in_index="yes" if status in ACCEPTED and price not in ("", "0", "0.0") and str(in_stock) == "True" else "no")
    for n in read_csv(run_dir / "name_matches.csv"):
        key = (n["item_code"], n["retailer"])
        if key in rows and rows[key]["use_in_index"] == "yes":
            continue                                  # a proven barcode match always wins over a name match
        rows[key] = dict(
            item_code=n["item_code"], retailer=n["retailer"], method="fresh_spec" if n.get("fresh") == "True" else "name",
            status=n["decision"], title=n["title"], url=n["url"], price=n["price"], regular_price=n["regular_price"],
            in_stock="", price_per_kg=n.get("price_per_kg", ""), origin=n.get("origin_seen", ""),
            evidence=n["reason"] + (f" | checker: {n['checker']}" if n.get("checker") else ""),
            use_in_index="yes" if n["decision"] == "name_match" and n["price"] not in ("", "0", "0.0") else "no")

    out = []
    for it in basket:
        for r in RETAILERS:
            row = rows.get((it.item_code, r)) or dict(item_code=it.item_code, retailer=r, method="", status="not_searched",
                                                     title="", url="", price="", regular_price="", in_stock="",
                                                     price_per_kg="", origin="", evidence="", use_in_index="no")
            out.append(dict(group=it.group_code, class_code=it.class_code, name_ar=it.name_ar, brand_ar=it.brand_ar,
                            basket_qty=it.qty_raw, basket_origin=it.origin_raw, **row))
    dest = run_dir / "prices.csv"
    with open(dest, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)

    by_item = collections.defaultdict(set)
    for o in out:
        if o["use_in_index"] == "yes":
            by_item[o["item_code"]].add(o["method"])
    groups = collections.defaultdict(lambda: collections.Counter())
    for it in basket:
        g = groups[it.group_code]
        g["items"] += 1
        m = by_item.get(it.item_code)
        if m:
            g["priced"] += 1
            g["by barcode" if "barcode" in m else ("by name" if "name" in m else "fresh spec")] += 1
    lines = ["# Price coverage - run " + run_dir.name, "",
             "Items with at least one accepted, in-stock price (Carrefour or Lulu).", "",
             "| Group | Items | Priced | by barcode | by name | fresh spec |", "|---|---:|---:|---:|---:|---:|"]
    tot = collections.Counter()
    for g in sorted(groups):
        c = groups[g]
        tot.update(c)
        lines.append(f"| {g} | {c['items']} | {c['priced']} | {c['by barcode']} | {c['by name']} | {c['fresh spec']} |")
    lines.append(f"| **All** | **{tot['items']}** | **{tot['priced']}** | {tot['by barcode']} | {tot['by name']} | {tot['fresh spec']} |")
    review = sum(1 for o in out if o["status"].startswith("review") or o["status"] in ("qty_unit_differs", "qty_title_url_conflict", "barcode_match_qty_unverified"))
    lines += ["", f"Rows waiting for the officer (review): {review}. Prices per retailer row: `prices.csv`."]
    (run_dir / "coverage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("written", dest)


if __name__ == "__main__":
    main(sys.argv[1])
