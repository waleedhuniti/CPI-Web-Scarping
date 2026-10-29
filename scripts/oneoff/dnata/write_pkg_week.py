"""Monthly package sheet for one stay, from dnata_packages.py + shots.py (+ shots_next.py for the Maldives transfer).
usage: python3 write_pkg_week.py <package sheet template.xlsx> <out.xlsx> <check-in YYYY-MM-DD> <check-out YYYY-MM-DD>
                                 pkg.json:shots.json [pkg2.json:shots2.json ...] [--next maldives_next.json]
A row's final price is the page's "Total holiday" (shots.py); for the Maldives it is the total after the mandatory resort transfer
(shots_next.py, the last "Total AED" on the extras page)."""
import datetime as dt, json, sys, openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.drawing.image import Image as XLImage
from PIL import Image as PImage
TPL, OUT, CI, CO = sys.argv[1:5]
pairs, nxt = [], {}
args = sys.argv[5:]
while args:
    a = args.pop(0)
    if a == "--next": nxt = json.load(open(args.pop(0)))
    else: pairs.append(a.split(":"))
day = lambda s: dt.date.fromisoformat(s).day
nights = (dt.date.fromisoformat(CO) - dt.date.fromisoformat(CI)).days
res = {}
for pj, sj in pairs:
    p, s = json.load(open(pj)), json.load(open(sj))
    for k, v in p.items():
        sh = s.get(k, {})
        if v.get("note") == "hotel not found on dnata for these dates": v = dict(v, note="الفندق غير معروض للحجز على دناتا لهذه التواريخ")
        v = dict(v, shown_total=sh.get("shown_total"), screenshot=sh.get("screenshot"), nights_shown=sh.get("nights_shown"), page_error=sh.get("error"))
        co = (sh.get("page_url") or v.get("page_url") or "")
        v["checkout"] = co.split("checkOut=")[1][:10] if "checkOut=" in co else CO
        if v.get("shown_total"): v["final"] = v["shown_total"]
        elif v.get("total"): v["final"] = v["total"]; v["note"] = ((v.get("note") or "") + " | السعر محسوب (الصفحة لم تُحمّل للقطة)").strip(" |")
        n = nxt.get(k) or {}
        tots = [float(x.replace(",", "")) for x in n.get("next_page_totals", []) if x]
        if tots and v.get("final") and max(tots) > v["final"]:
            v["transfer"] = round(max(tots) - v["final"], 2); v["final"] = max(tots)
            v["screenshot"] = n.get("screenshot") or v.get("screenshot")
            v["note"] = ((v.get("note") or "") + f" | شامل نقل المنتجع الإلزامي ({v['transfer']:,.0f} درهم)").strip(" |")
        if v["checkout"] != CO:
            v["note"] = ((v.get("note") or "") + f" | الإقامة {day(CI)}-{day(v['checkout'])} نوفمبر: رحلة الإماراتية تصل في اليوم التالي، فمُدّد السفر يوماً لتبقى {nights} ليالي كاملة").strip(" |")
        res[k] = v
wb = openpyxl.load_workbook(TPL)
src = wb.worksheets[0]
oc = wb.copy_worksheet(src); oc.title = f"نوفمبر 2026 ({day(CI)}-{day(CO)})"; oc.sheet_view.rightToLeft = src.sheet_view.rightToLeft
for r in range(3, oc.max_row + 1):                       # clear the template's prices, keep names and layout
    for c in range(3, 11):
        if not isinstance(oc.cell(r, c).value, str) or any(ch.isdigit() for ch in str(oc.cell(r, c).value)):
            oc.cell(r, c).value = None
    oc.cell(r, 11).value = None
oc.cell(1, 3).value = f"{day(CI)}-{day(CO)} نوفمبر 2026 ({nights} ليالي)"
yellow = PatternFill("solid", fgColor="FFF2CC")
for k, v in res.items():
    r = int(k)
    if v.get("final"): oc.cell(r, 3).value = v["final"]
    note = []
    if v.get("hotel_found") and v["hotel_found"].lower().split()[0] not in (v.get("sheet_name") or "").lower():
        note.append("فندق مختلف: " + v["hotel_found"])
    elif v.get("hotel_found") and v["hotel_found"] != v.get("sheet_name"):
        note.append("على دناتا: " + v["hotel_found"])
    if v.get("board") and "reakfast" not in v["board"]: note.append("بدون فطور: " + v["board"])
    if v.get("note"): note.append(v["note"])
    if note: oc.cell(r, 11).value = " | ".join(note); oc.cell(r, 11).fill = yellow
wb.remove(src)
d = wb.create_sheet(f"تفاصيل دناتا {day(CI)}-{day(CO)} نوفمبر"); d.sheet_view.rightToLeft = True
d.append(["الصف", "المدينة", "الفندق بالملف", "الفندق على دناتا", "النجوم", "نوع الوجبة", "قاعدة الوجبة", "الدخول", "الخروج",
          "سعر الباقة بالطيران الافتراضي", "الطيران الافتراضي", "رحلة الإماراتية بدون توقف (ذهاب / عودة)", "فرق سعر الإماراتية",
          "نقل المنتجع", "السعر النهائي كما يظهر بالصفحة (درهم)", "ملاحظات", "سعر محسوب (للمراجعة)", "لقطة الشاشة"])
for c in d[1]: c.font = Font(bold=True); c.alignment = Alignment(wrap_text=True)
for k in sorted(res, key=int):
    v = res[k]
    d.append([v["row"], v.get("destination") or v["city"], v.get("sheet_name"), v.get("hotel_found"), v.get("stars"), v.get("board"), v.get("board_rule"), CI, v["checkout"],
              v.get("package_default"), v.get("default_flight"), v.get("flight"), v.get("flight_delta"), v.get("transfer"), v.get("final"), v.get("note"), v.get("calc_total") or v.get("total"),
              (v.get("screenshot") or "").split("/")[-1]])
for col, w in zip("ABCDEFGHIJKLMNOPQR", (6, 22, 30, 32, 7, 18, 18, 11, 11, 13, 30, 28, 11, 10, 15, 50, 13, 36)):
    d.column_dimensions[col].width = w
n = wb.create_sheet("المنهجية"); n.sheet_view.rightToLeft = True
for line in [f"المصدر: dnatatravel.com (طيران + فندق)، تاريخ السحب {dt.date.today().isoformat()}.",
             f"الإقامة: {day(CI)} إلى {day(CO)} نوفمبر 2026 ({nights} ليالي)، شخص بالغ واحد، المغادرة من دبي (DXB). إذا وصلت رحلة الإماراتية في اليوم التالي وقلّت الليالي يُمدّد السفر يوماً لتبقى الإقامة {nights} ليالي كاملة (بانكوك)؛ عدد الليالي في كل لقطة شاشة.",
             "الطيران: طيران الإمارات فقط، بدون توقف ذهاباً وعودة، الأرخص المتاح.",
             "الوجبة: إقامة مع إفطار (Bed & Breakfast) إذا كانت متاحة للفندق، وإلا الأرخص؛ وأرخص غرفة لهذه الوجبة.",
             "السعر النهائي = إجمالي الباقة كما يظهر بصفحة دناتا بعد اختيار رحلة الإماراتية المباشرة (Total holiday)، شامل الضرائب والرسوم. المالديف: شامل نقل المنتجع الإلزامي (يظهر بعد «Continue to book»).",
             "نفس الفنادق المستخدمة في ملف 1-5 نوفمبر (نفس رقم الفندق على دناتا). لكل فندق لقطة شاشة في ورقة اللقطات.",
             "عمود الإماراتية للعطلات (Emirates Holidays) لم يُسحب: موقعها يحجب المتصفح الآلي.",
             "الخلايا الصفراء فيها ملاحظة: فندق مختلف عن الملف، أو بدون إفطار، أو تمديد يوم، أو نقل المنتجع، أو غير متوفر."]:
    n.append([line])
n.column_dimensions["A"].width = 120
sh = wb.create_sheet("لقطات الشاشة")
row = 1
for k in sorted(res, key=int):
    v = res[k]
    if not v.get("screenshot"): continue
    sh.cell(row, 1).value = f"{v['row']} - {v.get('hotel_found')} - AED {v['final']:,.0f}"
    sh.cell(row, 1).font = Font(bold=True)
    im = PImage.open(v["screenshot"]); im = im.resize((im.width // 2, im.height // 2)); tmp = v["screenshot"].replace(".png", "_s.png"); im.save(tmp)
    sh.add_image(XLImage(tmp), f"A{row + 1}")
    row += 28
wb.save(OUT); print(OUT)
for k in sorted(res, key=int):
    v = res[k]; print(k, v.get("hotel_found"), v.get("final"), v.get("checkout"), (v.get("note") or "")[:80])
