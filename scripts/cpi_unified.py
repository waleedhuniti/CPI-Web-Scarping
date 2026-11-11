"""One CPI price dataset from the two collections (basket runs + catalogue crawl), no duplicates.

Usage:
  python3 -I scripts/cpi_unified.py <runs dir> <catalogue history.json> <catalogue rows.json> <out.xlsx> [out.csv]

<runs dir> holds the panel's projects/cpi/runs export: <run id>.json (run doc with log) and <run id>/rows/cNNN.json.

One row = one (date, shop, product). The product key is the chain plus the shop's own product id (retailer_id,
else the id in the URL, else the URL), so a product found by barcode, by name, by the category crawl and by the
catalogue crawl on the same day is one row.

Rules (CLAUDE.md):
- Basket runs: the latest automatic run of each day. Rows with a price and accepted only. Category rows of a shop
  whose barcode pages were refused that day (>= 90% failed) are carried rows, not prices: dropped and counted.
  Rows with source "catalogue" reuse the latest catalogue (may be an older day): not observations; they only say
  which basket line a catalogue product serves.
- Catalogue history (changes only): the price on a day is the last entry on or before that day; a null entry means
  not listed. A shop listed under skipped[day] had an incomplete crawl: only its explicit entries of that day count.
  Days with no crawl give no rows. Nothing is filled across a gap.
- Two prices are kept apart: price_aed is the shelf (pack) price; unit_price_aed is the per-kg / piece / bunch
  price the category crawl reads. Same product, same day in both collections: one row, sources "both", the basket
  shelf price kept and a differing catalogue price written in the note. Within one run the shelf price comes from the
  barcode read first, then name search, then category.
"""
import csv, glob, json, os, re, sys
from collections import defaultdict

CHAIN_STORE = {"carrefour": "Carrefour", "lulu": "Lulu", "sharafdg": "Sharaf DG", "zara": "Zara", "max": "Max", "centrepoint": "Centrepoint"}
RANK = {"barcode": 0, "name_search": 1, "category": 2}
METHOD = {"barcode": "barcode", "name_search": "name search", "category": "category crawl"}


def chain_of(outlet):
    o = outlet.strip()
    if o.endswith("(Centrepoint)"):
        return "centrepoint"
    return {"Carrefour": "carrefour", "Lulu": "lulu", "Sharaf DG": "sharafdg", "Zara": "zara", "Max": "max"}.get(o, o.lower().replace(" ", ""))


def log_chain(name):
    n = name.lower()
    for k in CHAIN_STORE:
        if n.startswith(k) or n.replace(" ", "").startswith(k):
            return k
    return n.split()[0]


def pid_of(retailer_id, url):
    if retailer_id:
        return str(retailer_id).strip()
    m = re.search(r"/p/([\w-]+)", url or "") or re.search(r"-p(\d{6,})\.html", url or "")
    return m.group(1) if m else (url or "").strip()


def blocked_chains(run):
    out = set()
    for line in run.get("log") or []:
        m = re.match(r"^(.+?) barcode: (\d+) pages read, (\d+) failed", line)
        if m:
            read, failed = int(m.group(2)), int(m.group(3))
            tot = read + failed
            if (failed / tot if tot else 1) >= 0.9:
                out.add(log_chain(m.group(1)))
    return out


def num(v):
    try:
        f = float(v)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def rnd(v):
    return round(v, 2) if v is not None else None


def load_runs(runs_dir):
    """latest -auto run per day -> (day, run doc, rows)"""
    by_day = {}
    for f in sorted(glob.glob(os.path.join(runs_dir, "*-auto.json"))):
        rid = os.path.basename(f)[:-5]
        if not os.path.isdir(os.path.join(runs_dir, rid, "rows")):
            continue
        day = f"{rid[:4]}-{rid[4:6]}-{rid[6:8]}"
        if day not in by_day or rid > by_day[day][0]:
            by_day[day] = (rid, f)
    for day in sorted(by_day):
        rid, f = by_day[day]
        run = json.load(open(f, encoding="utf-8"))
        run = run.get("data", run)
        rows = []
        for cf in sorted(glob.glob(os.path.join(runs_dir, rid, "rows", "c*.json"))):
            d = json.load(open(cf, encoding="utf-8"))
            rows += d.get("data", d).get("rows", [])
        yield day, rid, run, rows


def main(runs_dir, hist_path, cat_path, out_xlsx, out_csv=None):
    hist = json.load(open(hist_path, encoding="utf-8"))
    cat = json.load(open(cat_path, encoding="utf-8"))
    ci = {c: i for i, c in enumerate(cat["cols"])}

    info = {}            # key -> descriptive fields (latest wins)
    for r in cat["rows"]:
        key = (chain_of(r[ci["outlet"]]), pid_of(r[ci["retailer_id"]], r[ci["url"]]))
        info[key] = {"store": r[ci["outlet"]], "title": r[ci["title"]], "brand": r[ci["brand"]], "size": r[ci["size"]],
                     "group": r[ci["division"]] or r[ci["group"]], "category": r[ci["category"]], "url": r[ci["url"]]}
    for k, p in hist["p"].items():
        outlet, raw = k.split("|", 1)
        key = (chain_of(outlet), pid_of("" if raw.startswith("http") else raw, p.get("u")))
        info.setdefault(key, {"store": outlet, "title": p.get("t", ""), "brand": "", "size": "", "group": p.get("g", ""),
                              "category": p.get("c", ""), "url": p.get("u", "")})

    lines = defaultdict(dict)   # key -> {item_code: name}
    obs = {}                    # (day, chain, pid) -> row dict
    stats = defaultdict(int)

    for day, rid, run, rows in load_runs(runs_dir):
        blocked = blocked_chains(run)
        best = {}
        for x in rows:
            ch = (x.get("retailer") or "").lower()
            pid = pid_of(x.get("retailer_id"), x.get("url"))
            price = num(x.get("price"))
            if x.get("url") or x.get("retailer_id"):
                if x.get("item_code"):
                    lines[(ch, pid)][x["item_code"]] = x.get("name", "")
            if price is None or str(x.get("accepted")).lower() not in ("yes", "true", "1"):
                stats["basket rows without a price (not found / not read)"] += 1
                continue
            src = x.get("source")
            if src == "catalogue":
                stats["basket rows reusing the catalogue (not counted twice)"] += 1
                continue
            if src == "category" and ch in blocked:
                stats["carried category rows of a refused shop (dropped)"] += 1
                continue
            if src not in RANK:
                stats[f"basket rows with unknown source {src}"] += 1
                continue
            k = (day, ch, pid)
            reg = num(x.get("regular_price"))
            b = best.setdefault(k, {"shelf": None, "regular": None, "rank": 9, "unit": None, "basis": "", "methods": set(),
                                    "title": "", "brand": "", "size": "", "group": "", "url": "", "note": ""})
            b["methods"].add(METHOD[src])
            for f, v in (("title", x.get("title")), ("brand", x.get("brand")), ("size", x.get("size")), ("url", x.get("url")),
                         ("group", f"{x.get('group_code', '')} {x.get('group_name', '')}".strip())):
                if v and not b[f]:
                    b[f] = v
            if src == "category":           # the category crawl gives a price per kg / piece / bunch
                up, basis = num(x.get("unit_price")) or price, x.get("price_basis") or ""
                if b["unit"] is None:
                    b["unit"], b["basis"] = up, basis
                elif abs(b["unit"] - up) > 1e-9:
                    b["note"] = (b["note"] + "; " if b["note"] else "") + f"category crawl also read {up:g}/{basis}"
                shelf = price if num(x.get("unit_price")) and abs(price - up) > 1e-9 else None
            else:
                shelf = price
            if shelf is not None:
                if b["shelf"] is None or RANK[src] < b["rank"]:
                    if b["shelf"] is not None and abs(b["shelf"] - shelf) > 1e-9:
                        b["note"] = (b["note"] + "; " if b["note"] else "") + f"another read {b['shelf']:g}"
                    b["shelf"], b["regular"], b["rank"] = shelf, reg or shelf, RANK[src]
                elif abs(b["shelf"] - shelf) > 1e-9:
                    b["note"] = (b["note"] + "; " if b["note"] else "") + f"{METHOD[src]} read {shelf:g}"
            if b.get("_seen"):
                stats["same product read twice in one run (merged)"] += 1
            b["_seen"] = True
        for k, b in best.items():
            obs[k] = {**b, "sources": "basket"}
        stats["basket observations"] += len(best)

    days = hist["days"]
    skipped = {d: set(v) for d, v in hist.get("skipped", {}).items()}
    for k, p in hist["p"].items():
        outlet, raw = k.split("|", 1)
        ch = chain_of(outlet)
        pid = pid_of("" if raw.startswith("http") else raw, p.get("u"))
        h = sorted(p["h"])
        j, cur = 0, None
        explicit = {}
        for e in h:
            explicit[e[0]] = e
        for di, day in enumerate(days):
            while j < len(h) and h[j][0] <= di:
                cur = h[j]
                j += 1
            if outlet in skipped.get(day, ()):
                e = explicit.get(di)
                if e is None:
                    stats["catalogue product-days skipped (incomplete crawl)"] += 1 if cur and cur[1] is not None else 0
                    continue
            else:
                e = cur
            if e is None or e[1] is None:
                continue
            price, reg = float(e[1]), float(e[2]) if e[2] is not None else float(e[1])
            key = (day, ch, pid)
            stats["catalogue observations"] += 1
            if key in obs:
                o = obs[key]
                if o["sources"] == "basket":
                    o["sources"] = "both"
                    o["methods"] = o["methods"] | {"catalogue crawl"}
                    o["store"] = outlet
                    if o["shelf"] is None:
                        o["shelf"], o["regular"] = price, reg
                    elif abs(o["shelf"] - price) > 1e-9:
                        o["note"] = (o["note"] + "; " if o["note"] else "") + f"catalogue read {price:g}"
                    stats["same product on the same day in both (merged)"] += 1
                continue
            inf = info.get((ch, pid), {})
            obs[key] = {"shelf": price, "regular": reg, "unit": None, "basis": "", "methods": {"catalogue crawl"}, "sources": "catalogue", "store": outlet,
                        "title": p.get("t", ""), "brand": inf.get("brand", ""), "size": inf.get("size", ""),
                        "group": inf.get("group") or p.get("g", ""), "category": p.get("c", ""), "url": p.get("u", ""), "note": ""}

    cols = ["date", "store", "chain", "product_id", "title", "brand", "size", "price_aed", "regular_price_aed", "on_offer",
            "unit_price_aed", "unit",
            "group", "category", "basket_item_codes", "basket_line_names", "found_by", "sources", "note", "url"]
    out = []
    for (day, ch, pid), o in sorted(obs.items()):
        inf = info.get((ch, pid), {})
        ln = lines.get((ch, pid), {})
        out.append([day, o.get("store") or inf.get("store") or CHAIN_STORE.get(ch, ch), ch, pid,
                    o.get("title") or inf.get("title", ""), o.get("brand") or inf.get("brand", ""), o.get("size") or inf.get("size", ""),
                    rnd(o["shelf"]), rnd(o["regular"]), "yes" if o["shelf"] and o["regular"] and o["regular"] > o["shelf"] + 1e-9 else "",
                    rnd(o["unit"]), o["basis"],
                    o.get("group") or inf.get("group", ""), o.get("category") or inf.get("category", ""),
                    " | ".join(sorted(ln)), " | ".join(ln[c] for c in sorted(ln)),
                    ", ".join(sorted(o["methods"])), o["sources"], o.get("note", ""), o.get("url") or inf.get("url", "")])

    keys = [(r[0], r[2], r[3]) for r in out]
    assert len(keys) == len(set(keys)), "duplicate (date, chain, product) rows"

    if out_csv:
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(out)
    write_xlsx(out_xlsx, cols, out, stats, days)
    for k in sorted(stats):
        print(f"{k}: {stats[k]:,}")
    print(f"rows: {len(out):,} · products: {len({(r[2], r[3]) for r in out}):,} · days: {len({r[0] for r in out})}")


def write_xlsx(path, cols, out, stats, cat_days):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook(write_only=True)
    ws = wb.create_sheet("All prices")
    ws.freeze_panes = "A2"
    widths = [11, 22, 11, 16, 50, 18, 10, 10, 10, 8, 10, 7, 26, 22, 20, 30, 26, 10, 26, 40]
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(65 + i)].width = w
    head = Font(bold=True, color="FFFFFF")
    fill = PatternFill("solid", fgColor="1B2A52")
    from openpyxl.cell import WriteOnlyCell
    hdr = []
    for c in cols:
        cell = WriteOnlyCell(ws, value=c)
        cell.font, cell.fill = head, fill
        hdr.append(cell)
    ws.append(hdr)
    for r in out:
        ws.append(r)

    s = wb.create_sheet("Summary")
    s.column_dimensions["A"].width = 30
    for c in "BCDEF":
        s.column_dimensions[c].width = 14
    s.append(["Store", "rows", "products", "basket only", "catalogue only", "both"])
    agg = defaultdict(lambda: [0, set(), 0, 0, 0])
    for r in out:
        a = agg[r[1]]
        a[0] += 1
        a[1].add(r[3])
        a[{"basket": 2, "catalogue": 3, "both": 4}[r[cols.index("sources")]]] += 1
    for st in sorted(agg):
        a = agg[st]
        s.append([st, a[0], len(a[1]), a[2], a[3], a[4]])
    s.append([])
    s.append(["Date", "rows"])
    per_day = defaultdict(int)
    for r in out:
        per_day[r[0]] += 1
    for d in sorted(per_day):
        s.append([d, per_day[d]])

    n = wb.create_sheet("Notes")
    n.column_dimensions["A"].width = 60
    n.column_dimensions["B"].width = 14
    for line in [
        "One row per date, shop and product. The two CPI collections (daily basket run: barcode, name search, category crawl;",
        "and the catalogue crawl) are merged on the shop's own product id, so no product appears twice on a day.",
        "sources: basket = only the basket run read it that day; catalogue = only the catalogue crawl; both = both read it",
        "(the basket price is kept; a different catalogue price is written in note).",
        "price_aed = shelf price of the pack as listed (barcode, name search or catalogue). unit_price_aed + unit = the price per kg,",
        "piece or bunch that the category crawl reads for loose and weighed food. The two are never mixed in one column.",
        "Not included: carried category rows of a shop that refused us that day, basket rows that reuse an older catalogue,",
        "and lines with no price (not found or not read). Refused pages stay unread; nothing is filled across a gap.",
        f"Catalogue crawl days: {cat_days[0]} to {cat_days[-1]} ({len(cat_days)} days). Prices in AED as listed online.",
        "basket_item_codes: the basket lines this product was matched to (by barcode or by spec).",
    ]:
        n.append([line])
    n.append([])
    for k in sorted(stats):
        n.append([k, stats[k]])
    wb.save(path)


if __name__ == "__main__":
    if len(sys.argv) < 5:
        sys.exit(__doc__)
    main(*sys.argv[1:6])
