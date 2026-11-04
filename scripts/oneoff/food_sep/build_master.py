"""One record per official food item (637) with everything an agent needs to diagnose it offline."""
import csv, gzip, json, re, statistics as st
from collections import defaultdict, Counter
import openpyxl
REPO = "/home/user/CPI-Web-Scarping/"; UP = "/root/.claude/uploads/60ceec26-2c73-59ee-8091-dd0a0c8d8ad5/"
FS = "/tmp/claude-0/-home-user-CPI-Web-Scarping/60ceec26-2c73-59ee-8091-dd0a0c8d8ad5/scratchpad/food_sep/"
BR = "/tmp/claude-0/-home-user-CPI-Web-Scarping/60ceec26-2c73-59ee-8091-dd0a0c8d8ad5/scratchpad/agents/brainstorm/"
num = lambda v: float(v) if isinstance(v, (int, float)) and v > 0 else None
# official
off = {}
for r in list(openpyxl.load_workbook(UP + "528ab259-_____________________.xlsx", read_only=True, data_only=True).worksheets[0].iter_rows(values_only=True))[1:]:
    c = str(r[0] or "").strip().zfill(9)
    if c.startswith("011"): off[c] = dict(desc=str(r[1] or "").strip(), unit=str(r[2] or "").strip(), aug=num(r[3]), sep=num(r[4]), oct=num(r[5]))
# basket source (office file) + basket.json + specs
src = {}
for r in openpyxl.load_workbook(REPO + "data/basket/basket_source.xlsx", read_only=True, data_only=True).worksheets[0].iter_rows(values_only=True):
    c = str(r[1] or "").strip()
    if len(c) == 9 and c.startswith("011"): src[c] = dict(name=str(r[2] or "").strip(), brand=str(r[3] or "").strip(), barcode=str(r[4] or "").strip(), origin=str(r[5] or "").strip(), qty=str(r[6] or "").strip())
basket = {b["item_code"]: b for b in json.load(open(REPO + "data/basket/basket.json", encoding="utf-8"))}
specs = {s["c"]: s for s in json.load(open(REPO + "data/basket/specs_en.json", encoding="utf-8"))}
exact = {x["code"]: x for x in json.load(open(FS + "exact_items.json"))}
checker = {r["﻿code"] if "﻿code" in r else r["code"]: r for r in csv.DictReader(open(BR + "checker_items.csv", encoding="utf-8-sig"))}
# our October rows (all statuses)
daily = defaultdict(lambda: defaultdict(lambda: dict(status=Counter(), detail=Counter(), titles=Counter(), prices=[], regs=[], urls=Counter(), source=Counter(), notes=Counter())))
for r in csv.DictReader(open(REPO + "data/exports/CPI_basket_12-29_Oct.csv", encoding="utf-8")):
    c = r["item_code"].zfill(9)
    if not c.startswith("011"): continue
    d = daily[c][r["retailer"]]
    d["status"][r["status"] + ("/accepted" if r["accepted"] == "yes" else "")] += 1
    if r.get("detail"): d["detail"][r["detail"][:60]] += 1
    if r.get("note") and r["accepted"] != "yes": d["notes"][r["note"][:90]] += 1
    if r["title"]:
        d["titles"][r["title"]] += 1; d["urls"][r["url"]] += 1; d["source"][r["source"]] += 1
        try:
            d["prices"].append(float(r["price"])); d["regs"].append(float(r["regular_price"] or r["price"]))
        except ValueError: pass
# catalogue history (15 Oct - 3 Nov): candidates by product type
h = json.load(gzip.open(REPO + "data/portal/cpi/catalogue/history.json.gz", "rt")); days = h["days"]
oct_idx = [i for i, d in enumerate(days) if "2026-10-15" <= d <= "2026-10-31"]
def expand(hist):
    out, cur, j = {}, (None, None), 0
    for i in range(len(days)):
        while j < len(hist) and hist[j][0] <= i: cur = (hist[j][1], hist[j][2]); j += 1
        out[i] = cur
    return out
listings = []
for key, v in h["p"].items():
    if v["o"] not in ("Carrefour", "Lulu"): continue
    ex = expand(v["h"]); pr = [ex[i] for i in oct_idx if ex[i][0]]
    last = [ex[i] for i in range(len(days)) if ex[i][0]]
    listings.append(dict(outlet=v["o"], title=v["t"], url=v["u"], cat=v.get("c"), grp=v.get("g"), tl=v["t"].lower(),
                         oct_offer=round(st.mean(p for p, _ in pr), 2) if pr else None, oct_regular=round(st.mean(r or p for p, r in pr), 2) if pr else None,
                         last_price=last[-1][0] if last else None, listed_days=len([1 for i in range(len(days)) if ex[i][0]])))
STOP = {"a","an","the","of","and","with","in","original","pure","premium","fresh","natural","regular","classic","plain","white","whole","full","pack","packet","bottle","jar","tin","can","box","bag","piece","pieces","long","grain","fine","mountain","raw","flavour","flavor"}
UNIT = {"kg":("g",1000),"kgs":("g",1000),"g":("g",1),"gm":("g",1),"gr":("g",1),"grams":("g",1),"l":("ml",1000),"ltr":("ml",1000),"litre":("ml",1000),"liter":("ml",1000),"lt":("ml",1000),"ml":("ml",1),"pcs":("pc",1),"pc":("pc",1),"pieces":("pc",1),"piece":("pc",1)}
SIZE = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|kgs|gm|gr|grams|g|ltr|litre|liter|lt|l|ml|pcs|pc|pieces|piece)\b", re.I)
def size_of(t):
    m = SIZE.search(t or "");
    if not m: return None
    u, f = UNIT[m.group(2).lower()]; return f"{round(float(m.group(1))*f)} {u}"
def stem(w):
    w = w.lower()
    for suf in ("ies", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4: return w[:-len(suf)] + ("y" if suf == "ies" else "")
    return w
def candidates(code):
    sp = specs.get(code)
    if not sp: return []
    brand = {stem(w) for w in re.findall(r"[a-z']+", sp.get("brand_en") or "")}
    words = [stem(w) for w in re.findall(r"[a-z']+", (sp.get("product_en") or "").lower()) if w not in STOP and len(w) > 2]
    extra = [stem(w) for mh in sp.get("must_have", []) for w in re.findall(r"[a-z']+", mh.lower()) if w not in STOP and len(w) > 2]
    nonbrand = [w for w in words if w not in brand]
    if not nonbrand and not extra: return []
    core = nonbrand[-1] if nonbrand else extra[-1]
    quals = sorted({w for w in nonbrand + extra if w != core})
    must_not = [w.lower() for w in sp.get("must_not", [])]
    want = size_of(sp.get("size") or "")
    out = []
    for L in listings:
        t = L["tl"]
        if core not in t and core not in (L["cat"] or ""): continue
        if any(re.search(r"\b" + re.escape(m) + r"\b", t) for m in must_not): continue
        score = sum(q in t for q in quals) + 2 * any(b in t for b in brand) + (2 if want and size_of(L["title"]) == want else 0) + (1 if core in t else 0)
        out.append((score, L))
    if not out:                                                    # loose fallback: any spec word, incl. query_en
        allw = sorted({w for w in words + extra + [stem(w) for w in re.findall(r"[a-z']+", (sp.get("query_en") or "").lower()) if w not in STOP and len(w) > 2] if w not in brand})
        for L in listings:
            t = L["tl"]; k = sum(w in t for w in allw)
            if k and not any(re.search(r"\b" + re.escape(m) + r"\b", t) for m in must_not): out.append((k, L))
    out.sort(key=lambda x: (-x[0], x[1]["outlet"]))
    return [dict(outlet=L["outlet"], title=L["title"], url=L["url"], category=L["cat"], size=size_of(L["title"]), oct_regular=L["oct_regular"], oct_offer=L["oct_offer"], last_price=L["last_price"], listed_days=L["listed_days"], score=s) for s, L in out[:16]]
items = []
for c, o in sorted(off.items()):
    b = basket.get(c, {}); s = src.get(c, {}); sp = specs.get(c, {}); e = exact.get(c); ck = checker.get(c, {})
    shops = {}
    for shop, d in daily.get(c, {}).items():
        shops[shop] = dict(status_counts=dict(d["status"]), details=dict(d["detail"].most_common(3)), notes=dict(d["notes"].most_common(2)), source=dict(d["source"]),
                           matched=[dict(title=t, n=n) for t, n in d["titles"].most_common(3)], urls=[u for u, _ in d["urls"].most_common(3)],
                           avg_price=round(st.mean(d["prices"]), 2) if d["prices"] else None, avg_regular=round(st.mean(d["regs"]), 2) if d["regs"] else None)
    if e: status = "exact_match"; comp = dict(ours_oct=round(e["ours"], 2), ours_regular=round(e["ours_reg"], 2), pct_vs_sep=round(e["pct"], 1), pct_regular=round(e["pct_reg"], 1), shops_found=e["shops"], far=e["far"], carrefour=e["carrefour"] and round(e["carrefour"], 2), lulu=e["lulu"] and round(e["lulu"], 2))
    elif any("category" in sh.get("source", {}) for sh in shops.values()): status = "product_set_estimate_only"; comp = dict(set_estimate=round(float(ck["ours"]), 2) if ck.get("ours") else None, pct_vs_sep=round((float(ck["ratio"]) - 1) * 100, 1) if ck.get("ratio") else None)
    elif any("catalogue" in sh.get("source", {}) for sh in shops.values()): status = "catalogue_name_match"; comp = dict(ours=round(float(ck["ours"]), 2) if ck.get("ours") else None, pct_vs_sep=round((float(ck["ratio"]) - 1) * 100, 1) if ck.get("ratio") else None)
    else: status = "no_price"; comp = {}
    items.append(dict(code=c, class_code=b.get("class_code"), class_name=b.get("class_name"), cpi_group=b.get("cpi_group"),
                      official=dict(desc=o["desc"], unit=o["unit"], brand=s.get("brand"), barcode=s.get("barcode"), origin=s.get("origin"), qty=s.get("qty"), price_aug=o["aug"], price_sep=o["sep"], price_oct=o["oct"]),
                      basket=dict(match_mode=b.get("match_mode"), fresh_type=b.get("fresh_type"), barcode_kind=b.get("barcode_kind"), qty_unit=b.get("qty_unit"), qty_total=b.get("qty_total")),
                      spec_en=dict(product_en=sp.get("product_en"), brand_en=sp.get("brand_en"), size=sp.get("size"), must_have=sp.get("must_have"), must_not=sp.get("must_not"), query_en=sp.get("query_en")),
                      status=status, comparison=comp, checker_causes=ck.get("causes"), our_october=shops, catalogue_candidates=candidates(c)))
json.dump(items, open("master.json", "w"), ensure_ascii=False, indent=1)
print(len(items), Counter(i["status"] for i in items))
# batches by cpi group, equalised chunks of <=32
import math
by = defaultdict(list)
for i in items: by[i["cpi_group"] or "?"].append(i)
n = 0; index = []
for g, xs in by.items():
    k = math.ceil(len(xs) / 32); size = math.ceil(len(xs) / k)
    for s0 in range(0, len(xs), size):
        n += 1; chunk = xs[s0:s0+size]
        json.dump(chunk, open(f"batch_{n:02d}.json", "w"), ensure_ascii=False, indent=1)
        index.append(dict(batch=n, file=f"batch_{n:02d}.json", group=g, n=len(chunk), statuses=dict(Counter(i["status"] for i in chunk))))
json.dump(index, open("batches.json", "w"), ensure_ascii=False, indent=1)
print(len(index), [b["n"] for b in index])
