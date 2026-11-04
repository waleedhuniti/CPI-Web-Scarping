"""Food (CPI 011): official September 2026 item prices vs our scraped October 2026 prices (12-29 Oct, accepted rows)."""
import csv, json, math, re, statistics as st, sys
from collections import defaultdict, Counter
import openpyxl
sys.path.insert(0, "/home/user/CPI-Web-Scarping/scripts")
from compare_official_month import WEIGHT

UP = "/root/.claude/uploads/60ceec26-2c73-59ee-8091-dd0a0c8d8ad5/"
REPO = "/home/user/CPI-Web-Scarping/"
FAMILY = {("kg", "g"), ("l", "ml"), ("pc", "pc")}          # listing basis vs line unit that convert correctly

ws = openpyxl.load_workbook(UP + "528ab259-_____________________.xlsx", read_only=True, data_only=True).worksheets[0]
off = {}
for r in list(ws.iter_rows(values_only=True))[1:]:
    if r[0] is None: continue
    num = lambda v: float(v) if isinstance(v, (int, float)) and v > 0 else None
    off[str(r[0]).strip().zfill(9)] = dict(desc=str(r[1] or "").strip(), unit=str(r[2] or "").strip(), aug=num(r[3]), sep=num(r[4]), oct=num(r[5]))

W = {}
for r in list(openpyxl.load_workbook(UP + "1eab1d7a-Book1.xlsx", read_only=True, data_only=True).worksheets[0].iter_rows(values_only=True))[1:]:
    try: W[str(r[1]).strip()] = float(r[3])
    except (TypeError, ValueError): pass
basket = {b["item_code"]: b for b in json.load(open(REPO + "data/basket/basket.json", encoding="utf-8"))}

TIER = {"barcode": "exact", "name_search": "exact", "category": "product set", "catalogue": "catalogue"}   # product set = chained estimate over a set of listings, not a price
obs = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
meta = defaultdict(lambda: dict(src=Counter(), shops=set(), titles=Counter(), unitbad=0))
for r in csv.DictReader(open(REPO + "data/exports/CPI_basket_12-29_Oct.csv", encoding="utf-8")):
    c = r["item_code"].zfill(9)
    if r["accepted"] != "yes" or not c.startswith("011") or c not in off or not off[c]["sep"]: continue
    # the price in the line's own unit: unit price x the line's quantity, only when the listing's price basis is in the
    # same unit family as the line (kg<->g, l<->ml, piece<->piece, bunch<->bunch); anything else cannot be compared
    try: p, up, tot = float(r["price"]), float(r["unit_price"] or 0), float(r["qty_total"] or 0)
    except ValueError: continue
    basis, lu = r["price_basis"], r["qty_unit"]
    if basis == "" and lu in ("pc", "") and r["source"] != "category":
        v = p                                               # a piece line priced from the shelf price
    elif (basis, lu) in {("kg", "g"), ("l", "ml"), ("pc", "pc"), ("bunch", "bunch")} and up > 0 and tot > 0:
        v = up * tot / {"g": 1000, "ml": 1000, "pc": 1, "bunch": 1}[lu]
    else:
        meta[c]["unitbad"] += 1; continue
    if v <= 0: continue
    obs[c][r["run_date"]][r["retailer"]].append(v)
    m = meta[c]; m["src"][TIER.get(r["source"], r["source"])] += 1; m["shops"].add(r["retailer"]); m["titles"][r["title"]] += 1; m.setdefault("notes", Counter())[r["note"][:90]] += 1

items = []
for c, days in obs.items():
    daily = [st.mean(st.mean(v) for v in shops.values()) for shops in days.values()]
    ours = st.mean(daily); o = off[c]; m = meta[c]
    b = basket.get(c, {})
    cls = str(b.get("class_code") or c[:7]); grp = re.sub(r"^\d+\s*-\s*", "", str(b.get("group_name", ""))).strip()
    ratio = ours / o["sep"]
    items.append(dict(code=c, group=grp, cls=cls, desc=o["desc"], unit=o["unit"], sep=o["sep"], oct_off=o["oct"], ours=ours,
                      pct=(ratio - 1) * 100, off_chg=((o["oct"] / o["sep"] - 1) * 100) if o["oct"] else None,
                      far=not (1/3 <= ratio <= 3), tier=m["src"].most_common(1)[0][0], shops=", ".join(sorted(m["shops"])),
                      days=len(days), title=m["titles"].most_common(1)[0][0], titles=" / ".join(t for t, _ in m["titles"].most_common(4)),
                      note=m["notes"].most_common(1)[0][0], w=W.get(cls, 0.0)))
nofood = sum(1 for c, o in off.items() if c.startswith("011") and o["sep"])
unitbad = sorted(c for c, m in meta.items() if m["unitbad"] and c not in obs)

def agg(xs):
    ok = [x for x in xs if not x["far"]]
    if not ok: return None
    lr = [math.log(x["ours"] / x["sep"]) for x in ok]
    cnt = Counter(x["cls"] for x in ok)
    ws_ = [x["w"] / cnt[x["cls"]] for x in ok]
    wg = math.exp(sum(w * l for w, l in zip(ws_, lr)) / sum(ws_)) if sum(ws_) else None
    return dict(n=len(ok), far=len(xs) - len(ok), geo=(math.exp(st.mean(lr)) - 1) * 100, med=st.median(x["pct"] for x in ok),
                wgeo=(wg - 1) * 100 if wg else None, within10=100 * sum(abs(x["pct"]) <= 10 for x in ok) / len(ok),
                offchg=(math.exp(st.mean(math.log(x["oct_off"] / x["sep"]) for x in ok if x["oct_off"])) - 1) * 100)
out = dict(n_official_food=nofood, n_compared=len(items), unit_excluded=len(unitbad))
out["all"] = agg(items)
for t in ("exact", "product set", "catalogue"):
    out[t] = agg([x for x in items if x["tier"] == t])
groups = defaultdict(list)
for x in items: groups[x["group"]].append(x)
out["groups"] = {g: dict(all=agg(xs), exact=agg([x for x in xs if x["tier"] == "exact"])) for g, xs in groups.items()}
json.dump(dict(summary=out, items=items, unitbad=unitbad), open(sys.argv[1], "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps({k: v for k, v in out.items() if k != "groups"}, ensure_ascii=False, indent=1, default=lambda v: round(v, 2)))
for g, d in sorted(out["groups"].items(), key=lambda kv: -kv[1]["all"]["n"] if kv[1]["all"] else 0):
    a, e = d["all"], d["exact"]
    if a: print(f"{g[:40]:40s} n={a['n']:3d} far={a['far']:2d} geo={a['geo']:+6.1f} med={a['med']:+6.1f} w10={a['within10']:4.0f}% offchg={a['offchg']:+5.1f} | exact n={e['n'] if e else 0} geo={(e['geo'] if e else 0):+6.1f}")
