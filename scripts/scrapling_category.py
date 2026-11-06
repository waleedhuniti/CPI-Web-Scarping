"""Bulk category crawl for basket lines WITHOUT a barcode (meat, fish, fruit, vegetables), then spec matching.

    python scripts/scrapling_category.py data/runs/<date>_category            # crawl + match
    python scripts/scrapling_category.py data/runs/<date>_category --match    # match again from the saved catalog

Barcoded basket lines are not touched here: they keep the barcode search (scripts/scrapling_search.py).

1. Crawl: Lulu reads every page of each category in config/categories.json (`page=1,2,..`) until a page brings no new
   product. Carrefour refuses its category pages (/c/F...: HTTP 403 since 30 Oct 2026) but serves its search pages, so for
   Carrefour the crawl searches the basket specs themselves (one query per spec: the first word of each must_have term)
   and keeps a product in a category only when Carrefour's own product data on the page puts it in that section
   (productCategory holds the category code, e.g. f1670000 = Meat & Poultry); a frozen or tinned product found by a
   'beef' search therefore never lands in the fresh-meat section. One request at a time, at least 2.5 s apart; a 429/503
   waits for Retry-After. A refused page (403, challenge, empty shell) stays unread: it is counted and logged as refused,
   never as "0 products", and crawl_status.json records pages read / refused per retailer.
   -> <run_dir>/catalog.csv: retailer, group, category, title, price, regular_price, size, price_per_kg / per unit,
      origin seen in the title, url.
2. Match each 'spec' basket line of those groups against its retailer's catalog with the English spec written for it
   (data/runs/2026-10-05/name_queries.json: must_have / must_not words) and the rules of docs/name_matching_rules.md:
   same product words, none of the excluded words, no organic / marinated / frozen unless the basket says so, a price
   that converts to the basket unit (per kg, or per piece / bunch), and the basket origin.
   -> <run_dir>/category_matches.csv, one row per basket line x retailer:
      match             one listing (or several within 15% per kg) of the basket origin - accepted
      review_multiple   several listings of the basket origin with prices that differ by more than 15%
      review_origin / substitute_origin  the product is there but without the basket origin (none stated, or another one):
                        kept for officer review; price proximity never approves an origin substitution
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
import urllib.parse
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
# processed meat (mortadella, luncheon, sausages, burgers, kebab) sits in the deli / chilled counter, not in the fresh-meat section
NOT_FRESH_LINE = re.compile(r"محمص|مكسرات|تمر|مجفف|زبيب|مجمد|معلب|مرتديلا|لانشون|نقانق|همبرجر|برجر|كباب|شيش|نجتس|مخلل|زيتون|جاف|مطحون|مسحوق")
NOT_FRESH = ["organic", "marinated", "ready to cook", "seasoned", "cooked", "smoked", "frozen", "juice", "dried",
             "canned", "puree", "pickled", "stuffed", "nuggets", "burger", "sausage", "kebab", "kofta"]


# ---------------------------------------------------------------- pinned reference products
# A basket line without a barcode is matched to one listing; without a memory the pick changes day to day (the median
# listing moves when the candidates move), which looks like inflation. The first accepted listing of a line at a
# retailer is pinned (data/state/category_pins.json; override with CPI_PINS=<json file>) and priced on the following days by its URL, so the same product is compared.
# If the pinned listing is gone from the catalogue the line is "not found" that day; after PIN_MAX_MISS days in a row a
# new listing is chosen and pinned (the officer should link the old and new price then).
PIN_MAX_MISS = 3


def pins_path():
    return Path(os.environ.get("CPI_PINS") or ROOT / "data/state/category_pins.json")


def load_pins():
    f = pins_path()
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def save_pins(pins):
    f = pins_path()
    f.parent.mkdir(parents=True, exist_ok=True)
    temp = f.with_suffix(f.suffix + ".tmp")
    temp.write_text(json.dumps(pins, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temp.replace(f)


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


MIN_DELAY = 2.5            # seconds between two requests to the same shop (a random 0-1 s is added)
CF_SEARCH = "https://www.carrefouruae.com/mafuae/en/search?keyword={q}&currentPage={page0}"
STOP_AFTER = 5            # refused pages in a row: the shop is blocking us, stop asking it for this run (circuit breaker)
CF_PAGES = 2               # search result pages read per query at most (60 products a page; the spec query puts the right products first)


def cf_code(cat):
    """Carrefour section code of a config category: 'code', else the id in its /c/<id> url (lower case, as on the page)."""
    m = re.search(r"/c/([A-Za-z0-9]+)", cat.get("url", ""))
    return str(cat.get("code") or (m.group(1) if m else "")).lower()


def carrefour_sections(html):
    """productId -> set of section codes, read from the product data embedded in a Carrefour search page."""
    h = html.replace('\\"', '"')
    marks = [(m.start(), m.group(1)) for m in re.finditer(r'"productId":"(\d+)"', h)]
    out = {}
    for n, (pos, pid) in enumerate(marks):
        end = marks[n + 1][0] if n + 1 < len(marks) else len(h)
        m = re.search(r'"productCategory":\[([^\]]*)\]', h[pos:end])
        if m:
            out.setdefault(pid, set()).update(c.strip().strip('"').lower() for c in m.group(1).split(",") if c.strip().strip('"'))
    return out


def search_query(spec):
    """A shop search query from an English spec: the first alternative of each must_have term, at most 4 words."""
    words = []
    for term in spec.get("must_have") or []:
        for w in str(term).lower().split():
            w = w.split("/")[0]                      # 'kingfish/kanad fresh' -> kingfish fresh
            if w and w not in words:
                words.append(w)
    if not words:
        words = [w for w in str(spec.get("query_alt") or spec.get("product_en") or "").lower().split()]
    return " ".join(words[:4])


def carrefour_queries(cats):
    """One query per basket spec line of the groups these Carrefour categories feed (deduplicated)."""
    from dataclasses import asdict
    from cpi.basket import load_basket_any
    groups = {g for c in cats for g in str(c["group"]).split(",")}
    specs = {x["c"]: x for x in json.load(open(SPECS, encoding="utf-8"))}
    qs = []
    for it in (asdict(i) for i in load_basket_any(ROOT)):
        if it["match_mode"] == "spec" and it["group_code"] in groups:
            q = search_query(specs.get(it["item_code"], {}))
            if q and q not in qs:
                qs.append(q)
    return qs


def get_page(s, url, delay, state):
    """One polite request: waits its turn, honours Retry-After on 429/503 (three tries), and says whether it was read.
    The first request of a Carrefour session can be refused while the session gets its cookies: it is asked once more."""
    wait = state.get("next", 0) - time.time()
    if wait > 0:
        time.sleep(wait)
    def fetch():
        page = s.get(url)
        for backoff in (30, 90, 180):
            if page.status not in (429, 503):
                break
            hd = getattr(page, "headers", None) or {}
            ra = str(hd.get("retry-after") or hd.get("Retry-After") or "").strip()
            time.sleep(min(float(ra), 600) if ra.isdigit() else backoff)
            page = s.get(url)
        html = page.body.decode("utf-8", "ignore") if isinstance(page.body, bytes) else str(page.body)
        ok = page.status == 200 and len(html) > 20_000 and ("carrefouruae" in html or "luluhypermarket" in html)
        return page, html, ok
    page, html, ok = fetch()
    if not ok and not state.get("warm") and "carrefouruae" in url:
        time.sleep(max(delay, MIN_DELAY) + random.random())
        page, html, ok = fetch()
    state["warm"] = True
    state["next"] = time.time() + max(delay, MIN_DELAY) + random.random()
    return page, html, ok


def catalog_row(retailer, cat, r):
    per, basis = price_basis(r)
    return dict(retailer=retailer, group=cat["group"], category=cat["name"], title=r["title"],
                price=r["price"], regular_price=r["regular_price"],
                size=r.get("size_text", ""), unit_price=per if per is not None else "",
                price_basis=basis, origin_seen=origin_of(r["title"]), url=r["url"],
                photo_url=r.get("photo", ""))


def crawl(run_dir, delay, only=None, max_queries=0):
    from scrapling.fetchers import FetcherSession
    cfg = json.load(open(CONFIG))
    if only:                                                   # crawl just these category names
        cfg = {r: [c for c in cfg[r] if c["name"] in only] for r in ("carrefour", "lulu")}
    out, log, status = [], [], {}
    with FetcherSession(impersonate="chrome", timeout=30, retries=3) as s:
        # Carrefour: search pages, products sorted into the config sections by the page's own section codes
        cats = [c for c in cfg["carrefour"] if cf_code(c)]
        st, state, found = {"read": 0, "refused": 0}, {}, {cf_code(c): {} for c in cats}
        queries = carrefour_queries(cats) if cats else []
        if max_queries:
            queries = queries[:max_queries]
        outside, pages_of, streak = set(), {c: set() for c in found}, 0
        for qn, q in enumerate(queries, 1):
            if streak >= STOP_AFTER:
                st["not_asked"] = len(queries) - qn + 1
                log.append(f"carrefour category: stopped after {streak} refused pages in a row (the shop is refusing us); "
                           f"{st['not_asked']} queries not asked - not read, not 'not found'")
                print(log[-1], flush=True)
                break
            seen_q = set()
            for n in range(CF_PAGES):
                url = CF_SEARCH.format(q=urllib.parse.quote(q), page0=n)
                try:
                    page, html, ok = get_page(s, url, delay, state)
                except Exception as e:
                    page, html, ok = None, "", False
                    print(f"carrefour | '{q}' page {n + 1}: FAILED {str(e)[:100]}", flush=True)
                if not ok:
                    st["refused"] += 1
                    streak += 1
                    log.append(f"carrefour | search '{q}' page {n + 1}: REFUSED (HTTP {getattr(page, 'status', '-')}, {len(html)} bytes) - not read")
                    print(log[-1], flush=True)
                    break
                streak = 0
                st["read"] += 1
                rows, secs = ss.parse_carrefour(page, q), carrefour_sections(html)
                new = [r for r in rows if r["url"] not in seen_q]
                for r in new:
                    seen_q.add(r["url"])
                    codes = secs.get(str(r.get("product_id")), set())
                    hit = [c for c in found if c in codes]
                    if not hit:
                        outside.add(r["url"])
                    for c in hit:
                        found[c].setdefault(r["url"], r)
                        pages_of[c].add((qn, n))
                print(f"carrefour | [{qn}/{len(queries)}] '{q}' page {n + 1}: {len(rows)} cards, {len(new)} new", flush=True)
                if len(rows) < 60 or not new:
                    break
        for c in cats:
            got = found[cf_code(c)]
            log.append(f"carrefour | {c['name']}: {len(got)} products from {len(pages_of[cf_code(c)])} pages (search, section {cf_code(c)})")
            out += [catalog_row("carrefour", c, r) for r in got.values()]
        log.append(f"carrefour category: {st['read']} pages read, {st['refused']} refused; {len(queries)} queries; "
                   f"{len(outside)} products outside the crawled sections dropped")
        status["carrefour"] = st
        # Lulu: its category pages
        st, state, streak = {"read": 0, "refused": 0}, {}, 0
        for cat in cfg["lulu"]:
            if streak >= STOP_AFTER:
                log.append(f"lulu category: stopped after {streak} refused pages in a row; {cat['name']} and the rest not read")
                print(log[-1], flush=True)
                break
            seen, pages = {}, 0
            for n in range(60):
                url = cat["url"].format(page0=n, page1=n + 1)
                try:
                    page, html, ok = get_page(s, url, delay, state)
                except Exception as e:
                    page, html, ok = None, "", False
                    print(f"lulu | {cat['name']} page {n + 1}: FAILED {str(e)[:100]}", flush=True)
                if not ok:
                    st["refused"] += 1
                    streak += 1
                    log.append(f"lulu | {cat['name']} page {n + 1}: REFUSED (HTTP {getattr(page, 'status', '-')}, {len(html)} bytes) - not read")
                    print(log[-1], flush=True)
                    break
                streak = 0
                st["read"] += 1
                pages += 1
                rows = ss.parse_lulu(page, cat["name"])
                new = [r for r in rows if r["url"] not in seen]
                for r in new:
                    seen[r["url"]] = r
                print(f"lulu | {cat['name']} | page {n + 1}: {len(rows)} cards, {len(new)} new", flush=True)
                if not new:
                    break
            log.append(f"lulu | {cat['name']}: {len(seen)} products from {pages} pages")
            out += [catalog_row("lulu", cat, r) for r in seen.values()]
        log.append(f"lulu category: {st['read']} pages read, {st['refused']} refused")
        status["lulu"] = st
    for k, v in status.items():
        tot = v["read"] + v["refused"]
        v["state"] = "not_read" if not tot else "ok" if v["refused"] <= 0.05 * tot else "blocked" if v["refused"] >= 0.9 * tot else "partial"
    fields = ["retailer", "group", "category", "title", "price", "regular_price", "size", "unit_price", "price_basis",
              "origin_seen", "url", "photo_url"]
    with open(run_dir / "catalog.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    (run_dir / "crawl_log.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    (run_dir / "crawl_status.json").write_text(json.dumps(status, indent=1) + "\n", encoding="utf-8")
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
    """w is a title word, or its plural/singular (tomato / tomatoes). Only a short ending counts: 'bone' is NOT 'boneless'."""
    return any(x == w or (len(w) >= 4 and len(x) >= 4 and abs(len(x) - len(w)) <= 2 and (x.startswith(w) or w.startswith(x)))
               for x in tw)


def phrase_ok(tw, phrase):
    """A must_have phrase ('kingfish/kanad', 'whole chicken') holds when one of its alternatives has all its words."""
    alts = [a for a in re.split(r"\s*/\s*", phrase) if a.strip()]
    for a in alts:
        core = [w for w in words(a) if w not in STOP]
        if not core or all(has_word(tw, w) for w in core):   # 'fresh/chilled': 'fresh' is never required
            return True
    return False


def basket_basis(item, spec):
    if (spec or {}).get("basis"):                     # the spec states the unit when the basket's unit text cannot (a bunch of spinach compared by the kilo)
        return spec["basis"]
    size = (spec or {}).get("size", "").lower()
    if "bunch" in size or "حزمة" in item["qty_raw"]:
        return "bunch"
    if item["qty_unit"] == "g" or "kg" in size:
        return "kg"
    if item["qty_unit"] == "ml":
        return "l"
    return "pc"


# words a title seldom carries but the English spec adds to describe the product ("whole watermelon", "loose olives", "large purple eggplant")
DESCRIPTORS = {"whole", "loose", "large", "small", "medium", "big", "head", "bulb", "bunch", "per", "kg", "dry", "raw", "round", "long",
               "white", "black", "green", "red", "yellow", "purple", "pink", "local", "plain", "natural", "premium", "extra", "imported",
               "packaged", "pack", "pre-packed"}


FUNC = {"the", "and", "or", "of", "with", "a", "in"}


def phrase_all(tw, phrase):
    """A must_not phrase ('fresh ginger', 'sea bass') excludes a title only when EVERY word of one alternative is in it (fresh is a real word here)."""
    for a in [x for x in re.split(r"\s*/\s*", phrase) if x.strip()]:
        core = [w for w in words(a) if w not in FUNC]
        if core and all(has_word(tw, w) for w in core):
            return True
    return False


NOT_CANNED_LINE = re.compile(r"جاف|سائب|مخلل مشكل|مخلل البصل")        # dry pulses, loose olives and pickles: not from tins and jars
CANNED_SECTION = re.compile(r"tins|jars|canned", re.I)


def make_filter(it, spec):
    """(unit basis, predicate): the predicate says whether a catalogue row is the product this basket line stands for
    (product words, none of the excluded words, section, price convertible to the line's unit). Origin is not looked at."""
    want = basket_basis(it, spec)
    frozen_ok = "مجمد" in it["name_ar"] or "frozen" in (spec.get("query_en", "") + spec.get("product_en", "")).lower()
    fresh_line = it["group_code"] in ("0112", "0113", "0116", "0117") and not NOT_FRESH_LINE.search(it["name_ar"]) and not frozen_ok
    musts = []
    for m in spec.get("must_have", []):
        if re.search(r"\d", m):
            continue
        drop = DESCRIPTORS - set(spec.get("keep", []))             # "keep": ["green"] when the colour is the product (green olives)
        core = " / ".join(" ".join(w for w in words(a) if w not in drop) for a in re.split(r"\s*/\s*", m))
        if re.sub(r"[ /]", "", core):                   # a phrase made only of descriptors ('whole', 'loose', 'large') is not required
            musts.append(core)
    nots = spec.get("must_not", [])
    not_canned = bool(NOT_CANNED_LINE.search(it["name_ar"]))

    def ok(row):
        t, tw = row["title"].lower(), words(row["title"])
        if "frozen" in str(row.get("category", "")).lower():     # the frozen section: the title need not say 'frozen'
            tw = tw + ["frozen"]
        if not musts and not words(spec.get("query_en", "")):
            return False
        if not musts and not all(has_word(tw, w) for w in words(spec.get("query_en", "")) if w not in STOP):
            return False
        if musts and not all(phrase_ok(tw, m) for m in musts):
            return False
        if any(phrase_all(tw, n) for n in nots):
            return False
        asked = (spec.get("query_en", "") + " " + spec.get("product_en", "")).lower()
        if any(x in t for x in NOT_FRESH if not (x == "frozen" and frozen_ok) and x not in asked):
            return False
        if not_canned and CANNED_SECTION.search(str(row.get("category", ""))):
            return False
        if "frozen" in str(row.get("category", "")).lower() and not frozen_ok:   # frozen section, title may not say so
            return False
        if fresh_line and not FRESH_SECTION.search(str(row.get("category", ""))):   # no pickles, tins, dried fruit
            return False
        return row["price_basis"] == want and bool(row["unit_price"])
    return want, ok


ORIGIN_PCT_LOW = 0.15  # last price under AED 10: +/-15%, or a move of at most AED 3 (tomato 5 -> 3 is fine)
ORIGIN_ABS_LOW = 3.0
ORIGIN_PCT_HIGH = 0.30  # last price AED 10 or more: +/-30% only (mortadella 10 -> 18 is a jump)
ORIGIN_BIG = 10.0


def origin_change_ok(last, new):
    if last <= 0:
        return False
    chg = abs(new - last)
    if last >= ORIGIN_BIG:
        return chg / last <= ORIGIN_PCT_HIGH
    return chg / last <= ORIGIN_PCT_LOW or chg <= ORIGIN_ABS_LOW


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
        want, ok = make_filter(it, spec)
        for retailer in ("carrefour", "lulu"):
            cands = [row for row in catalog
                     if row["retailer"] == retailer and it["group_code"] in str(row["group"]).split(",") and ok(row)]
            plan.append((it, spec, want, retailer, cands))
    enrich_origins(run_dir, list({id(c): c for *_, cands in plan for c in cands if not c["origin_seen"]}.values()), delay)
    pins = load_pins()
    names = {}
    for i in items:
        names[i["name_ar"]] = names.get(i["name_ar"], 0) + 1
    today = run_dir.name[:10]
    out = []
    for it, spec, want, retailer, cands in plan:
            same = [c for c in cands if it["origin_iso"] and it["origin_iso"] in c["origin_seen"].split(",")]
            unknown = [c for c in cands if not c["origin_seen"]]
            other = [c for c in cands if c["origin_seen"] and it["origin_iso"] not in c["origin_seen"].split(",")]
            pick, status, pin_state = None, "no_match", ""
            key = f"{it['item_code']}|{retailer}"
            pin = pins.get(key)
            cur = next((c for c in same if c["url"] == pin["url"]), None) if pin else None
            if cur is not None and (cur["price_basis"] != want or not cur["unit_price"]):
                cur = None
            if pin and cur is not None and pin.get("policy_version") == 2:                      # the same listing as before
                pick, status, pin_state = cur, "match", "pinned"
            elif pin and pin.get("policy_version") == 2 and pin.get("miss", 0) + (pin.get("last") != today) < PIN_MAX_MISS:   # gone today: not found, wait
                pin_state = "pinned_missing"
            elif same:
                per = sorted(float(c["unit_price"]) for c in same)
                med = statistics.median(per)
                pick = min(same, key=lambda c: abs(float(c["unit_price"]) - med))
                status = "match" if per[-1] <= per[0] * 1.15 else "review_multiple"
            elif unknown or other:                           # origin unclear / only another origin: office rule against the last accepted price
                pool, status = (unknown, "review_origin") if unknown else (other, "substitute_origin")
                last = float(pin["unit"]) if pin and pin.get("unit") else None
                per = sorted(float(c["unit_price"]) for c in pool)
                target = last if last else statistics.median(per)
                pick = min(pool, key=lambda c: abs(float(c["unit_price"]) - target))
                # Price proximity is not identity evidence. Keep origin candidates in review.
                pin_state = "origin_review"
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
            elif status == "match" and pick is not None:
                if pin_state == "pinned":
                    pin["miss"], pin["last"] = 0, today
                    pin["unit"] = float(pick["unit_price"])
                else:
                    pins[key] = {"policy_version": 2, "url": pick["url"], "title": pick["title"], "since": today, "last": today, "miss": 0,
                                 "unit": float(pick["unit_price"])}
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
    ap.add_argument("--max-queries", type=int, default=0, help="Carrefour: search only the first N spec queries (tests)")
    a = ap.parse_args()
    run_dir = Path(a.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    if not a.match:
        started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        crawl(run_dir, a.delay, set(a.only.split(";")) if a.only else None, a.max_queries)
        (run_dir / "started.txt").write_text(started + "\n")
    if not a.crawl_only:
        match(run_dir, delay=a.delay)


if __name__ == "__main__":
    main()

