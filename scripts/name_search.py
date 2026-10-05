"""Search by name + brand + size for basket items that the barcode did not settle.

Step 1 - build the search URLs (one per item and retailer, plus an alternative query when there is one):

    python scripts/name_search.py urls data/runs/2026-10-05/name_queries.json data/runs/2026-10-05

  Items searched at a retailer are those without a final accepted barcode match there (barcode not found, size
  doubts, page-check doubts) and every item without a barcode. Writes <retailer>_name_urls.json (crawler input)
  and name_url_map.json (url -> item code, query).

Step 2 - crawl the URLs with apify/website-content-crawler: crawlerType cheerio, maxCrawlDepth 0, ignoreCanonicalUrl
  true, htmlTransformer "none", readableTextCharThreshold 0, removeCookieWarnings false. WITHOUT htmlTransformer "none"
  the default 'readable text' clean-up throws away the product grid: most Lulu pages and ~20% of Carrefour pages came
  back as an empty page shell (2026-10-05).

Step 3 - turn the crawled pages into candidate lists:

    python scripts/name_search.py candidates <retailer> <dataset.json> data/runs/2026-10-05

  Writes <retailer>_name_candidates.json: per item, every listing seen on its search pages with the price, the
  size read from the title, whether that size equals the basket size, and a name/brand score. Nothing is accepted
  here; the decision is made in step 4 (judging) and every accepted row keeps the listing URL as evidence.

Step 4 - judge:  python scripts/name_search.py batches <run_dir> <batch_dir>   then the cpi-name-judge workflow
  (one judge per 30 records, a skeptical challenger for every accepted match), then
  python scripts/name_search.py apply <workflow_output> <batch_dir> <run_dir>   -> name_matches.csv

Step 5 - second source: python scripts/name_search.py pagecheck-input <run_dir>, crawl <retailer>_name_product_urls.json,
  python scripts/verify_pages.py <retailer> <pages.json> <run_dir>/<retailer>_name_matched.csv
"""
import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cpi.basket import load_basket  # noqa: E402
from cpi.matcher import ACCEPTED, Listing, name_score  # noqa: E402
from cpi.quantity import Quantity, all_quantities, pack_count, same_quantity  # noqa: E402
from cpi.retailers import carrefour, lulu  # noqa: E402

SEARCH = {
    "carrefour": "https://www.carrefouruae.com/mafuae/en/search?keyword={q}",
    "lulu": "https://gcc.luluhypermarket.com/en-ae/list/?search_text={q}",
}
QUERY_PARAM = {"carrefour": "keyword", "lulu": "search_text"}
_PRODUCT_LINK = {
    "carrefour": re.compile(r"\[([^\]\n]{3,})\]\((https://www\.carrefouruae\.com/[^)\s]*?/p/\d+)[^)\s]*\)"),
    "lulu": re.compile(r"\[([^\]\n]{3,})\]\((https://gcc\.luluhypermarket\.com/en-ae/(?:[^)\s]*?/)?p/[^)\s/?]+)/?(?:\?[^)\s]*)?\)"),
}


def final_accepted(run_dir: Path, retailer: str) -> set:
    """Item codes with an accepted barcode match that also survived the product-page check."""
    check = run_dir / f"{retailer}_matched_page_check.csv"
    matched = run_dir / f"{retailer}_matched.csv"
    if check.exists():
        return {r["item_code"] for r in csv.DictReader(open(check, encoding="utf-8-sig")) if r["final_status"] in ACCEPTED}
    return {r["item_code"] for r in csv.DictReader(open(matched, encoding="utf-8-sig")) if r["status"] in ACCEPTED}


def build_urls(queries_path, run_dir):
    run_dir = Path(run_dir)
    queries = {q["c"]: q for q in json.load(open(queries_path, encoding="utf-8"))}
    url_map = {}
    for retailer in SEARCH:
        done = final_accepted(run_dir, retailer)
        urls = []
        for code, q in queries.items():
            if code in done:
                continue
            # packaged goods: the precise brand + product query; loose fresh items also the query with the origin
            kinds = ("query_en", "query_alt") if q.get("sold_by_weight") else ("query_en",)
            for kind in kinds:
                text = (q.get(kind) or "").strip()
                if not text:
                    continue
                url = SEARCH[retailer].format(q=quote_plus(text))
                if url not in url_map:
                    urls.append({"url": url})
                url_map.setdefault(url, []).append({"item_code": code, "query": text, "kind": kind, "retailer": retailer})
        json.dump(urls, open(run_dir / f"{retailer}_name_urls.json", "w"), indent=0)
        print(f"{retailer}: {len({u['item_code'] for v in url_map.values() for u in v if u['retailer'] == retailer})} items, "
              f"{len(urls)} search pages")
    json.dump(url_map, open(run_dir / "name_url_map.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)


_NO_RESULTS = {
    "lulu": ("No results found",),
    "carrefour": ("No results found", "no results found", "We couldn't find", "We couldn’t find", "Sorry, no results"),
}


def _says_no_results(retailer, markdown) -> bool:
    return any(p in markdown for p in _NO_RESULTS[retailer])


def page_listings(retailer, markdown, query) -> list:
    """Every product card on a search page: the retailer parser's fields plus the raw card text (for the judge)."""
    if _says_no_results(retailer, markdown):
        return []
    parsed = (carrefour.parse_search_markdown(markdown, query) if retailer == "carrefour"
              else lulu.parse_search_markdown(markdown, query))
    by_url = {p.url.rstrip("/"): p for p in parsed}
    links = list(_PRODUCT_LINK[retailer].finditer(markdown))
    out, seen = [], set()
    for i, m in enumerate(links):
        url = m.group(2).rstrip("/")
        title = m.group(1).strip()
        if url in seen or title.startswith("!"):
            continue
        seen.add(url)
        end = links[i + 1].start() if i + 1 < len(links) else m.end() + 300
        card = markdown[m.end():min(end, m.end() + 300)].split("[")[0]       # stop at the next link / image
        card = re.sub(r"\s+", " ", card).strip()
        p = by_url.get(url)
        # size the price is for: Carrefour prints it on the card ('AED5.00 500g - Approx 6 pieces/KG',
        # 'AED181.97 2.60KG Min Order 2 kg'), Lulu in the title ('Orange Valencia 2.5 kg')
        sized = all_quantities(title) or all_quantities(re.sub(r"AED\s?[\d.,]+|per\s+\w+|pieces?/KG", " ", card))
        price = p.price if p else None
        per_kg = per_l = None
        if price and sized and sized[0].unit == "g" and sized[0].total > 0:
            per_kg = round(price / sized[0].total * 1000, 2)
        if price and sized and sized[0].unit == "ml" and sized[0].total > 0:
            per_l = round(price / sized[0].total * 1000, 2)
        out.append({
            "title": title, "url": url, "price": p.price if p else None,
            "regular_price": p.regular_price if p else None,
            "unit_price": (p.extra.get("unit_price") if p else None) or None,
            "unit_basis": (p.extra.get("unit_basis") if p else "") or "",
            "card": card[:200], "priced_size": f"{sized[0].total:g}{sized[0].unit}" if sized else "",
            "price_per_kg": per_kg, "price_per_l": per_l,
        })
    return out


def build_candidates(retailer, dataset_path, run_dir):
    run_dir = Path(run_dir)
    url_map = json.load(open(run_dir / "name_url_map.json", encoding="utf-8"))
    basket = {i.item_code: i for i in load_basket(ROOT / "data/basket/basket_source.xlsx")}
    data = json.load(open(dataset_path, encoding="utf-8"))
    pages = data["items"] if isinstance(data, dict) else data
    per_item, unread = {}, []
    for pg in pages:
        q = parse_qs(urlparse(pg["url"]).query).get(QUERY_PARAM[retailer], [""])[0]
        key = SEARCH[retailer].format(q=quote_plus(q))
        targets = url_map.get(key) or url_map.get(pg["url"]) or []
        md = pg.get("markdown") or ""
        listings = page_listings(retailer, md, q)
        if not listings and not _says_no_results(retailer, md):
            unread.append(pg["url"])           # neither products nor the site's 'no results' message: page did not render
        for t in targets:
            rec = per_item.setdefault(t["item_code"], {"queries": [], "listings": {}})
            rec["queries"].append({"query": q, "kind": t["kind"], "results": len(listings)})
            for lst in listings:
                rec["listings"].setdefault(lst["url"], lst)

    out = []
    for code, rec in per_item.items():
        it = basket[code]
        item_q = Quantity(it.qty_raw, it.qty_unit, it.qty_total, it.qty_count, it.qty_flag)
        n = pack_count(it.name_ar)
        cands = []
        for lst in rec["listings"].values():
            qs = all_quantities(lst["title"])
            size_equal = None
            if item_q.ok and qs:
                size_equal = any(same_quantity(item_q, x) or (n > 1 and x.unit == item_q.unit and
                                 abs(x.total - n * item_q.total) <= 0.005 * x.total) for x in qs)
            score = name_score(it.name_ar, it.brand_ar, Listing(retailer, lst["title"]))
            cands.append(dict(lst, size_in_title=[f"{x.total:g}{x.unit}" for x in qs], size_equal=size_equal,
                              name_score=round(score, 2)))
        cands.sort(key=lambda c: (c["size_equal"] is True, c["name_score"]), reverse=True)
        out.append({"item_code": code, "retailer": retailer, "name_ar": it.name_ar, "brand_ar": it.brand_ar,
                    "qty_raw": it.qty_raw, "basket_size": f"{item_q.total:g}{item_q.unit}" if item_q.ok else "",
                    "origin_raw": it.origin_raw, "fresh_type": it.fresh_type, "queries": rec["queries"],
                    "candidates": cands})
    dest = run_dir / f"{retailer}_name_candidates.json"
    json.dump(out, open(dest, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    with_size = sum(1 for o in out if any(c["size_equal"] for c in o["candidates"]))
    print(f"{retailer}: {len(pages)} pages, {len(out)} items, {sum(1 for o in out if o['candidates'])} with listings, "
          f"{with_size} with a listing of the basket size | pages that did not render: {len(unread)}")
    json.dump(unread, open(run_dir / f"{retailer}_name_unread.json", "w"), indent=0)
    print("written", dest)


_WORD = re.compile(r"[a-z0-9]+")


def _overlap(words, title) -> float:
    """Share of the query's key words found in a listing title (English, case-insensitive)."""
    want = {w for w in _WORD.findall(" ".join(words).lower()) if len(w) > 1}
    have = set(_WORD.findall(title.lower()))
    return len(want & have) / len(want) if want else 0.0


def _slim(c, fresh) -> dict:
    """What a judge needs to see of one listing (the full record stays in <retailer>_name_candidates.json)."""
    out = {"title": c["title"], "url": c["url"], "price": c["price"]}
    if c.get("regular_price") and c["price"] and c["regular_price"] > c["price"]:
        out["was"] = c["regular_price"]
    if fresh:
        out.update(priced_size=c["priced_size"], per_kg=c["price_per_kg"])
        if not c["priced_size"]:
            out["card"] = c["card"][:80]
    else:
        out["size_equal"] = c["size_equal"]
    return out


def build_batches(run_dir, out_dir, per_batch=30):
    """Judge input: per item and retailer the basket spec, the query spec and a trimmed candidate list.

    Packaged goods: only listings whose title states the basket size (or states no size) can be the item, so items
    without such a listing are settled here as 'no listing of the basket size' and never reach a judge.
    """
    run_dir, out_dir = Path(run_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    queries = {q["c"]: q for q in json.load(open(run_dir / "name_queries.json", encoding="utf-8"))}
    records, settled = [], []
    for retailer in SEARCH:
        path = run_dir / f"{retailer}_name_candidates.json"
        if not path.exists():
            continue
        for rec in json.load(open(path, encoding="utf-8")):
            q = queries[rec["item_code"]]
            key = [q["brand_en"], q["product_en"]] + q["must_have"]
            for c in rec["candidates"]:
                c["match_words"] = round(_overlap(key, c["title"]), 2)
            fresh = bool(q["sold_by_weight"] or rec["fresh_type"])
            if fresh:
                keep = sorted(rec["candidates"], key=lambda c: c["match_words"], reverse=True)[:15]
            else:
                same = [c for c in rec["candidates"] if c["size_equal"] is True]
                unknown = [c for c in rec["candidates"] if c["size_equal"] is None]
                keep = sorted(same, key=lambda c: c["match_words"], reverse=True)[:10] + \
                    sorted(unknown, key=lambda c: c["match_words"], reverse=True)[:3]
                if not keep or max(c["match_words"] for c in keep) == 0:
                    settled.append({"item_code": rec["item_code"], "retailer": retailer, "decision": "no_match",
                                    "reason": "no listing of the basket size with the brand/product words"
                                    if rec["candidates"] else "search returned no listings"})
                    continue
            records.append({
                "item_code": rec["item_code"], "retailer": retailer, "fresh": fresh,
                "basket": {"name_ar": rec["name_ar"], "brand_ar": rec["brand_ar"], "size": rec["qty_raw"],
                           "origin": rec["origin_raw"], "fresh_type": rec["fresh_type"]},
                "spec": {k: q[k] for k in ("brand_en", "product_en", "must_have", "must_not", "size", "sold_by_weight", "note")},
                "searched": [x["query"] for x in rec["queries"]],
                "candidates": [_slim(c, fresh) for c in keep],
            })
    records.sort(key=lambda r: (r["fresh"], r["item_code"], r["retailer"]))
    batches = [records[i:i + per_batch] for i in range(0, len(records), per_batch)]
    for i, b in enumerate(batches):
        # the judge sees candidate ids (c0, c1, ...) instead of long URLs; the _full file maps them back
        json.dump(b, open(out_dir / f"judge_{i:02d}_full.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        shown = [dict(r, candidates=[dict({"id": f"c{j}"}, **{k: v for k, v in c.items() if k != "url"})
                                     for j, c in enumerate(r["candidates"])]) for r in b]
        json.dump(shown, open(out_dir / f"judge_{i:02d}.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(settled, open(run_dir / "name_settled_without_judge.json", "w"), indent=0)
    print(f"{len(records)} item-retailer records to judge in {len(batches)} batches "
          f"({sum(r['fresh'] for r in records)} fresh) | settled without a judge: {len(settled)}")


def apply_judgements(workflow_output, batch_dir, run_dir):
    """Turn the judge + challenger verdicts into name_matches.csv.

    match + upheld by the challenger      -> name_match (goes into the index)
    match but refuted by the challenger    -> review (both reasons kept)
    review                                 -> review
    no_match, or no listing of the size    -> no_match
    For loose fresh items matched at both retailers, prices per kg more than 1.86x apart (i.e. outside +/-30% of
    their mean) are sent to review: one of the two is probably another grade or a different cut.
    """
    run_dir, batch_dir = Path(run_dir), Path(batch_dir)
    raw = open(workflow_output, encoding="utf-8").read()
    data = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    data = data.get("result", data)
    full, cands = {}, {}
    for f in sorted(batch_dir.glob("judge_??_full.json")):
        for r in json.load(open(f, encoding="utf-8")):
            full[(r["item_code"], r["retailer"])] = r
    for retailer in SEARCH:
        path = run_dir / f"{retailer}_name_candidates.json"
        if path.exists():
            for rec in json.load(open(path, encoding="utf-8")):
                for c in rec["candidates"]:
                    cands[(rec["item_code"], retailer, c["url"])] = c
    rows = {}
    for b in data["batches"]:
        verdicts = {(v["item_code"], v["retailer"]): v for v in (b.get("verdicts") or [])}
        for d in b["decisions"]:
            key = (d["item_code"], d["retailer"])
            rec = full.get(key)
            if not rec:
                continue
            chosen = {}
            if d["candidate_id"].startswith("c") and d["candidate_id"][1:].isdigit():
                j = int(d["candidate_id"][1:])
                if j < len(rec["candidates"]):
                    chosen = cands.get(key + (rec["candidates"][j]["url"],), {})
            v = verdicts.get(key)
            decision, checker = {"match": "name_match", "review": "review", "no_match": "no_match"}[d["decision"]], ""
            if d["decision"] == "match":
                if v is None:
                    decision, checker = "review", "not challenged"
                elif not v["upheld"]:
                    decision, checker = "review", "refuted: " + v["why"]
                else:
                    checker = "upheld: " + v["why"]
                if v and v.get("better_candidate_id"):
                    decision, checker = "review", checker + f" | better candidate {v['better_candidate_id']}"
            if decision != "no_match" and not chosen:
                decision, checker = "review", (checker + " | chosen id not found").strip(" |")
            rows[key] = dict(item_code=key[0], retailer=key[1], fresh=rec["fresh"], decision=decision,
                             title=chosen.get("title", ""), url=chosen.get("url", ""), price=chosen.get("price") or "",
                             regular_price=chosen.get("regular_price") or "", price_per_kg=chosen.get("price_per_kg") or "",
                             priced_size=chosen.get("priced_size", ""), origin_seen=d.get("origin_seen", ""),
                             reason=d["reason"], checker=checker)
    for key, rec in full.items():
        if key not in rows:
            rows[key] = dict(item_code=key[0], retailer=key[1], fresh=rec["fresh"], decision="review", title="", url="",
                             price="", regular_price="", price_per_kg="", priced_size="", origin_seen="",
                             reason="not judged (batch failed)", checker="")
    for st in json.load(open(run_dir / "name_settled_without_judge.json")):
        rows.setdefault((st["item_code"], st["retailer"]), dict(
            item_code=st["item_code"], retailer=st["retailer"], fresh=False, decision="no_match", title="", url="",
            price="", regular_price="", price_per_kg="", priced_size="", origin_seen="", reason=st["reason"], checker=""))
    # cross-retailer sanity band for loose fresh items
    by_item = {}
    for r in rows.values():
        if r["fresh"] and r["decision"] == "name_match" and r["price_per_kg"]:
            by_item.setdefault(r["item_code"], []).append(r)
    for code, rs in by_item.items():
        if len(rs) == 2:
            lo, hi = sorted(float(x["price_per_kg"]) for x in rs)
            if lo > 0 and hi / lo > 1.86:
                for x in rs:
                    x["decision"] = "review"
                    x["checker"] += f" | per-kg prices {lo:.2f} vs {hi:.2f} across retailers: outside +/-30% band"
    out = sorted(rows.values(), key=lambda r: (r["item_code"], r["retailer"]))
    dest = run_dir / "name_matches.csv"
    with open(dest, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    import collections
    c = collections.Counter((r["retailer"], r["fresh"], r["decision"]) for r in out)
    for k in sorted(c):
        print(f"  {k[0]:10s} {'fresh' if k[1] else 'packaged':9s} {k[2]:12s} {c[k]}")
    print("written", dest)


def pagecheck_input(run_dir):
    """<retailer>_name_matched.csv in the shape verify_pages.py reads, plus the product URLs to crawl."""
    run_dir = Path(run_dir)
    rows = list(csv.DictReader(open(run_dir / "name_matches.csv", encoding="utf-8-sig")))
    for retailer in SEARCH:
        sel = [r for r in rows if r["retailer"] == retailer and r["decision"] == "name_match" and r["url"]]
        with open(run_dir / f"{retailer}_name_matched.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["item_code", "status", "title", "url", "price", "regular_price", "in_stock",
                                              "reasons"])
            w.writeheader()
            for r in sel:
                w.writerow(dict(item_code=r["item_code"], status="fuzzy_match", title=r["title"], url=r["url"],
                                price=r["price"], regular_price=r["regular_price"], in_stock="", reasons=r["reason"]))
        json.dump([{"url": r["url"]} for r in sel], open(run_dir / f"{retailer}_name_product_urls.json", "w"), indent=0)
        print(f"{retailer}: {len(sel)} name matches to open on the product page")


if __name__ == "__main__":
    if sys.argv[1] == "urls":
        build_urls(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "candidates":
        build_candidates(sys.argv[2], sys.argv[3], sys.argv[4])
    elif sys.argv[1] == "batches":
        build_batches(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "apply":
        apply_judgements(sys.argv[2], sys.argv[3], sys.argv[4])
    elif sys.argv[1] == "pagecheck-input":
        pagecheck_input(sys.argv[2])
