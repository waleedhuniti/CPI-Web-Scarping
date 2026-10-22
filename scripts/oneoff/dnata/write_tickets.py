import json, openpyxl, openpyxl.utils
from openpyxl.styles import Font, Alignment, PatternFill
R = json.load(open("tickets_res.json"))
CITY = {"Delhi": ["DEL"], "London": ["LHR", "LGW"], "Riyadh": ["RUH"], "Karachi": ["KHI"], "New York": ["JFK", "EWR"], "Tehran": ["IKA"],
        "Bangkok": ["BKK"], "Istanbul": ["IST", "SAW"], "Cairo": ["CAI"], "Alexandria": ["HBE"], "Amman": ["AMM"]}
def rng(city, leg, airline):
    lo = hi = None; fl = []
    for ap in CITY[city]:
        e = (R.get(f"{ap}_{leg}", {}).get("airlines") or {}).get(airline)
        if not e: continue
        lo = e["min"] if lo is None else min(lo, e["min"]); hi = e["max"] if hi is None else max(hi, e["max"])
        fl.append(f"{ap}: {e['min_flight']} ({round(e['min'])}) … {e['max_flight']} ({round(e['max'])}), {e['n']} أسعار")
    return (round(lo) if lo else None), (round(hi) if hi else None), "; ".join(fl)
wb = openpyxl.load_workbook("up3/tickets.xlsx")
dom_src, for_src = wb["الطيران المحلى"], wb["الطيران الاجنبى"]
yellow = PatternFill("solid", fgColor="FFF2CC")
# domestic: flydubai C/D, Emirates F/G on the out and back rows of week 1 (the return row and ticket price keep the sheet's own formulas)
dom = wb.copy_worksheet(dom_src); dom.title = "محلي 1-6 نوفمبر"; dom.sheet_view.rightToLeft = dom_src.sheet_view.rightToLeft
DROW = {"Delhi": 4, "London": 7, "Riyadh": 10, "Karachi": 13, "New York": 16, "Tehran": 19, "Bangkok": 22, "Istanbul": 25, "Cairo": 28, "Alexandria": 31, "Amman": 34}
for city, r0 in DROW.items():
    for i, leg in enumerate(("out", "back")):
        for (clo, chi), al in (((3, 4), "Flydubai"), ((6, 7), "Emirates")):
            lo, hi, _ = rng(city, leg, al)
            dom.cell(r0 + i, clo).value = lo
            dom.cell(r0 + i, chi).value = hi if (hi and hi != lo) else None
    for clo, chi, cav in ((3, 4, 5), (6, 7, 8)):          # same formula on every return row: out + back, ticket = average of lowest and highest
        L, H, A = (openpyxl.utils.get_column_letter(c) for c in (clo, chi, cav))
        if dom.cell(r0, clo).value and dom.cell(r0 + 1, clo).value:
            dom.cell(r0 + 2, clo).value = f"=SUM({L}{r0}:{L}{r0+1})"; dom.cell(r0 + 2, chi).value = f'=IF(AND({H}{r0}="",{H}{r0+1}=""),"",IF({H}{r0}="",{L}{r0},{H}{r0})+IF({H}{r0+1}="",{L}{r0+1},{H}{r0+1}))'; dom.cell(r0 + 2, cav).value = f"=AVERAGE({L}{r0+2}:{H}{r0+2})"
        else:
            for c in (clo, chi, cav): dom.cell(r0 + 2, c).value = None
dom.cell(1, 3).value = "الأسبوع الأول: الذهاب 1 نوفمبر، العودة 6 نوفمبر 2026"
for r in range(4, 37):                                   # other weeks: leave empty
    for c in range(10, dom.max_column + 1):
        if not (isinstance(dom.cell(r, c).value, str) and dom.cell(r, c).value.startswith("=")): dom.cell(r, c).value = None
# foreign: the country's national carrier, week 1 columns C/D
NAT = {"Delhi": (3, "Air India"), "London": (6, "British Airways"), "Riyadh": (9, "Saudia"), "Karachi": (12, "Pakistan International Airlines"),
       "Istanbul": (15, "Turkish Airlines"), "Cairo": (18, "Egyptair"), "Amman": (21, "Royal Jordanian Airlines")}
fo = wb.copy_worksheet(for_src); fo.title = "أجنبي 1-6 نوفمبر"; fo.sheet_view.rightToLeft = for_src.sheet_view.rightToLeft
for city, (r0, al) in NAT.items():
    for i, leg in enumerate(("out", "back")):
        lo, hi, _ = rng(city, leg, al)
        fo.cell(r0 + i, 3).value = lo; fo.cell(r0 + i, 4).value = hi if (hi and hi != lo) else None
    if fo.cell(r0, 3).value and fo.cell(r0 + 1, 3).value:
        fo.cell(r0 + 2, 3).value = f"=SUM(C{r0}:C{r0+1})"; fo.cell(r0 + 2, 4).value = f'=IF(AND(D{r0}="",D{r0+1}=""),"",IF(D{r0}="",C{r0},D{r0})+IF(D{r0+1}="",C{r0+1},D{r0+1}))'; fo.cell(r0 + 2, 5).value = f"=AVERAGE(C{r0+2}:D{r0+2})"
    else:
        for c in (3, 4, 5): fo.cell(r0 + 2, c).value = None
fo.cell(1, 2).value = "الأسبوع الأول: الذهاب 1 نوفمبر، العودة 6 نوفمبر 2026"
# details
d = wb.create_sheet("تفاصيل التذاكر 1-6 نوفمبر"); d.sheet_view.rightToLeft = True
d.append(["الوجهة", "الشركة", "ذهاب 1 نوفمبر: أقل", "ذهاب: أعلى", "عودة 6 نوفمبر: أقل", "عودة: أعلى", "ذهاب + عودة (مجموع، طريقة الملف): أقل", "مجموع: أعلى",
          "تذكرة ذهاب وعودة واحدة (للمقارنة): أقل", "تذكرة ذهاب وعودة: أعلى", "الرحلات (أقل / أعلى)"])
for c in d[1]: c.font = Font(bold=True); c.alignment = Alignment(wrap_text=True)
for city in CITY:
    als = sorted({a for ap in CITY[city] for leg in ("out", "back", "return") for a in (R.get(f"{ap}_{leg}", {}).get("airlines") or {})})
    if not als:
        d.append([city, "لا توجد رحلات مباشرة على دناتا لهذه التواريخ"]); continue
    for al in als:
        o = rng(city, "out", al); bk = rng(city, "back", al); rt = rng(city, "return", al)
        s_lo = o[0] + bk[0] if o[0] and bk[0] else None; s_hi = (o[1] or o[0]) + (bk[1] or bk[0]) if o[0] and bk[0] else None
        d.append([city, al, o[0], o[1], bk[0], bk[1], s_lo, s_hi, rt[0], rt[1], " | ".join(x for x in (o[2], bk[2]) if x)])
for col, w in zip("ABCDEFGHIJK", (12, 26, 12, 12, 12, 12, 16, 12, 16, 12, 90)): d.column_dimensions[col].width = w
n = wb.create_sheet("منهجية التذاكر"); n.sheet_view.rightToLeft = True
for line in ["المصدر: dnatatravel.com (طيران فقط)، تاريخ السحب 22 أكتوبر 2026، الأسعار بالدرهم شاملة الضرائب، شخص بالغ واحد، الدرجة السياحية.",
             "الذهاب يوم 1 نوفمبر 2026 من دبي (DXB)، والعودة يوم 6 نوفمبر 2026 إلى دبي. رحلات مباشرة فقط (بدون توقف)، على نفس الشركة.",
             "أقل/أعلى سعر = أرخص وأغلى سعر معروض لنفس الشركة في ذلك اليوم (أوقات وفئات أسعار مختلفة).",
             "صف (الذهاب والعودة) وسعر التذكرة محسوبان بمعادلات الملف نفسها: مجموع الذهاب + العودة، ثم متوسط الأقل والأعلى.",
             "لندن = هيثرو (LHR) وجاتويك (LGW)؛ نيويورك = JFK؛ إسطنبول = المطار الجديد (IST) وصبيحة (SAW).",
             "لا توجد نتائج على دناتا: طهران، الإسكندرية، الطيران السعودي (الرياض)، الطيران الباكستاني (كراتشي)؛ البريطانية تظهر للعودة فقط.",
             "وحّدنا المعادلات في كل الصفوف (بعض صفوف الملف الأصلي كانت لا تجمع الأعلى، وسعر لندن كان =F8 أي العودة فقط). عند تساوي الأقل والأعلى يُترك الأعلى فارغاً، والمعادلة تأخذ الأقل مكانه. إذا غاب الذهاب أو العودة يُترك صف الذهاب والعودة فارغاً.",
             "ورقة التفاصيل فيها أيضاً سعر تذكرة الذهاب والعودة الواحدة للمقارنة (غالباً أرخص من مجموع تذكرتين منفصلتين)."]:
    n.append([line])
n.column_dimensions["A"].width = 120
out = "/home/user/CPI-Web-Scarping/data/exports/dnata_air_tickets_1-6_Nov_2026.xlsx"
wb.save(out); print(out)
