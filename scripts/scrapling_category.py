"""Bulk category crawl for basket lines WITHOUT a barcode (meat, fish, fruit, vegetables), then spec matching.

    python scripts/scrapling_category.py data/runs/<date>_category            # crawl + match
    python scripts/scrapling_category.py data/runs/<date>_category --match    # match again from the saved catalog

Barcoded basket lines are not touched here: they keep the barcode search (scripts/scrapling_search.py).

1. Crawl: every page of each category in config/categories.json (Carrefour `currentPage=0,1,..`, Lulu `page=1,2,..`)
   until a page brings no new product. One request at a time, --delay seconds apart.
   -> <run_dir>/catalog.csv: retailer, group, category, title, price, regular_price, size, price_per_kg / per unit,
      origin seen in the title, url.
2. Match each 'spec' basket line of those groups against its retailer's catalog with the English spec written for it
   (data/runs/2026-10-05/name_queries.json: must_have / must_not words) and the rules of docs/name_matching_rules.md:
   same product words, none of the excluded words, no organic / marinated / frozen unless the basket says so, a price
   that converts to the basket unit (per kg, or per piece / bunch), and the basket origin.
   -> <run_dir>/category_matches.csv, one row per basket line x retailer:
      match             one listing (or several within 15% per kg) of the basket origin - accepted
      review_multiple   several listings of the basket origin with prices that differ by more than 15%
      review_origin     the product is there but the title names no origin
      substitute_origin the product is there only from another origin (office rule: +/-30% of last month's price)
      no_match          nothing fits
"""
import argparse
import csv
import json
import os
import random
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from cpi.origin import origin_iso_en  # noqa: E402
from cpi.quantity import find_quantity  # noqa: E402
import scrapling_search as ss  # noqa: E402

CONFIG = ROOT / "config/categories.json"
SPECS = ROOT / "data/basket/specs_en.json"   # English spec per basket line (from data/runs/2026-10-05/name_queries.json)
DEMONYMS = {"indian": "IN", "pakistani": "PK", "australian": "AU", "brazilian": "BR", "kenyan": "KE", "ethiopian": "ET",
            "saudi": "SA", "omani": "OM", "egyptian": "EG", "jordanian": "JO", "lebanese": "LB", "turkish": "TR",
            "iranian": "IR", "chinese": "CN", "american": "US", "dutch": "NL", "spanish": "ES", "italian": "IT",
            "south african": "ZA", "new zealand": "NZ", "norwegian": "NO", "scottish": "GB", "local": "AE", "uae": "AE",
            "emirati": "AE", "yemeni": "YE", "sudanese": "SD", "somali": "SO", "moroccan": "MA", "filipino": "PH",
            "thai": "TH", "vietnamese": "VN", "sri lankan": "LK", "bangladeshi": "BD", "french": "FR", "chilean": "CL"}
STOP = {"fresh", "loose", "deli", "counter", "per", "kg", "imported", "the", "and", "or", "of", "with", "a", "in"}
# fresh meat, fish, fruit and vegetable lines are priced only from fresh sections (not tins, pickles, frozen, nuts)
FRESH_SECTION = re.compile(r"^(?!.*(dried|nuts|tins|canned|frozen|jars|pickle)).*(fresh|meat|poultry|fish|seafood|fruit|vegetable|herb|beef|chicken|lamb)", re.I)
NOT_FRESH_LINE = re.compile(r"محمص|مكسرات|تمر|مجفف|زبيب|مجمد|معلب")
NOT_FRESH = ["organic", "marinated", "ready to cook", "seasoned", "cooked", "smoked", "frozen", "juice", "dried",
             "canned", "puree", "pickled", "stuffed", "nuggets", "burger", "sausage", "kebab", "kofta"]


# ---------------------------------------------------------------- pinned reference products
# A basket line without a barcode is matched to one listing; without a memory the pick changes day to day (the median
# listing moves when the candidates move), which looks like inflation. The first accepted listing of a line at a
# retailer is pinned (CPI_PINS=<json file>) and priced on the following days by its URL, so the same product is compared.
# If the pinned listing is gone from the catalogue the line is "not found" that day; after PIN_MAX_MISS days in a row a
# new listing is chosen and pinned (the officer should link the old and new price then).
PIN_MAX_MISS = 3


def load_pins():
    f = os.environ.get("CPI_PINS")
    if f and Path(f).exists():
        return json.load(open(f, encoding="utf-8"))
    return {}


def save_pins(pins):
    f = os.environ.get("CPI_PINS")
    if f:
        json.dump(pins, open(f, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------- crawl

def origin_of(title):
    t = " " + re.sub(r"[^a-z ]", " ", title.lower()) + " "
    for k, iso in sorted(DEMONYMS.items(), key=lambda kv: -len(kv[0])):
        if f" {k} " in t:
            return iso
    return origin_iso_en(title)


def price_basis(row):
    """(per-unit price, basis): basis 'kg' / 'l' / 'pc' / 'bunch'; per kg from the card's unit price or the pack size."""
    title, price = row["title"], row["price"]
    if row.get("unit_basis", "").lower().startswith("kil") and row.get("unit_price"):
        return round(row["unit_price"], 2), "kg"
    t = title.lower()
    if re.search(r"\bbunch\b", t):
        return price, "bunch"
    if re.search(r"\bper\s*kg\b|\b1\s*kg\b", t) and not re.search(r"\d+\s*x", t):
        q = find_quantity(title)
        if not q.unit:
            return price, "kg"
    q = find_quantity((row.get("size_text") or "") + " " + title)
    if q.unit == "g" and q.total:
        return round(price / (q.total / 1000), 2), "kg"
    if q.unit == "ml" and q.total:
        return round(price / (q.total / 1000), 2), "l"
    if q.unit == "pc" and q.total:
        return round(price / q.total, 2), "pc"
    if re.search(r"\b(pc|pcs|piece|each|per piece)\b", t):
        return price, "pc"
    return None, ""


def crawl(run_dir, delay, only=None):
    from scrapling.fetchers import FetcherSession
    cfg = json.load(open(CONFIG))
    if only:                                                   # crawl just these category names
        cfg = {r: [c for c in cfg[r] if c["name"] in only] for r in ("carrefour", "lulu")}
    out, log = [], []
    with FetcherSession(impersonate="chrome", timeout=30, retries=3) as s:
        for retailer in ("carrefour", "lulu"):
            parse = ss.parse_carrefour if retailer == "carrefour" else ss.parse_lulu
            for cat in cfg[retailer]:
                seen, pages = {}, 0
                for n in range(60):
                    url = cat["url"].format(page0=n, page1=n + 1)
                    try:
                        page = s.get(url)
                        rows = parse(page, cat["name"]) if page.status == 200 else []
                    except Exception as e:
                        log.append(f"{retailer} {cat['name']} page {n}: FAILED {str(e)[:100]}")
                        print(log[-1]); rows = []
                    new = [r for r in rows if r["url"] not in seen]
                    for r in new:
                        seen[r["url"]] = r
                    pages += 1
                    print(f"{retailer} | {cat['name']} | page {n + 1}: {len(rows)} cards, {len(new)} new", flush=True)
                    time.sleep(delay + random.random())
                    if not new:
                        break
                log.append(f"{retailer} | {cat['name']}: {len(seen)} products from {pages} pages")
                for r in seen.values():
                    per, basis = price_basis(r)
                    out.append(dict(retailer=retailer, group=cat["group"], category=cat["name"], title=r["title"],
                                    price=r["price"], regular_price=r["regular_price"],
                                    size=r.get("size_text", ""), unit_price=per if per is not None else "",
                                    price_basis=basis, origin_seen=origin_of(r["title"]), url=r["url"],
                                    photo_url=r.get("photo", "")))
    with open(run_dir / "catalog.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    (run_dir / "crawl_log.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    print("\n".join(log))
    return out


# ---------------------------------------------------------------- origin from the product page (titles often omit it)

def page_origin(retailer, html):
    """ISO codes of the origin printed on a product page: Carrefour 'Origin | New Zealand, France', Lulu 'Country of origin: India'."""
    if retailer == "carrefour":
        m = re.search(r">\s*Origin\s*</[^>]+>\s*(?:<[^>]+>\s*)*([^<]{2,80})<", html)
    else:
        m = re.search(r"Country of origin:\s*([A-Za-z][A-Za-z ,.'&-]{1,60}?)\s*(?:\\|\"|<|$)", html)
    if not m:
        return ""
    isos = [origin_of(" " + part.strip() + " ") or origin_iso_en(part) for part in re.split(r",|/| and ", m.group(1))]
    return ",".join(dict.fromkeys(i for i in isos if i))


def enrich_origins(run_dir, rows, delay):
    """Fill origin_seen for these catalog rows from their product pages (cached in origins.json)."""
    cache_path = run_dir / "origins.json"
    cache = json.load(open(cache_path)) if cache_path.exists() else {}
    todo = [r for r in rows if r["url"] not in cache]
    if todo:
        from scrapling.fetchers import FetcherSession
        with FetcherSession(impersonate="chrome", timeout=30, retries=3) as s:
            for n, r in enumerate(todo, 1):
                try:
                    p = s.get(r["url"])
                    html = p.body.decode("utf-8", "ignore") if isinstance(p.body, bytes) else str(p.body)
                    cache[r["url"]] = page_origin(r["retailer"], html) if p.status == 200 else ""
                except Exception:
                    cache[r["url"]] = ""
                print(f"origin {n}/{len(todo)}: {r['title'][:50]} -> {cache[r['url']] or '?'}", flush=True)
                time.sleep(delay + random.random())
        json.dump(cache, open(cache_path, "w"), indent=0)
    for r in rows:
        r["origin_seen"] = r["origin_seen"] or cache.get(r["url"], "")


# ---------------------------------------------------------------- match

def words(text):
    return re.findall(r"[a-z]+", text.lower())


def has_word(tw, w):
    return any(x == w or (len(w) >= 4 and (x.startswith(w) or w.startswith(x) and len(x) >= 4)) for x in tw)


def phrase_ok(tw, phrase):
    """A must_have phrase ('kingfish/kanad', 'whole chicken') holds when one of its alternatives has all its words."""
    alts = [a for a in re.split(r"\s*/\s*", phrase) if a.strip()]
    for a in alts:
        core = [w for w in words(a) if w not in STOP]
        if not core or all(has_word(tw, w) for w in core):   # 'fresh/chilled': 'fresh' is never required
            return True
    return False


def basket_basis(item, spec):
    size = (spec or {}).get("size", "").lower()
    if "bunch" in size or "حزمة" in item["qty_raw"]:
        return "bunch"
    if item["qty_unit"] == "g" or "kg" in size:
        return "kg"
    if item["qty_unit"] == "ml":
        return "l"
    return "pc"


def match(run_dir, catalog=None, delay=1.5):
    if catalog is None:
        catalog = list(csv.DictReader(open(run_dir / "catalog.csv", encoding="utf-8-sig")))
    specs = {x["c"]: x for x in json.load(open(SPECS, encoding="utf-8"))}
    from dataclasses import asdict
    from cpi.basket import load_basket_any
    basket = [asdict(i) for i in load_basket_any(ROOT)]
    groups = {g for row in catalog for g in str(row["group"]).split(",")}
    items = [i for i in basket if i["match_mode"] == "spec" and i["group_code"] in groups]
    plan = []
    for it in items:
        spec = specs.get(it["item_code"], {})
        want = basket_basis(it, spec)
        fresh_line = it["group_code"] in ("0112", "0113", "0116", "0117") and not NOT_FRESH_LINE.search(it["name_ar"])
        frozen_ok = "مجمد" in it["name_ar"] or "frozen" in (spec.get("query_en", "") + spec.get("product_en", "")).lower()
        musts = [m for m in spec.get("must_have", []) if not re.search(r"\d", m)]
        nots = spec.get("must_not", [])
        for retailer in ("carrefour", "lulu"):
            cands = []
            for row in catalog:
                if row["retailer"] != retailer or it["group_code"] not in str(row["group"]).split(","):
                    continue
                t, tw = row["title"].lower(), words(row["title"])
                if not musts and not all(has_word(tw, w) for w in words(spec.get("query_en", "")) if w not in STOP):
                    continue
                if musts and not all(phrase_ok(tw, m) for m in musts):
                    continue
                if any(phrase_ok(tw, n) and any(w not in STOP for w in words(n)) for n in nots):
                    continue
                if any(x in t for x in NOT_FRESH if not (x == "frozen" and frozen_ok)):
                    continue
                if "frozen" in str(row.get("category", "")).lower() and not frozen_ok:   # frozen section, title may not say so
                    continue
                if fresh_line and not FRESH_SECTION.search(str(row.get("category", ""))):   # no pickles, tins, dried fruit
                    continue
                if row["price_basis"] != want or not row["unit_price"]:
                    continue
                cands.append(row)
            plan.append((it, spec, want, retailer, cands))
    enrich_origins(run_dir, list({id(c): c for *_, cands in plan for c in cands if not c["origin_seen"]}.values()), delay)
    pins = load_pins()
    today = run_dir.name[:10]
    by_url = {(r["retailer"], r["url"]): r for r in catalog}
    out = []
    for it, spec, want, retailer, cands in plan:
            same = [c for c in cands if it["origin_iso"] in c["origin_seen"].split(",")]
            unknown = [c for c in cands if not c["origin_seen"]]
            other = [c for c in cands if c["origin_seen"] and it["origin_iso"] not in c["origin_seen"].split(",")]
            pick, status, pin_state = None, "no_match", ""
            key = f"{it['item_code']}|{retailer}"
            pin = pins.get(key)
            cur = by_url.get((retailer, pin["url"])) if pin else None
            if cur is not None and (cur["price_basis"] != want or not cur["unit_price"]):
                cur = None
            if pin and cur is not None:                      # the same listing as before
                pick, status, pin_state = cur, "match", "pinned"
            elif pin and pin.get("miss", 0) + (pin.get("last") != today) < PIN_MAX_MISS:   # gone today: not found, wait
                pin_state = "pinned_missing"
            elif same:
                per = sorted(float(c["unit_price"]) for c in same)
                med = statistics.median(per)
                pick = min(same, key=lambda c: abs(float(c["unit_price"]) - med))
                status = "match" if per[-1] <= per[0] * 1.15 else "review_multiple"
            elif unknown:
                pick, status = min(unknown, key=lambda c: float(c["unit_price"])), "review_origin"
            elif other:
                pick, status = min(other, key=lambda c: float(c["unit_price"])), "substitute_origin"
            if pin_state == "" and pin:
                pin_state = "repinned"
            alts = sorted(cands, key=lambda c: float(c["unit_price"]))
            out.append(dict(item_code=it["item_code"], group=it["group_code"], name_ar=it["name_ar"],
                            basket_qty=it["qty_raw"], basket_origin=it["origin_iso"], spec_en=spec.get("product_en", ""),
                            retailer=retailer, status=status, accepted="yes" if status == "match" else "no",
                            title=pick["title"] if pick else "", price=pick["price"] if pick else "",
                            regular_price=pick["regular_price"] if pick else "",
                            unit_price=pick["unit_price"] if pick else "", price_basis=want,
                            origin_seen=pick["origin_seen"] if pick else "", n_candidates=len(cands),
                            other_candidates=" | ".join(f"{c['title']} [{c['origin_seen'] or '?'}] ({c['unit_price']}/{c['price_basis']})" for c in alts if c is not pick)[:400],
                            url=pick["url"] if pick else "", pin_state=pin_state))
            if pin_state == "pinned_missing":
                if pin.get("last") != today:
                    pin["miss"], pin["last"] = pin.get("miss", 0) + 1, today
            elif status in ("match", "review_multiple") and pick is not None:
                if pin_state == "pinned":
                    pin["miss"], pin["last"] = 0, today
                else:
                    pins[key] = {"url": pick["url"], "title": pick["title"], "since": today, "last": today, "miss": 0}
    save_pins(pins)
    with open(run_dir / "category_matches.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    for retailer in ("carrefour", "lulu"):
        mine = [r for r in out if r["retailer"] == retailer]
        counts = {}
        for r in mine:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        print(f"{retailer}: {len(mine)} non-barcode basket lines | accepted {counts.get('match', 0)} | {counts}")
        for g in sorted({r['group'] for r in mine}):
            gm = [r for r in mine if r["group"] == g]
            print(f"   {g}: {sum(r['status'] == 'match' for r in gm)}/{len(gm)} accepted, "
                  f"{sum(r['status'] != 'no_match' for r in gm)} with a candidate")
    print("written", run_dir / "category_matches.csv")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("--match", action="store_true", help="only re-run matching on the saved catalog.csv")
    ap.add_argument("--delay", type=float, default=1.5)
    ap.add_argument("--crawl-only", action="store_true", help="crawl without matching (merge later with combine_run.py)")
    ap.add_argument("--only", help="category names to crawl, separated by ';' (default: all)")
    a = ap.parse_args()
    run_dir = Path(a.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    if not a.match:
        started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        crawl(run_dir, a.delay, set(a.only.split(";")) if a.only else None)
        (run_dir / "started.txt").write_text(started + "\n")
    if not a.crawl_only:
        match(run_dir, delay=a.delay)


if __name__ == "__main__":
    main()
