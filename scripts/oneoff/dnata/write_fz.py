"""Fill the manual team's tickets sheet (domestic tab, flydubai columns) from fz_full_res.json.
usage: python3 write_fz.py manual_tickets.xlsx fz_full_res.json out.xlsx"""
import json, sys, openpyxl
from openpyxl.styles import Font, PatternFill
SRC, RESF, OUT = sys.argv[1:4]
R = json.load(open(RESF))
wb = openpyxl.load_workbook(SRC)
src = wb["الطيران المحلى"]
yellow = PatternFill("solid", fgColor="FFF2CC")
CITY = {"Delhi": "DEL", "Riyadh": "RUH", "Karachi": "KHI", "colombo": "CMB", "Istanbul": "IST", "Alexandria": "ALY", "Amman": "AMM"}
ws = wb.copy_worksheet(src); ws.title = "محلي 1-6 نوفمبر (فلاي دبي)"; ws.sheet_view.rightToLeft = src.sheet_view.rightToLeft
ws.cell(1, 3).value = "الأسبوع الأول: ذهاب 1 نوفمبر، عودة 6 نوفمبر 2026 (بحث ذهاب وعودة)"
rows = {}
for r in range(4, ws.max_row + 1):
    a = str(ws.cell(r, 1).value or "").lower()
    for city in CITY:
        if city.lower() in a: rows[city] = r
for r in range(4, ws.max_row + 1):                        # clear numbers of the copy, keep labels
    for c in range(3, ws.max_column + 1):
        v = ws.cell(r, c).value
        if isinstance(v, (int, float)) or (isinstance(v, str) and v.startswith("=")): ws.cell(r, c).value = None
LEG = {"out": "ذهاب", "back": "عودة"}
notes = {"Delhi": ["ذهاب: رحلة واحدة فقط، وسعرها ارتفع خلال اليوم (1684 صباحاً في شريط التواريخ، 2035 عند السحب الأخير)"]}
for city, r0 in rows.items():
    v = R.get(CITY[city], {})
    for i, k in enumerate(("out", "back")):
        x = v.get(k)
        if not x: continue
        ws.cell(r0 + i, 3).value = x["lowest"]
        ws.cell(r0 + i, 4).value = x["highest"] if x["highest"] != x["lowest"] else None
        if x["shifted_days"]:
            notes.setdefault(city, []).append(f"{LEG[k]}: لا توجد رحلة يوم {('1','6')[i]} نوفمبر، أُخذ سعر {x['date'][8:]} نوفمبر")
            ws.cell(r0 + i, 3).fill = yellow; ws.cell(r0 + i, 4).fill = yellow
    if v.get("out") and v.get("back"):
        ws.cell(r0 + 2, 3).value = f"=SUM(C{r0}:C{r0+1})"
        ws.cell(r0 + 2, 4).value = f'=IF(AND(D{r0}="",D{r0+1}=""),"",IF(D{r0}="",C{r0},D{r0})+IF(D{r0+1}="",C{r0+1},D{r0+1}))'
        ws.cell(r0 + 2, 5).value = f"=AVERAGE(C{r0+2}:D{r0+2})"
    else:
        notes.setdefault(city, []).append("لا توجد رحلات فلاي دبي على هذا الخط في هذه الفترة")
for city, ns in notes.items():
    c = ws.cell(rows[city], 10); c.value = "؛ ".join(ns); c.fill = yellow
# per-flight detail
det = wb.create_sheet("تفاصيل الرحلات"); det.sheet_view.rightToLeft = True
det.append(["الوجهة", "الاتجاه", "التاريخ", "الرحلة", "وقت الإقلاع", "أرخص سعر سياحي للرحلة (درهم)"])
for c in det[1]: c.font = Font(bold=True)
for city, r0 in rows.items():
    v = R.get(CITY[city], {})
    for k in ("out", "back"):
        for f in (v.get(k) or {}).get("flights", []):
            det.append([city, LEG[k], v[k]["date"], f["flight"], f["dep"][11:16], f["from"]])
for col, w in zip("ABCDEF", (14, 10, 12, 10, 12, 28)): det.column_dimensions[col].width = w
# comparison with the manual figures
cmp_ = wb.create_sheet("مقارنة مع السحب اليدوي"); cmp_.sheet_view.rightToLeft = True
cmp_.append(["الوجهة", "الاتجاه", "يدوي أقل", "آلي أقل", "يدوي أعلى", "آلي أعلى", "ملاحظة"])
for c in cmp_[1]: c.font = Font(bold=True)
for city, r0 in rows.items():
    for i, k in enumerate(("out", "back")):
        cmp_.append([city, LEG[k], src.cell(r0 + i, 3).value, ws.cell(r0 + i, 3).value,
                     src.cell(r0 + i, 4).value, ws.cell(r0 + i, 4).value, "؛ ".join(notes.get(city, [])) if i == 0 else ""])
for col, w in zip("ABCDEFG", (14, 10, 12, 12, 12, 12, 70)): cmp_.column_dimensions[col].width = w
n = wb.create_sheet("منهجية"); n.sheet_view.rightToLeft = True
for line in ["المصدر: موقع فلاي دبي (flydubai.com)، تاريخ السحب 22 أكتوبر 2026، شخص بالغ واحد، الدرجة السياحية، رحلات مباشرة فقط.",
             "بحث ذهاب وعودة: ذهاب 1 نوفمبر 2026، عودة 6 نوفمبر 2026.",
             "لكل رحلة يُؤخذ السعر الظاهر \"from AED\" (أرخص فئة سياحية للرحلة). أقل سعر = أرخص رحلة في اليوم، أعلى سعر = أغلى رحلة في اليوم.",
             "إذا تساوى السعران (أو توجد رحلة واحدة) يُترك عمود أعلى سعر فارغاً، ويحسب مجموع الذهاب والعودة لأعلى سعر من أقل سعر لذلك الاتجاه.",
             "إذا لم توجد رحلة في يوم العودة يُؤخذ اليوم الذي بعده (مظلل بالأصفر مع ملاحظة).",
             "الأسعار تتغير خلال اليوم؛ أي فرق عن السحب اليدوي سببه وقت السحب.",
             "الإماراتية: موقع الحجز يرفض المتصفح الآلي (403 Access restricted)، فلم تُسحب أسعارها."]:
    n.append([line])
n.column_dimensions["A"].width = 130
wb.save(OUT); print(OUT)
for row in cmp_.iter_rows(min_row=2, values_only=True): print(row)
