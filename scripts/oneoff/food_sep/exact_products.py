"""Exact-match food products: official September price (mean of 4-5 shops) vs our October price (Lulu, Carrefour), per product."""
import csv, json, statistics as st, sys
from collections import defaultdict
import openpyxl
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Font, PatternFill, Alignment
sys.path.insert(0, "/home/user/CPI-Web-Scarping/scripts")
from compare_official_month import WEIGHT
UP = "/root/.claude/uploads/60ceec26-2c73-59ee-8091-dd0a0c8d8ad5/"; REPO = "/home/user/CPI-Web-Scarping/"
ws = openpyxl.load_workbook(UP + "528ab259-_____________________.xlsx", read_only=True, data_only=True).worksheets[0]
off = {}
for r in list(ws.iter_rows(values_only=True))[1:]:
    if r[0] is None or not isinstance(r[4], (int, float)) or r[4] <= 0: continue
    off[str(r[0]).strip().zfill(9)] = dict(desc=str(r[1] or "").strip(), unit=str(r[2] or "").strip(), sep=float(r[4]), oct=float(r[5]) if isinstance(r[5], (int, float)) else None)
basket = {b["item_code"]: b for b in json.load(open(REPO + "data/basket/basket.json", encoding="utf-8"))}
obs = defaultdict(lambda: defaultdict(lambda: defaultdict(list))); reg = defaultdict(lambda: defaultdict(lambda: defaultdict(list))); titles = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
for r in csv.DictReader(open(REPO + "data/exports/CPI_basket_12-29_Oct.csv", encoding="utf-8")):
    c = r["item_code"].zfill(9)
    if r["accepted"] != "yes" or r["source"] not in ("barcode", "name_search") or not c.startswith("011") or c not in off: continue
    try: p, up, tot = float(r["price"]), float(r["unit_price"] or 0), float(r["qty_total"] or 0)
    except ValueError: continue
    basis, lu = r["price_basis"], r["qty_unit"]
    if basis == "" and lu in ("pc", ""): v = p
    elif (basis, lu) in {("kg", "g"), ("l", "ml"), ("pc", "pc"), ("bunch", "bunch")} and up > 0 and tot > 0: v = up * tot / {"g": 1000, "ml": 1000, "pc": 1, "bunch": 1}[lu]
    else: continue
    obs[c][r["retailer"]][r["run_date"]].append(v); titles[c][r["retailer"]][r["title"]] += 1
    try: rp = float(r["regular_price"] or 0)
    except ValueError: rp = 0
    reg[c][r["retailer"]][r["run_date"]].append(v * rp / p if rp > p else v)      # the regular (pre-offer) price in the same unit
items = []
for c, shops in obs.items():
    per = {s: st.mean(st.mean(v) for v in days.values()) for s, days in shops.items()}
    perr = {s: st.mean(st.mean(v) for v in days.values()) for s, days in reg[c].items()}
    ours = st.mean(per.values()); ours_reg = st.mean(perr.values()); o = off[c]
    items.append(dict(code=c, group=str(basket.get(c, {}).get("group_name", "")).split("-", 1)[-1].strip(), desc=o["desc"], unit=o["unit"], sep=o["sep"], oct_off=o["oct"],
                      carrefour=per.get("carrefour"), lulu=per.get("lulu"), ours=ours, diff=ours - o["sep"], pct=(ours / o["sep"] - 1) * 100,
                      carrefour_reg=perr.get("carrefour"), lulu_reg=perr.get("lulu"), ours_reg=ours_reg, diff_reg=ours_reg - o["sep"], pct_reg=(ours_reg / o["sep"] - 1) * 100,
                      shops=len(per), on_offer=round(ours_reg, 2) != round(ours, 2),
                      far=not (1/3 <= ours / o["sep"] <= 3), days=max(len(d) for d in shops.values()),
                      title=" / ".join(f"{s}: {max(t, key=t.get)}" for s, t in titles[c].items())))
items.sort(key=lambda x: (x["group"], x["code"]))
json.dump(items, open("exact_items.json", "w"), ensure_ascii=False, indent=1)
ok = [x for x in items if not x["far"]]
print(len(items), "products;", len(ok), "comparable;", "mean diff AED", round(st.mean(x["diff"] for x in ok), 2), "median %", round(st.median(x["pct"] for x in ok), 2))
# ---- Excel
navy = PatternFill("solid", fgColor="14264B"); amber = PatternFill("solid", fgColor="FFF2CC"); grn = PatternFill("solid", fgColor="E2F0D9"); red = PatternFill("solid", fgColor="FCE4E4")
wb = openpyxl.Workbook(); sh = wb.active; sh.title = "فرق السعر لكل منتج"; sh.sheet_view.rightToLeft = True
head = ["رمز السلعة", "المجموعة", "وصف السلعة (الرسمي)", "وحدة البيع", "الرسمي سبتمبر (متوسط 4-5 محلات)", "سعرنا أكتوبر (متوسط المتاجر التي وُجد فيها)",
        "كارفور أكتوبر", "لولو أكتوبر", "فرق السعر (درهم)", "فرق السعر %", "عدد المتاجر التي وُجد فيها", "سعرنا بالسعر العادي (قبل العرض)",
        "كارفور عادي", "لولو عادي", "فرق السعر العادي (درهم)", "فرق السعر العادي %", "الرسمي أكتوبر", "أيام الرصد", "المنتج الذي التُقط", "ملاحظة"]
sh.append(head)
for c in sh[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = navy; c.alignment = Alignment(wrap_text=True, vertical="center")
for col, w in zip("ABCDEFGHIJKLMNOPQRST", (11, 24, 34, 9, 13, 13, 11, 11, 11, 10, 9, 13, 11, 11, 11, 10, 11, 8, 70, 30)): sh.column_dimensions[col].width = w
sh.freeze_panes = "D2"
rd = lambda v: None if v is None else round(v, 2)
for x in items:
    note = "منتج أو عبوة مختلفة على الأغلب (أكثر من 3 أضعاف)" if x["far"] else ("وُجد في متجر واحد فقط" if x["shops"] == 1 else "")
    sh.append([x["code"], x["group"], x["desc"], x["unit"], rd(x["sep"]), rd(x["ours"]), rd(x["carrefour"]), rd(x["lulu"]), rd(x["diff"]), round(x["pct"], 1),
               x["shops"], rd(x["ours_reg"]), rd(x["carrefour_reg"]), rd(x["lulu_reg"]), rd(x["diff_reg"]), round(x["pct_reg"], 1),
               rd(x["oct_off"]), x["days"], x["title"], note])
    row = sh[sh.max_row]
    if x["far"]:
        for c in row: c.fill = amber
    else:
        row[9].fill = grn if abs(x["pct"]) <= 5 else (red if abs(x["pct"]) > 15 else PatternFill())
sh.auto_filter.ref = f"A1:T{sh.max_row}"
n = wb.create_sheet("ملاحظات"); n.sheet_view.rightToLeft = True
for t in ["المنتجات المطابقة فقط (باركود أو اسم): نفس المنتج الذي يسعّره المكتب الرسمي، من لولو وكارفور.",
          "الرسمي: متوسط سبتمبر 2026 من 4 إلى 5 محلات. سعرنا: متوسط الأيام من 12 إلى 29 أكتوبر 2026، لكل متجر، ثم متوسط المتجرين.",
          "السعر مقارَن بوحدة البند الرسمية (مثلاً 1 كغ أو 400 غ أو حبة) بتحويل سعر الوحدة؛ منتج وحدته من عائلة مختلفة لم يُقارن.",
          "فرق السعر (درهم) = سعرنا − الرسمي. أخضر: ضمن ±5%، أحمر: أكثر من ±15%، أصفر: الفرق أكثر من 3 أضعاف فالمطابقة غالباً خطأ.",
          "سعرنا = متوسط المتاجر التي وُجد فيها المنتج. إذا لم يجده البحث في أحد المتجرين (not found) يُحسب من المتجر الآخر وحده، ويُكتب ذلك في عمود الملاحظة وعمود عدد المتاجر.",
          "السعر العادي = السعر قبل العرض كما يعرضه الموقع (السعر المشطوب). ملاحظة: لولو لا يُسجَّل له أي عرض بسبب خطأ في المحلل (قيد الإصلاح)، فسعره هنا هو السعر العادي أصلاً.",
          "ملف داخلي: يحتوي أسعاراً رسمية، لا يُنشر."]: n.append([t])
# chart sheet: the 25 largest differences each way (comparable products), labelled by our listing title
cd = wb.create_sheet("بيانات الرسم"); cd.append(["product", "difference AED"])
big = sorted(ok, key=lambda x: x["diff"])
pick = big[:25] + big[-25:]
for x in pick: cd.append([x["desc"][:28], round(x["diff"], 2)])
ch = BarChart(); ch.type = "bar"; ch.height = 26; ch.width = 24; ch.title = "فرق السعر بالدرهم: سعرنا أكتوبر − الرسمي سبتمبر (أكبر 50 فرقاً)"
ch.add_data(Reference(cd, min_col=2, min_row=1, max_row=cd.max_row), titles_from_data=True); ch.set_categories(Reference(cd, min_col=1, min_row=2, max_row=cd.max_row))
ch.legend = None; ch.y_axis.title = "AED"
cs = wb.create_sheet("الرسم", 0); cs.add_chart(ch, "B2")
wb.save(sys.argv[1]); print("saved", sys.argv[1])
