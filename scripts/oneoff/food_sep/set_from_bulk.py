"""Set price from the bulk catalogue: for each exact-match food item, every catalogue listing of the same product type and
size at Carrefour and Lulu (brand ignored), its October mean regular/offer price, vs the official September price."""
import json, gzip, re, statistics as st, sys
from collections import defaultdict
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
REPO = "/home/user/CPI-Web-Scarping/"
items = {x["code"]: x for x in json.load(open("exact_items.json"))}
specs = {x["c"]: x for x in json.load(open(REPO + "data/basket/specs_en.json", encoding="utf-8"))}
h = json.load(gzip.open(REPO + "data/portal/cpi/catalogue/history.json.gz", "rt"))
days = h["days"]; oct_idx = [i for i, d in enumerate(days) if "2026-10-15" <= d <= "2026-10-31"]
STOP = {"a", "an", "the", "of", "and", "with", "in", "original", "pure", "premium", "fresh", "natural", "regular", "classic", "plain", "white",
        "whole", "full", "pack", "packet", "bottle", "jar", "tin", "can", "box", "bag", "piece", "pieces", "long", "grain", "fine", "mountain", "raw"}
UNIT = {"kg": ("g", 1000), "kgs": ("g", 1000), "g": ("g", 1), "gm": ("g", 1), "gr": ("g", 1), "grams": ("g", 1), "l": ("ml", 1000), "ltr": ("ml", 1000),
        "litre": ("ml", 1000), "liter": ("ml", 1000), "lt": ("ml", 1000), "ml": ("ml", 1), "pcs": ("pc", 1), "pc": ("pc", 1), "pieces": ("pc", 1), "piece": ("pc", 1)}
SIZE = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|kgs|gm|gr|grams|g|ltr|litre|liter|lt|l|ml|pcs|pc|pieces|piece)\b", re.I)
MULTI = re.compile(r"\b\d+\s*[x×]\s*\d|\bpack of\b|\bvalue pack\b|\btwin\b|\bbundle\b", re.I)

def size_of(text):
    m = SIZE.search(text or "")
    if not m: return None
    u, f = UNIT[m.group(2).lower()]; return (u, round(float(m.group(1)) * f))

def expand(hist):
    """day index -> (offer, regular) from the change-point history."""
    out, cur = {}, (None, None); j = 0
    for i in range(len(days)):
        while j < len(hist) and hist[j][0] <= i: cur = (hist[j][1], hist[j][2]); j += 1
        out[i] = cur
    return out

results = []
for code, it in items.items():
    sp = specs.get(code)
    if not sp: continue
    brand = {w.lower() for w in re.findall(r"[a-z']+", sp.get("brand_en", "") or "")}
    words = [w for w in re.findall(r"[a-z']+", (sp.get("product_en") or "").lower()) if w not in STOP and w not in brand and len(w) > 2]
    if not words: continue
    core = words[-1]; quals = words[:-1]
    must_not = [w.lower() for w in sp.get("must_not", [])]
    want = size_of(sp.get("size") or "")
    members = []
    for key, v in h["p"].items():
        if v["o"] not in ("Carrefour", "Lulu") or v.get("g") != "food": continue
        t = v["t"].lower()
        if core not in t: continue
        if quals and not any(q in t for q in quals): continue
        if any(m in t for m in must_not): continue
        if MULTI.search(v["t"]): continue
        if want and size_of(v["t"]) != want: continue
        ex = expand(v["h"]); pr = [ex[i] for i in oct_idx if ex[i][0]]
        if not pr: continue
        members.append(dict(outlet=v["o"], title=v["t"], url=v["u"], days=len(pr), offer=st.mean(p for p, _ in pr), regular=st.mean(r or p for p, r in pr)))
    if not members: continue
    per_outlet = defaultdict(list)
    for m in members: per_outlet[m["outlet"]].append(m)
    set_reg = st.mean(st.mean(m["regular"] for m in ms) for ms in per_outlet.values())      # mean per outlet, then across outlets
    set_off = st.mean(st.mean(m["offer"] for m in ms) for ms in per_outlet.values())
    results.append(dict(code=code, group=it["group"], desc=it["desc"], unit=it["unit"], sep=it["sep"], barcode_ours=it["ours"], barcode_pct=it["pct"],
                        barcode_shops=it["shops"], set_reg=set_reg, set_off=set_off, set_pct=(set_reg / it["sep"] - 1) * 100, set_off_pct=(set_off / it["sep"] - 1) * 100,
                        n=len(members), n_cf=len(per_outlet.get("Carrefour", [])), n_lulu=len(per_outlet.get("Lulu", [])),
                        members="; ".join(f"{m['outlet'][:2]}: {m['title']} ({m['regular']:.2f})" for m in sorted(members, key=lambda m: (m["outlet"], m["regular"]))),
                        core=core, quals=",".join(quals)))
json.dump(results, open("set_results.json", "w"), ensure_ascii=False, indent=1)
def stats(xs, k):
    v = [x[k] for x in xs]; return f"n={len(v)} median {st.median(v):+.1f}% within10 {100*sum(abs(a)<=10 for a in v)/len(v):.0f}% within5 {100*sum(abs(a)<=5 for a in v)/len(v):.0f}%"
ok = [r for r in results if 1/3 <= r["set_reg"] / r["sep"] <= 3]
print("items with a set:", len(results), "| comparable:", len(ok))
print("barcode  :", stats(ok, "barcode_pct")); print("set reg  :", stats(ok, "set_pct")); print("set offer:", stats(ok, "set_off_pct"))
one = [r for r in ok if r["barcode_shops"] == 1]
print("single-shop items:", len(one)); print("  barcode:", stats(one, "barcode_pct")); print("  set reg:", stats(one, "set_pct"))
big = [r for r in ok if abs(r["barcode_pct"]) > 15]
print("items where barcode is >15% off:", len(big)); print("  barcode:", stats(big, "barcode_pct")); print("  set reg:", stats(big, "set_pct"))
# excel
navy = PatternFill("solid", fgColor="14264B"); grn = PatternFill("solid", fgColor="E2F0D9"); amber = PatternFill("solid", fgColor="FFF2CC")
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "المجموعة من الكتالوج"; ws.sheet_view.rightToLeft = True
head = ["رمز السلعة", "المجموعة", "وصف السلعة", "الوحدة", "الرسمي سبتمبر", "سعرنا بالباركود (أكتوبر)", "فرق الباركود %", "متاجر الباركود",
        "سعر المجموعة (عادي)", "فرق المجموعة %", "سعر المجموعة (عرض)", "فرق المجموعة (عرض) %", "عدد المنتجات", "كارفور", "لولو", "كلمات البحث", "أعضاء المجموعة (السعر العادي)"]
ws.append(head)
for c in ws[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = navy; c.alignment = Alignment(wrap_text=True, vertical="center")
for col, w in zip("ABCDEFGHIJKLMNOPQ", (11, 22, 30, 8, 10, 11, 10, 8, 11, 10, 11, 10, 8, 7, 7, 18, 120)): ws.column_dimensions[col].width = w
ws.freeze_panes = "D2"
for r in sorted(results, key=lambda r: (r["group"], r["code"])):
    ws.append([r["code"], r["group"], r["desc"], r["unit"], round(r["sep"], 2), round(r["barcode_ours"], 2), round(r["barcode_pct"], 1), r["barcode_shops"],
               round(r["set_reg"], 2), round(r["set_pct"], 1), round(r["set_off"], 2), round(r["set_off_pct"], 1), r["n"], r["n_cf"], r["n_lulu"], f"{r['core']} + {r['quals']}", r["members"]])
    row = ws[ws.max_row]
    if abs(r["set_pct"]) < abs(r["barcode_pct"]): row[9].fill = grn
    if not (1/3 <= r["set_reg"] / r["sep"] <= 3): 
        for c in row: c.fill = amber
ws.auto_filter.ref = f"A1:Q{ws.max_row}"
n = wb.create_sheet("ملاحظات"); n.sheet_view.rightToLeft = True
for t in ["المجموعة = كل منتجات الكتالوج (زحف الفئات، 15-31 أكتوبر) في كارفور ولولو بنفس نوع المنتج ونفس الحجم، بغض النظر عن العلامة التجارية. العبوات المتعددة مستبعدة.",
          "سعر المجموعة = متوسط السعر العادي لكل منتج خلال أكتوبر، ثم متوسط منتجات المتجر، ثم متوسط المتجرين.",
          "كلمات البحث مأخوذة من المواصفة الإنجليزية للبند (specs_en.json) بعد حذف العلامة التجارية؛ هذه مطابقة آلية أولية، والقائمة تحتاج مراجعة بشرية قبل اعتمادها.",
          "أخضر: المجموعة أقرب للرسمي من الباركود. أصفر: سعر المجموعة أبعد من 3 أضعاف (المطابقة الآلية خاطئة على الأغلب).", "ملف داخلي: يحتوي أسعاراً رسمية."]: n.append([t])
wb.save(sys.argv[1]); print("saved", sys.argv[1])
