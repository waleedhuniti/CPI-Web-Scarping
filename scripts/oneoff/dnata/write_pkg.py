import json, openpyxl, sys
from openpyxl.styles import Font, Alignment, PatternFill
res = json.load(open(sys.argv[1])); out = sys.argv[2]
wb = openpyxl.load_workbook("up/pkg.xlsx")
src = wb.worksheets[0]
oc = wb.copy_worksheet(src); oc.title = "أكتوبر 2026"; oc.sheet_view.rightToLeft = src.sheet_view.rightToLeft
for r in range(3, oc.max_row + 1):                       # clear the September prices, keep names and layout
    for c in range(3, 11):
        if not isinstance(oc.cell(r, c).value, str) or any(ch.isdigit() for ch in str(oc.cell(r, c).value)):
            oc.cell(r, c).value = None
    oc.cell(r, 11).value = None
oc.cell(1, 9).value = "الأسبوع الرابع (25-29 أكتوبر)"
yellow = PatternFill("solid", fgColor="FFF2CC")
for k, v in res.items():
    r = int(k)
    if v.get("total"):
        oc.cell(r, 9).value = v["total"]
    note = []
    if v.get("hotel_found") and v.get("hotel_found").lower().split()[0] not in (v.get("sheet_name") or "").lower():
        note.append("فندق مختلف: " + v["hotel_found"])
    elif v.get("hotel_found") and v["hotel_found"] != v.get("sheet_name"):
        note.append("على دناتا: " + v["hotel_found"])
    if v.get("board") and "reakfast" not in v["board"]: note.append("بدون فطور: " + v["board"])
    if v.get("note"): note.append(v["note"])
    if note:
        oc.cell(r, 11).value = " | ".join(note); oc.cell(r, 11).fill = yellow
d = wb.create_sheet("تفاصيل دناتا 25-29 أكتوبر")
d.sheet_view.rightToLeft = True
hdr = ["الصف", "المدينة", "الفندق بالملف", "الفندق على دناتا", "النجوم", "نوع الوجبة", "قاعدة الوجبة",
       "سعر الباقة بالطيران الافتراضي", "الطيران الافتراضي", "رحلة الإماراتية بدون توقف (ذهاب / عودة)", "فرق سعر الإماراتية",
       "السعر النهائي (درهم)", "ملاحظات"]
d.append(hdr)
for c in d[1]: c.font = Font(bold=True); c.alignment = Alignment(wrap_text=True)
for k in sorted(res, key=int):
    v = res[k]
    d.append([v["row"], v.get("destination") or v["city"], v.get("sheet_name"), v.get("hotel_found"), v.get("stars"), v.get("board"), v.get("board_rule"),
              v.get("package_default"), v.get("default_flight"), v.get("flight"), v.get("flight_delta"), v.get("total"), v.get("note")])
for col, w in zip("ABCDEFGHIJKLM", (6, 22, 34, 34, 7, 20, 18, 14, 34, 30, 12, 14, 40)):
    d.column_dimensions[col].width = w
n = wb.create_sheet("المنهجية")
n.sheet_view.rightToLeft = True
for line in ["المصدر: dnatatravel.com (طيران + فندق)، تاريخ السحب 20 أكتوبر 2026.",
             "الإقامة: 25 إلى 29 أكتوبر 2026 (4 ليالي)، شخص بالغ واحد، المغادرة من دبي (DXB).",
             "الطيران: طيران الإمارات فقط، بدون توقف ذهاباً وعودة، الأرخص المتاح.",
             "الوجبة: إقامة مع إفطار (Bed & Breakfast) إذا كانت متاحة للفندق، وإلا الأرخص.",
             "السعر النهائي = سعر الباقة بالطيران الافتراضي + فرق سعر رحلة الإماراتية (كما يعرضه الموقع)، شامل الضرائب والرسوم.",
             "عمود الإماراتية للعطلات (Emirates Holidays) لم يُسحب.",
             "الخلايا الصفراء فيها ملاحظة: فندق مختلف عن الملف، أو بدون إفطار، أو غير متوفر."]:
    n.append([line])
n.column_dimensions["A"].width = 110
wb.save(out); print(out)
