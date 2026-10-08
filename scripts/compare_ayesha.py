"""Compare scraped Carrefour / Lulu prices with the field researcher's (Ayesha) daily sheet, item by item.

    python scripts/compare_ayesha.py data/runs/2026-10-08_ayesha

Barcode items: the retailer's search for the barcode must return exactly one product, whose size must equal the basket
size. Fresh items: the chosen listing per item is in fresh_choices.json (product, kind and origin checked by hand).
"""
import csv, gzip, json, sys
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from cpi.quantity import parse_quantity, same_quantity, all_quantities  # noqa: E402
from name_search import page_listings, SEARCH  # noqa: E402


def num(v):
    try:
        return float(str(v).replace("عرض", "").strip())
    except (TypeError, ValueError):
        return None


def main(run):
    run = Path(run)
    items = json.load(open(run / "ayesha_items.json", encoding="utf-8"))
    pages = {}
    for r in SEARCH:
        for pg in json.load(gzip.open(run / f"{r}_search_pages.json.gz", "rt", encoding="utf-8")):
            pages[pg["url"]] = pg["markdown"]
    fresh = json.load(open(run / "fresh_choices.json", encoding="utf-8")) if (run / "fresh_choices.json").exists() else {}
    out = []
    for i in items:
        bq = parse_quantity(i["qty"])
        for r in SEARCH:
            ayesha = i[f"ayesha_{r}"]
            row = dict(item_code=i["item_code"], name_ar=i["name_ar"], brand_ar=i["brand_ar"], barcode=i["barcode"],
                       qty=i["qty"], retailer=r, ayesha_price=num(ayesha), ayesha_note="" if num(ayesha) is not None else (ayesha or ""),
                       scraped_price="", scraped_title="", url="", status="", note="")
            if not i["queries"]:
                row["status"] = "not_in_supermarkets"
            elif i["barcode_kind"] == "gtin":
                ls = page_listings(r, pages.get(SEARCH[r].format(q=quote_plus(i["queries"][0])), ""), i["queries"][0])
                if not ls:
                    row["status"] = "not_found"
                elif len(ls) > 1:
                    row["status"], row["note"] = "several_results", "; ".join(f"{l['title']} {l['price']}" for l in ls[:3])
                else:
                    l = ls[0]
                    row.update(scraped_price=l["price"], scraped_title=l["title"], url=l["url"])
                    qs = all_quantities(l["title"])
                    ok = (not bq.ok) or not qs or any(same_quantity(bq, q) for q in qs)
                    row["status"] = "barcode_match" if ok else "size_differs"
                    if not ok:
                        row["note"] = f"basket {i['qty']} vs listing {qs[0].total:g}{qs[0].unit}"
            else:
                c = fresh.get(f"{i['item_code']}|{r}")
                if c and c.get("url"):
                    row.update(scraped_price=c["price"], scraped_title=c["title"], url=c["url"], status="fresh_match",
                               note=c.get("note", ""))
                else:
                    row.update(status="not_found", note=(c or {}).get("note", ""))
            a, s = row["ayesha_price"], num(row["scraped_price"])
            row["diff_pct"] = round((s - a) / a * 100, 1) if (a and s) else ""
            row["agree"] = ("yes" if abs(s - a) < 0.01 else "no") if (a and s) else ""
            out.append(row)
    with open(run / "comparison.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    both = [o for o in out if o["agree"]]
    print(f"rows {len(out)} | both have a price: {len(both)} | same price: {sum(o['agree']=='yes' for o in both)} "
          f"| within 5%: {sum(abs(o['diff_pct'])<=5 for o in both)}")
    for r in SEARCH:
        rr = [o for o in out if o["retailer"] == r]
        print(r, "ayesha priced", sum(o['ayesha_price'] is not None for o in rr), "| scraped", sum(bool(o['scraped_price']) for o in rr),
              "| both", sum(bool(o['agree']) for o in rr), "| equal", sum(o['agree'] == 'yes' for o in rr),
              "| only ayesha", sum(o['ayesha_price'] is not None and not o['scraped_price'] for o in rr),
              "| only scraped", sum(o['ayesha_price'] is None and bool(o['scraped_price']) for o in rr))
    return out


if __name__ == "__main__":
    main(sys.argv[1])
