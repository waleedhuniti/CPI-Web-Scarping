import json, openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
R = json.load(open("fz_res.json"))
wb = openpyxl.load_workbook("up4/manual_tickets.xlsx")
src = wb["الطيران المحلى"]
yellow = PatternFill("solid", fgColor="FFF2CC")
CITY = {"Delhi": ["DEL"], "Riyadh": ["RUH"], "Karachi": ["KHI"], "Colombo": ["CMB"], "Istanbul": ["IST"], "Alexandria": ["HBE"], "Amman": ["AMM"]}
NOTE = {"Delhi": "العودة 6 نوفمبر: لا توجد رحلة لفلاي دبي؛ السعر من الأيام المجاورة (4 و5 و7 نوفمبر: 933)",
        "Alexandria": "لا توجد رحلات فلاي دبي إلى الإسكندرية (HBE) في هذه الفترة",
        "Istanbul": "المطار الجديد (IST)؛ صبيحة (SAW): ذهاب 971، عودة 884"}
ws = wb.copy_worksheet(src); ws.title = "محلي 1-6 نوفمبر (فلاي دبي)"; ws.sheet_view.rightToLeft = src.sheet_view.rightToLeft
ws.cell(1, 3).value = "الأسبوع الأول: ذهاب 1 نوفمبر، عودة 6 نوفمبر 2026 (بحث ذهاب وعودة)"
rows = {}
for r in range(4, ws.max_row + 1):
    a = str(ws.cell(r, 1).value or "")
    for city in CITY:
        if city.lower() in a.lower() or (city == "Colombo" and "colombo" in a.lower()): rows[city] = r
for r in range(4, 40):                                    # clear week-1 numbers of the copy (keep labels)
    for c in range(3, 9):
        v = ws.cell(r, c).value
        if v is not None and not (isinstance(v, str) and not v.startswith("=") and not v[:1].isdigit()): ws.cell(r, c).value = None
    for c in range(10, ws.max_column + 1):
        if not isinstance(ws.cell(r, c).value, str) or ws.cell(r, c).value.startswith("="): ws.cell(r, c).value = None
for city, r0 in rows.items():
    v = R.get(CITY[city][0], {})
    out, back = v.get("out"), v.get("back")
    if city == "Delhi" and back is None: back = 933.0
    ws.cell(r0, 3).value = out; ws.cell(r0 + 1, 3).value = back
    if out and back:
        ws.cell(r0 + 2, 3).value = f"=SUM(C{r0}:C{r0+1})"; ws.cell(r0 + 2, 5).value = f"=AVERAGE(C{r0+2}:D{r0+2})"
    if city in NOTE:
        ws.cell(r0, 10).value = NOTE[city]; ws.cell(r0, 10).fill = yellow
# comparison with the manual figures
cmp_ = wb.create_sheet("مقارنة مع السحب اليدوي"); cmp_.sheet_view.rightToLeft = True
cmp_.append(["الوجهة", "الاتجاه", "يدوي (الشباب)", "آلي (موقع فلاي دبي)", "الفرق", "ملاحظة"])
for c in cmp_[1]: c.font = Font(bold=True)
for city, r0 in rows.items():
    for i, leg in enumerate(("ذهاب 1 نوفمبر", "عودة 6 نوفمبر")):
        man = src.cell(r0 + i, 3).value; auto = ws.cell(r0 + i, 3).value
        diff = round(auto - man) if isinstance(man, (int, float)) and isinstance(auto, (int, float)) else None
        cmp_.append([city, leg, man, auto, diff, NOTE.get(city, "") if i == 0 else ""])
for col, w in zip("ABCDEF", (14, 16, 16, 18, 10, 70)): cmp_.column_dimensions[col].width = w
n = wb.create_sheet("منهجية"); n.sheet_view.rightToLeft = True
for line in ["المصدر: موقع فلاي دبي (flydubai.com)، تاريخ السحب 22 أكتوبر 2026، شخص بالغ واحد، الدرجة السياحية.",
             "بحث ذهاب وعودة: ذهاب 1 نوفمبر 2026، عودة 6 نوفمبر 2026. السعر المسجل لكل اتجاه = أرخص سعر يعرضه الموقع لذلك اليوم (شريط التواريخ)، بنفس طريقة السحب اليدوي.",
             "أعلى سعر: غير متوفر آلياً؛ قائمة الرحلات في موقع فلاي دبي تعرض رسالة خطأ للمتصفح الآلي، فسُجّل الأقل فقط.",
             "الإماراتية: موقع الحجز يرفض المتصفح الآلي (403 Access restricted)، فلم تُسحب أسعارها.",
             "الأسعار تتغير خلال اليوم؛ فروقات صغيرة عن السحب اليدوي (مثلاً إسطنبول) سببها وقت السحب."]:
    n.append([line])
n.column_dimensions["A"].width = 130
out = "/home/user/CPI-Web-Scarping/data/exports/flydubai_tickets_1-6_Nov_2026.xlsx"
wb.save(out); print(out)
for row in cmp_.iter_rows(min_row=2, values_only=True): print(row[:5])
