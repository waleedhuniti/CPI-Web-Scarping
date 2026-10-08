import glob, json, os, re, sys
from datetime import datetime, timezone

W = "w"
UNITS = [(r"^(kg|kgs|kilo|kilos|kilogram|kilograms|كغ|كجم|كيلو|كيلوغرام|كيلوجرام|كلغ)$", "g", 1000),
         (r"^(g|gm|gms|gr|grm|gram|grams|غ|غم|غرام|جم|جرام|ج)$", "g", 1),
         (r"^(l|lt|ltr|ltrs|litre|litres|liter|liters|لتر|ل|ليتر)$", "ml", 1000),
         (r"^(ml|mls|millilitre|milliliter|مل|ملل|مليلتر)$", "ml", 1),
         (r"^(pc|pcs|piece|pieces|pack|eggs?|حبة|حبه|حبات|بيضة|بيضه|قطعة)$", "pc", 1)]
N, U = r"(\d+(?:\.\d+)?)", r"([a-z؀-ۿ]+)"


def digits(x): return re.sub(r"\D", "", str(x or ""))
def sform(r): d = digits(r); return "0" + d if len(d) == 11 else d


def valid(r):
    d = sform(r)
    if len(d) not in (8, 12, 13, 14): return False
    p = d.zfill(14); s = sum(int(p[i]) * (3 if i % 2 == 0 else 1) for i in range(13))
    return (10 - s % 10) % 10 == int(p[13])


def unit(u):
    for rx, b, f in UNITS:
        if re.match(rx, u.lower()): return b, f


def pqty(t):
    if not t: return None
    s = str(t).translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")).lower()
    m = re.search(N + r"\s*[x×*]\s*" + N + r"\s*" + U, s)
    if m and unit(m[3]): b, f = unit(m[3]); return b, float(m[1]) * float(m[2]) * f
    m = re.search(N + r"\s*" + U + r"\s*[x×*]\s*" + N, s)
    if m and unit(m[2]): b, f = unit(m[2]); return b, float(m[1]) * float(m[3]) * f
    for m in re.finditer(N + r"\s*" + U, s):
        if unit(m[2]): b, f = unit(m[2]); return b, float(m[1]) * f


def itemq(it): return (it["qty_unit"], float(it["qty_total"])) if it.get("qty_total") and it.get("qty_unit") else pqty(it.get("qty_raw"))
def num(v):
    try: return float(str(v).replace(",", "")) if v not in (None, "") else None
    except ValueError: return None


def doc(path):
    d = json.load(open(path, encoding="utf-8"))
    return d.get("data", d) if isinstance(d, dict) else d


def fill(v, subs):
    if isinstance(v, list): return [fill(x, subs) for x in v]
    if isinstance(v, dict): return {k: fill(x, subs) for k, x in v.items()}
    if isinstance(v, str):
        m = re.fullmatch(r"\{(\w+)\}", v)
        if m and m[1] in subs: return subs[m[1]]
    return v


def load():
    proj = doc(f"{W}/projects/cpi.json")
    items = [i for f in sorted(glob.glob(f"{W}/projects/cpi/basket/*.json")) for i in doc(f).get("items", [])]
    return proj, items


def plan():
    proj, items = load()
    codes = list(dict.fromkeys(sform(i["barcode_raw"]) for i in items if valid(i.get("barcode_raw"))))
    out = []
    for key, a in proj["actors"].items():
        if not a.get("enabled") or a.get("mode") == "single": continue
        size = max(1, int(a.get("batch_size") or 10))
        for k in range(0, len(codes), size):
            b = codes[k:k + size]; urls = [str(a.get("url_template", "")).replace("{barcode}", c) for c in b]
            inp = fill(a["input"], {"barcodes": b, "barcodes_json": json.dumps(b), "barcodes_text": "\n".join(b), "urls": urls,
                                    "start_urls": [{"url": u, "userData": {"ean": c}} for u, c in zip(urls, b)]})
            i = len([x for x in out if x["key"] == key])
            json.dump(inp, open(f"{W}/in_{key}_{i}.json", "w"), ensure_ascii=False)
            out.append({"key": key, "i": i, "actor": a["actor"], "fields": a.get("dataset_fields", ""), "batch": b})
    json.dump(out, open(f"{W}/plan.json", "w"))
    for x in out: print(x["key"], x["i"], x["actor"], f"input={W}/in_{x['key']}_{x['i']}.json", f"fields={x['fields']}")
    print(len(out), "runs,", len(codes), "barcodes")


def find_items(o):
    if isinstance(o, dict):
        if isinstance(o.get("items"), list): return o["items"]
        for v in o.values():
            r = find_items(v)
            if r is not None: return r
    if isinstance(o, list):
        if o and isinstance(o[0], dict) and o[0].get("type") == "text":
            for blk in o:
                try: r = find_items(json.loads(blk.get("text", "")))
                except ValueError: r = None
                if r is not None: return r
        elif all(isinstance(x, dict) for x in o): return o
    if isinstance(o, str):
        try: return find_items(json.loads(o))
        except ValueError: return None


def ingest(key, i, path):
    items = find_items(json.load(open(path, encoding="utf-8")))
    if items is None: sys.exit(f"no items found in {path}")
    json.dump(items, open(f"{W}/ds_{key}_{i}.json", "w"), ensure_ascii=False)
    print(key, i, len(items), "items")


LULU = re.compile(r"\[([^\]\n]+)\]\((https://gcc\.luluhypermarket\.com/en-ae/(?:[^)\s]*?/)?p/[^)\s]*?)\)\s*\n\s*\n([\d,]+(?:\.\d+)?)(?:\s*\n\s*\n([\d,]+(?:\.\d+)?))?")


def parse(parser, items, batch, cfg):
    rows, searched = [], set()
    if parser == "carrefour_actor":
        for it in items:
            c = digits(it.get("searchQuery"))
            if len(c) >= 8: rows.append(dict(code=c, title=it.get("title") or "", price=num(it.get("price")), regular_price=num(it.get("regularPrice")) or num(it.get("price")), url=it.get("url") or ""))
        searched = set(batch)
    elif parser == "lulu_search_markdown":
        for it in items:
            m = re.search(r"search_text=([^&]+)", it.get("url") or ""); md = it.get("markdown") or it.get("text") or ""
            if not m or ("All Products" not in md and "No results found" not in md): continue
            q = m[1]; searched.add(q)
            if "No results found" in md: continue
            for c in LULU.finditer(md):
                p, o = num(c[3]), num(c[4])
                rows.append(dict(code=q, title=c[1].strip(), price=p, regular_price=o if o and o > p else p, url=c[2].split("?")[0]))
    else:
        f = cfg.get("fields") or {}
        for it in items:
            r = {k: it.get(v) for k, v in f.items()}
            if r.get("code"): r["code"] = sform(r["code"]); rows.append(r)
        searched = set(batch)
    return rows, searched


def finish():
    proj, items = load(); runs = json.load(open(f"{W}/plan.json"))
    rid = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M") + "-auto"; started = os.environ.get("STARTED") or datetime.now(timezone.utc).isoformat(timespec="seconds")
    results, summary, log = [], {}, []
    for key, a in proj["actors"].items():
        mine = [r for r in runs if r["key"] == key]
        if not mine: continue
        label = a.get("label") or key; rows, searched, failed = [], set(), set()
        for r in mine:
            p = f"{W}/ds_{key}_{r['i']}.json"
            if not os.path.exists(p): failed |= set(r["batch"]); continue
            rr, s = parse(a.get("parser"), json.load(open(p, encoding="utf-8")), r["batch"], a); rows += rr; searched |= s
        ok = sum(os.path.exists(f"{W}/ds_{key}_{r['i']}.json") for r in mine)
        log.append(f"{label}: {ok} of {len(mine)} runs ok, {len(rows)} listings")
        by = {}
        for r in rows: by.setdefault(r["code"], {})[r["url"] or r["title"]] = r
        res = []
        for it in items:
            if not valid(it.get("barcode_raw")): continue
            code = sform(it["barcode_raw"])
            base = dict(actor=label, item_code=it.get("item_code", ""), name=it.get("name_ar", ""), brand=it.get("brand_ar", ""), basket_qty=it.get("qty_raw", ""), barcode=code, title="", price="", regular_price="", url="", accepted="no")
            hits = list(by.get(code, {}).values())
            if not hits:
                res.append(dict(base, status="error" if code in failed else "not_found" if code in searched else "not_searched")); continue
            want, best = itemq(it), None
            for h in hits:
                got = pqty(h["title"]) or pqty(re.sub(r"[-_/]", " ", h.get("url") or ""))
                if not want or not got: st = "size_unverified"
                elif abs(want[1] - got[1]) <= want[1] * 0.005:
                    st = ("barcode_match" if len(hits) == 1 else "multiple_results") if want[0] == got[0] else ("unit_label" if "pc" not in (want[0], got[0]) and len(hits) == 1 else "size_unverified")
                else: st = "qty_mismatch"
                rank = {"barcode_match": 5, "unit_label": 4, "multiple_results": 3, "size_unverified": 2, "qty_mismatch": 1}[st]
                if not best or rank > best[0]: best = (rank, st, h)
            _, st, h = best
            res.append(dict(base, status=st, accepted="yes" if st in ("barcode_match", "unit_label") else "no", title=h["title"], price=h["price"], regular_price=h["regular_price"], url=h["url"]))
        st = {}
        for r in res: st[r["status"]] = st.get(r["status"], 0) + 1
        summary[key] = dict(label=label, lines=len(res), accepted=sum(r["accepted"] == "yes" for r in res), statuses=st); results += res
    os.makedirs(f"{W}/out", exist_ok=True)
    chunks, cur, size = [], [], 0
    for r in results:
        s = len(json.dumps(r, ensure_ascii=False))
        if size + s > 110000 and cur: chunks.append(cur); cur, size = [], 0
        cur.append(r); size += s
    chunks.append(cur)
    for i, c in enumerate(chunks): json.dump({"rows": c, "i": i}, open(f"{W}/out/c{i:03d}.json", "w"), ensure_ascii=False)
    acc = sum(r["accepted"] == "yes" for r in results)
    status = "done" if all(os.path.exists(f"{W}/ds_{r['key']}_{r['i']}.json") for r in runs) else "error"
    json.dump(dict(startedAt=started, finishedAt=datetime.now(timezone.utc).isoformat(timespec="seconds"), status=status, summary=summary, chunks=len(chunks), count=len(results), accepted=acc, log=log + ["scheduled run"]), open(f"{W}/out/run.json", "w"), ensure_ascii=False)
    json.dump({"lastRun": {"at": started, "status": status, "accepted": acc}}, open(f"{W}/out/last.json", "w"))
    print("RUN_ID", rid, "chunks", len(chunks), "rows", len(results), "accepted", acc, "status", status)
    for k, v in summary.items(): print(" ", v["label"], v["accepted"], "/", v["lines"], v["statuses"])


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "plan": plan()
    elif cmd == "ingest": ingest(*sys.argv[2:5])
    elif cmd == "finish": finish()
