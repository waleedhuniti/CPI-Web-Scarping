import json, sys, collections
d = json.load(open(sys.argv[1], encoding="utf-8"))
m = d["meta"]; ob = d["observations"]
it = m["items"]
c = collections.Counter((i["kind"], i["market"]) for i in it)
print("items", len(it), dict(c), "cities", len({i["city"] for i in it if i["kind"] == "hotel"}))
print("outlets", len(m["outlets"]), [o["code"] for o in m["outlets"]])
print("periods", m["periods"])
for w in m["weeks"]: print(" week", w["id"], w["tickets"], w["packages"], w["collected_on"], w["status"])
assert all(i["collection"] == {"frequency": "monthly", "lead_days": None, "note": "to be determined"} for i in it)
print("sample", len(m["sample"]), collections.Counter((s["survey"], s["outlet"]) for s in m["sample"]))
assert len({i["code"] for i in it}) == len(it) and len({o["code"] for o in m["outlets"]}) == 11
codes = {i["code"] for i in it}; ocodes = {o["code"] for o in m["outlets"]}
samp = {(s["outlet"], s["item"]) for s in m["sample"]}
for wk, doc in ob.items():
    rows = doc["rows"]
    assert all(r["week"] == wk and r["item"] in codes and r["outlet"] in ocodes and (r["outlet"], r["item"]) in samp for r in rows)
    assert len({(r["outlet"], r["item"], r["leg"]) for r in rows}) == len(rows)
    assert all(r["leg"] in ("out", "back", "package") for r in rows)
    print(wk, len(rows), dict(collections.Counter((r["survey"], r["status"]) for r in rows)))
name = {i["code"]: i["name_en"] for i in it}
def get(wk, o, item, leg):
    return [r for r in ob[wk]["rows"] if r["outlet"] == o and r["item"] == item and r["leg"] == leg]
print("--- known cases")
for wk in ob:
    for leg in ("out", "back"):
        r = get(wk, "ba", "TF-LHR", leg); print(wk, "BA", leg, [(x.get("lowest"), x.get("highest"), x["status"]) for x in r])
for wk in ob:
    print(wk, "FZ RUH", [(x["leg"], x.get("lowest"), x.get("highest"), x["status"]) for x in ob[wk]["rows"] if x["outlet"] == "flydubai" and x["item"] == "TD-RUH"])
for o in ("pia", "egyptair", "saudia", "rj", "airindia", "turkish", "emirates", "ekholidays"):
    print(o, {wk: sorted(collections.Counter(r["status"] for r in ob[wk]["rows"] if r["outlet"] == o).items()) for wk in ob})
print("--- outlet state per week (5.1 SPPI parser)")
for o in ocodes:
    st = {}
    for wk in ob:
        rs = [r for r in ob[wk]["rows"] if r["outlet"] == o]
        s = {r["status"] for r in rs}
        st[wk] = "Not read" if not rs else "Read OK" if s == {"ok"} else "Blocked" if s == {"blocked"} else "Failed" if s == {"failed"} else "Partial"
    print(" ", o, st)
print("--- flags")
for wk in ob:
    for r in ob[wk]["rows"]:
        if r.get("flags"): print(" ", wk, r["outlet"], r["item"], r["leg"], r["flags"], r.get("date_used"), r.get("matched_name", ""))
print("size", len(json.dumps(d, ensure_ascii=False).encode()), {wk: len(json.dumps(ob[wk], ensure_ascii=False).encode()) for wk in ob}, "meta", len(json.dumps(m, ensure_ascii=False).encode()))
