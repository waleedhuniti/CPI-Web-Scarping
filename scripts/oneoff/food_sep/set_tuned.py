"""Two tighter set definitions, same catalogue data:
 A. class-brands set: same type+size, but only the brands the basket names for that 7-digit class (e.g. Egyptian rice: Cleopatra, Pharoes, Sunwhite)
 B. calibrated set: same type+size, the <=3 listings per shop whose October regular price is nearest the official September price
    (circular for Sep/Oct by construction; its value is the list of products it picks, to be validated on November)."""
import json, gzip, re, statistics as st, sys
from collections import defaultdict
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
exec(open("set_from_bulk.py").read().split("results = []")[0])          # reuse loaders/helpers (items, specs, h, days, size_of, expand, STOP...)
basket = {b["item_code"]: b for b in json.load(open(REPO + "data/basket/basket.json", encoding="utf-8"))}
class_brands = defaultdict(set)
for c, sp in specs.items():
    for w in re.findall(r"[a-z']+", (sp.get("brand_en") or "").lower()):
        if len(w) > 2 and w not in STOP: class_brands[c[:7]].add(w)

def candidates(code):
    sp = specs.get(code)
    if not sp: return None, []
    brand = {w.lower() for w in re.findall(r"[a-z']+", sp.get("brand_en", "") or "")}
    words = [w for w in re.findall(r"[a-z']+", (sp.get("product_en") or "").lower()) if w not in STOP and w not in brand and len(w) > 2]
    if not words: return None, []
    core, quals = words[-1], words[:-1]; must_not = [w.lower() for w in sp.get("must_not", [])]; want = size_of(sp.get("size") or "")
    out = []
    for key, v in h["p"].items():
        if v["o"] not in ("Carrefour", "Lulu") or v.get("g") != "food": continue
        t = v["t"].lower()
        if core not in t or (quals and not any(q in t for q in quals)) or any(m in t for m in must_not) or MULTI.search(v["t"]): continue
        if want and size_of(v["t"]) != want: continue
        ex = expand(v["h"]); pr = [ex[i] for i in oct_idx if ex[i][0]]
        if pr: out.append(dict(outlet=v["o"], title=v["t"], regular=st.mean(r or p for p, r in pr), offer=st.mean(p for p, _ in pr)))
    return sp, out

def set_price(ms):
    po = defaultdict(list)
    for m in ms: po[m["outlet"]].append(m["regular"])
    return st.mean(st.mean(v) for v in po.values())

rows = []
for code, it in items.items():
    sp, cand = candidates(code)
    if not cand: continue
    brands = class_brands.get(code[:7], set())
    A = [m for m in cand if any(b in m["title"].lower() for b in brands)]
    B = []
    for o in ("Carrefour", "Lulu"):
        ms = sorted([m for m in cand if m["outlet"] == o], key=lambda m: abs(m["regular"] - it["sep"]))[:3]
        B += ms
    r = dict(code=code, group=it["group"], desc=it["desc"], unit=it["unit"], sep=it["sep"], barcode_pct=it["pct"], barcode_shops=it["shops"],
             all_n=len(cand), all_pct=(set_price(cand) / it["sep"] - 1) * 100,
             A_n=len(A), A_pct=(set_price(A) / it["sep"] - 1) * 100 if A else None, A_members="; ".join(f"{m['outlet'][:2]}: {m['title']} ({m['regular']:.2f})" for m in A),
             B_n=len(B), B_pct=(set_price(B) / it["sep"] - 1) * 100 if B else None, B_members="; ".join(f"{m['outlet'][:2]}: {m['title']} ({m['regular']:.2f})" for m in B),
             brands=",".join(sorted(brands)))
    rows.append(r)
json.dump(rows, open("set_tuned.json", "w"), ensure_ascii=False, indent=1)
def stats(v): v = [x for x in v if x is not None and abs(x) < 200]; return f"n={len(v):3d} median {st.median(v):+5.1f}%  within5 {100*sum(abs(a)<=5 for a in v)/len(v):3.0f}%  within10 {100*sum(abs(a)<=10 for a in v)/len(v):3.0f}%"
print("barcode        :", stats([r["barcode_pct"] for r in rows]))
print("all-brands set :", stats([r["all_pct"] for r in rows]))
print("A class-brands :", stats([r["A_pct"] for r in rows]))
print("B calibrated   :", stats([r["B_pct"] for r in rows]))
sub = [r for r in rows if r["A_pct"] is not None]
print("-- same items that have an A set:"); print("   barcode:", stats([r["barcode_pct"] for r in sub])); print("   A      :", stats([r["A_pct"] for r in sub]))
fail = [r for r in rows if abs(r["barcode_pct"]) > 15]
print("-- items where barcode is >15% off:", len(fail)); print("   barcode:", stats([r["barcode_pct"] for r in fail])); print("   A      :", stats([r["A_pct"] for r in fail])); print("   B      :", stats([r["B_pct"] for r in fail]))
# excel
navy = PatternFill("solid", fgColor="14264B")
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "ثلاث طرق للمجموعة"; ws.sheet_view.rightToLeft = True
ws.append(["رمز السلعة", "المجموعة", "وصف السلعة", "الوحدة", "الرسمي سبتمبر", "فرق الباركود %", "متاجر الباركود", "كل العلامات: عدد", "كل العلامات: فرق %",
           "علامات السلة: عدد", "علامات السلة: فرق %", "علامات السلة في هذا الصنف", "أعضاء مجموعة علامات السلة", "المعايَرة: عدد", "المعايَرة: فرق %", "أعضاء المجموعة المعايَرة (مرشحون للتثبيت)"])
for c in ws[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = navy; c.alignment = Alignment(wrap_text=True, vertical="center")
for col, w in zip("ABCDEFGHIJKLMNOP", (11, 22, 30, 8, 10, 10, 8, 8, 10, 8, 10, 22, 70, 8, 10, 90)): ws.column_dimensions[col].width = w
ws.freeze_panes = "D2"; rd = lambda v: None if v is None else round(v, 1)
for r in sorted(rows, key=lambda r: (r["group"], r["code"])):
    ws.append([r["code"], r["group"], r["desc"], r["unit"], round(r["sep"], 2), rd(r["barcode_pct"]), r["barcode_shops"], r["all_n"], rd(r["all_pct"]),
               r["A_n"], rd(r["A_pct"]), r["brands"], r["A_members"], r["B_n"], rd(r["B_pct"]), r["B_members"]])
ws.auto_filter.ref = f"A1:P{ws.max_row}"
n = wb.create_sheet("ملاحظات"); n.sheet_view.rightToLeft = True
for t in ["كل العلامات: كل منتجات الكتالوج بنفس النوع والحجم (الطريقة السابقة).",
          "علامات السلة: نفس النوع والحجم، لكن فقط العلامات التجارية التي تسمّيها السلة الرسمية لهذا الصنف (7 أرقام). غير دائرية: لا تستعمل السعر الرسمي.",
          "المعايَرة: نفس النوع والحجم، أقرب 3 منتجات في كل متجر إلى السعر الرسمي لسبتمبر. قريبة من الرسمي بالبناء، فلا تقيس الدقة؛ قيمتها أنها تقترح المنتجات التي يسعّرها الجامعون على الأغلب، وتُختبر على نوفمبر.",
          "ملف داخلي: يحتوي أسعاراً رسمية."]: n.append([t])
wb.save(sys.argv[1]); print("saved", sys.argv[1])
