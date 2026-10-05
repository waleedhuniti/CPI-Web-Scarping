"""Second-source check: open every matched product page and compare it with the search result.

    python scripts/verify_pages.py carrefour <pages.json> data/runs/2026-10-05/carrefour_matched.csv
    python scripts/verify_pages.py lulu      <pages.json> data/runs/2026-10-05/lulu_matched.csv

<pages.json> is a list of {url, markdown|html, jsonLd} from apify/website-content-crawler (cheerio) over the product URLs.
  * Carrefour: price + stock from the JSON-LD offer, pack size and origin from the page text (markdown).
  * Lulu:      price + stock from the JSON-LD offer, the product's REAL barcodes + pack size + origin from the record
               embedded in the HTML (crawl with saveHtml, htmlTransformer none, and do not remove <script>).
Writes <matched>_page_check.csv with a final_status / final_price / final_in_stock per row and prints agreement rates.
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cpi import gtin  # noqa: E402
from cpi.basket import load_basket  # noqa: E402
from cpi.matcher import ACCEPTED, BARCODE_UNIT_LABEL  # noqa: E402
from cpi.quantity import Quantity, all_quantities, pack_count, same_quantity  # noqa: E402
from cpi.retailers import carrefour, lulu  # noqa: E402


def pid(url) -> str:
    m = re.search(r"/p/([^/?]+)", url or "")
    return m.group(1) if m else ""


def read_page(retailer, page) -> dict:
    if retailer == "carrefour":
        return dict(carrefour.parse_product_page(page.get("markdown") or "", page.get("jsonLd")), eans=None)
    return lulu.parse_product_page(page.get("html") or "", page.get("jsonLd"))


def main(retailer, pages_path, matched_path):
    pages = {pid(p["url"]): p for p in json.load(open(pages_path, encoding="utf-8"))}
    basket = {i.item_code: i for i in load_basket(ROOT / "data/basket/basket_source.xlsx")}
    rows = list(csv.DictReader(open(matched_path, encoding="utf-8-sig")))
    out = []
    for r in rows:
        if not r["url"]:
            continue
        rec = dict(item_code=r["item_code"], status=r["status"], title=r["title"], url=r["url"],
                   search_price=r["price"], search_in_stock=r["in_stock"])
        page = pages.get(pid(r["url"]))
        if not page:
            out.append(dict(rec, check="page_not_read", final_status=r["status"]))
            continue
        p = read_page(retailer, page)
        it = basket[r["item_code"]]
        item_q = Quantity(it.qty_raw, it.qty_unit, it.qty_total, it.qty_count, it.qty_flag)
        pack_qs = all_quantities(p["pack_size"])
        n = pack_count(it.name_ar)

        def same_pack(q):
            return (same_quantity(item_q, q)
                    or (r["status"] == BARCODE_UNIT_LABEL and abs(q.total - item_q.total) < 0.01)
                    or (n > 1 and q.unit == item_q.unit and abs(q.total - n * item_q.total) < 0.01 * q.total))

        sp = float(r["price"] or 0)
        price_ok = abs(sp - p["price"]) < 0.005
        stock_ok = str(p["in_stock"]) == str(r["in_stock"]) if r["in_stock"] not in ("", "None") else None
        # the page may state the size another way than the basket ('200 g' for a '4 pcs 200 g' roll pack): that is fine
        # when the listing title states both the basket size and the page size
        title_qs = all_quantities(r["title"])
        title_bridge = any(same_pack(t) for t in title_qs) and \
            any(same_quantity(q, t) for q in pack_qs for t in title_qs)
        pack_ok = (any(same_pack(q) for q in pack_qs) or title_bridge) if (item_q.ok and pack_qs) else None
        ean_ok = (any(gtin.same_gtin(it.gtin, e) for e in p["eans"]) if p["eans"] else False) \
            if (p.get("eans") is not None and it.gtin) else None

        problems = []
        if not price_ok:
            problems.append(f"price search {sp:.2f} vs page {p['price']:.2f}")
        if stock_ok is False:
            problems.append(f"stock search {r['in_stock']} vs page {p['in_stock']}")
        if pack_ok is False and r["status"] in ACCEPTED:
            problems.append(f"page pack size '{p['pack_size']}' vs basket '{it.qty_raw}'")
        if ean_ok is False:
            problems.append(f"basket barcode {it.gtin} not among the page's barcodes {p['eans']}")

        # what goes forward: the product page is the later, more detailed source. An accepted row is sent back to the
        # officer when the page shows another pack size or (Lulu) does not carry the basket barcode at all.
        final = r["status"]
        if r["status"] in ACCEPTED and ean_ok is False:
            final = "review_page_barcode"
        elif r["status"] in ACCEPTED and pack_ok is False:
            final = "review_page_pack_size"
        elif ean_ok and r["status"] not in ACCEPTED and pack_ok:
            final = "barcode_match"          # page proves the barcode and the size: a search-side doubt is resolved
        out.append(dict(rec, page_price=p["price"], page_in_stock=p["in_stock"], page_pack_size=p["pack_size"],
                        page_origin=p["origin"], page_eans=" ".join(p["eans"] or []) if p.get("eans") is not None else "",
                        basket_qty=it.qty_raw, basket_gtin=it.gtin, price_agree=price_ok, stock_agree=stock_ok,
                        pack_agrees_with_basket=pack_ok, barcode_on_page=ean_ok,
                        check="ok" if not problems else "; ".join(problems),
                        final_status=final, final_price=p["price"] if p["price"] > 0 else "", final_in_stock=p["in_stock"]))

    dest = Path(matched_path).with_name(Path(matched_path).stem + "_page_check.csv")
    fields = list(dict.fromkeys(k for o in out for k in o))
    with open(dest, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)

    read = [o for o in out if o["check"] != "page_not_read"]
    acc = [o for o in read if o["status"] in ACCEPTED]
    n = len(read)
    print(f"{retailer}: product pages read {n} of {len(out)}")
    print(f"  price equal (search vs page)    {sum(o['price_agree'] for o in read)}/{n}")
    s = [o for o in read if o["stock_agree"] is not None]
    if s:
        print(f"  stock equal                     {sum(o['stock_agree'] for o in s)}/{len(s)}")
    pk = [o for o in acc if o["pack_agrees_with_basket"] is not None]
    print(f"  accepted rows whose page pack size equals the basket size {sum(o['pack_agrees_with_basket'] for o in pk)}/{len(pk)}"
          f" ({len(acc) - len(pk)} pages show no readable pack size)")
    b = [o for o in read if o["barcode_on_page"] is not None]
    if b:
        print(f"  basket barcode printed on the product page {sum(o['barcode_on_page'] for o in b)}/{len(b)}")
    print(f"  pages with an origin            {sum(1 for o in read if o['page_origin'])}")
    usable = [o for o in read if o["final_status"] in ACCEPTED and o["final_price"] != "" and o["final_in_stock"]]
    print(f"  FINAL: accepted, priced and in stock on the product page: {len(usable)}"
          f" | back to review: {sum(o['final_status'].startswith('review_page') for o in read)}"
          f" | rescued by the page: {sum(o['final_status'] != o['status'] and not o['final_status'].startswith('review') for o in read)}")
    for o in read:
        if o["check"] != "ok" and not o["check"].startswith("stock search False vs page True"):
            print("  !", o["item_code"], o["status"], "->", o["final_status"], "|", o["title"][:50], "|", o["check"])
    print("written", dest)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
