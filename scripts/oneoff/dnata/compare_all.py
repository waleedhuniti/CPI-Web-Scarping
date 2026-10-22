"""Full comparison of the automated fare pull (airline sites, 1 Nov out / 6 Nov back) against the manual team's sheet.
usage: python3 compare_all.py manual_tickets.xlsx out.xlsx"""
import json, sys, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
SRC, OUT = sys.argv[1:3]
man = openpyxl.load_workbook(SRC, data_only=False)
dom, fo = man["الطيران المحلى"], man["الطيران الاجنبى"]
def rows_of(ws, start):
    out = {}
    for r in range(start, 40):
        a = str(ws.cell(r, 1).value or "").strip()
        if a and ws.cell(r, 2).value in ("الذهاب",): out[a.lower()] = r
    return out
D, F = rows_of(dom, 4), rows_of(fo, 3)
def find(rows, key): return next(r for a, r in rows.items() if key in a)
def num(v): return float(v) if isinstance(v, (int, float)) else None
def load(f, k):
    try: return json.load(open(f)).get(k)
    except FileNotFoundError: return None
FZ = json.load(open("fz_full_res.json"))
LINES = [  # airline, city, sheet, row key, low col, high col, auto result, block reason
    ("فلاي دبي", "دلهي", dom, D, "delhi", 3, 4, FZ.get("DEL"), None),
    ("فلاي دبي", "الرياض", dom, D, "riyadh", 3, 4, FZ.get("RUH"), None),
    ("فلاي دبي", "كراتشي", dom, D, "karachi", 3, 4, FZ.get("KHI"), None),
    ("فلاي دبي", "كولومبو", dom, D, "colombo", 3, 4, FZ.get("CMB"), None),
    ("فلاي دبي", "إسطنبول", dom, D, "istanbul", 3, 4, FZ.get("IST"), None),
    ("فلاي دبي", "الإسكندرية", dom, D, "alexandria", 3, 4, FZ.get("ALY"), None),
    ("فلاي دبي", "عمّان", dom, D, "amman", 3, 4, FZ.get("AMM"), None),
    ("الخطوط السعودية", "الرياض", fo, F, "riyadh", 3, 4, load("air_saudia_res.json", "RUH"), None),
    ("مصر للطيران", "القاهرة", fo, F, "cairo", 3, 4, load("air_egyptair_res.json", "CAI"), None),
    ("الملكية الأردنية", "عمّان", fo, F, "amman", 3, 4, load("air_rj_res.json", "AMM"), None),
    ("الباكستانية", "إسلام آباد", fo, F, "isb", 3, 4, load("air_pia_res.json", "ISB"), None),
    ("طيران الهند", "دلهي", fo, F, "delhi", 3, 4, None, "موقع طيران الهند يحجب السيرفر (Akamai Access Denied) بعد أول زيارة"),
    ("التركية", "إسطنبول", fo, F, "istanbul", 3, 4, None, "موقع التركية يطلب تحقق بشري (Press & Hold) قبل البحث"),
    ("البريطانية", "لندن", fo, F, "london", 3, 4, None, "فارغ عند الشباب أيضاً"),
] + [("الإماراتية", c, dom, D, k, 6, 7, None, "موقع الإماراتية يحجب المتصفح الآلي (Access restricted) قبل أي بحث")
     for c, k in (("دلهي", "delhi"), ("لندن", "london"), ("الرياض", "riyadh"), ("كراتشي", "karachi"), ("نيويورك", "new york"),
                  ("كولومبو", "colombo"), ("بانكوك", "bangkok"), ("إسطنبول", "istanbul"), ("القاهرة", "cairo"), ("عمّان", "amman"))]
NOTE = {
    ("فلاي دبي", "دلهي", "out"): "رحلة واحدة؛ السعر ارتفع خلال اليوم (1684 صباحاً ثم 2035)",
    ("فلاي دبي", "دلهي", "back"): "لا رحلة يوم 6؛ أُخذ يوم 7 نوفمبر",
    ("الخطوط السعودية", "الرياض", "out"): "الشباب تركوا الأعلى فارغاً؛ رحلة SV563 بسعر 580",
    ("الملكية الأردنية", "عمّان", "out"): "أقل سعر كان 585 بأول سحب ثم نفد وصار 735؛ أعلى سعر 1105 عند الشباب = سعر Flex لرحلة RJ613، والأعلى الحالي RJ611 بـ 1335",
    ("الباكستانية", "إسلام آباد", "out"): "آخر 3 مقاعد بالسعر الأرخص؛ السعر تحرك",
    ("الباكستانية", "إسلام آباد", "back"): "750 = سعر العودة داخل بحث ذهاب وعودة؛ نفس الرحلة كبحث ذهاب فقط 975، والظاهر الشباب بحثوها ذهاب فقط",
}
LEG = {"out": "ذهاب 1/11", "back": "عودة 6/11"}
green, red, grey = (PatternFill("solid", fgColor=c) for c in ("E2EFDA", "FCE4D6", "EDEDED"))
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "مقارنة كاملة"; ws.sheet_view.rightToLeft = True
ws.append(["شركة الطيران", "الوجهة", "الاتجاه", "يدوي أقل", "آلي أقل", "فرق الأقل", "يدوي أعلى", "آلي أعلى", "فرق الأعلى", "النتيجة", "السبب / ملاحظة"])
tk = wb.create_sheet("سعر التذكرة"); tk.sheet_view.rightToLeft = True
tk.append(["شركة الطيران", "الوجهة", "سعر التذكرة يدوي", "سعر التذكرة آلي", "الفرق", "ملاحظة"])
det = wb.create_sheet("تفاصيل الرحلات"); det.sheet_view.rightToLeft = True
det.append(["شركة الطيران", "الوجهة", "الاتجاه", "التاريخ", "الرحلة", "وقت الإقلاع", "أرخص سعر سياحي (درهم)"])
summary = {"مطابق": 0, "فرق": 0, "لم يُسحب": 0}
def ticket(lo, hi):
    if None in lo: return None
    return round((sum(lo) + sum(h if h is not None else l for l, h in zip(lo, hi))) / 2, 1)
for air, city, sheet, rows, key, cl, ch, res, block in LINES:
    r0 = find(rows, key)
    mlo, mhi, alo, ahi = [], [], [], []
    for i, k in enumerate(("out", "back")):
        ml, mh = num(sheet.cell(r0 + i, cl).value), num(sheet.cell(r0 + i, ch).value)
        x = (res or {}).get(k) if isinstance(res, dict) else None
        al, ah = (x["lowest"], x["highest"]) if x else (None, None)
        if ah is not None and ah == al: ah = None                 # same as lowest -> blank (our rule)
        mh_eff = mh if mh is not None and mh != ml else None
        mlo.append(ml); mhi.append(mh_eff); alo.append(al); ahi.append(ah)
        if al is None:
            status, fill = "لم يُسحب", grey
        else:
            same = ml == al and (mh_eff or ml) == (ah or al)
            status, fill = ("مطابق", green) if same else ("فرق", red)
        summary[status] += 1
        dl = round(al - ml) if al is not None and ml is not None else None
        dh = round((ah or al) - (mh_eff or ml)) if al is not None and ml is not None and (ah or mh_eff) else None
        note = NOTE.get((air, city, k)) or (block if i == 0 else "")
        ws.append([air, city, LEG[k], ml, al, dl, mh, ah, dh, status, note])
        ws.cell(ws.max_row, 10).fill = fill
        for f in (x or {}).get("flights", []):
            det.append([air, city, LEG[k], x["date"], f.get("flight"), str(f.get("dep", ""))[-8:-3] if "T" in str(f.get("dep", "")) else f.get("dep"), f.get("from")])
    m, a = ticket(mlo, mhi), ticket(alo, ahi)
    tk.append([air, city, m, a, round(a - m, 1) if m is not None and a is not None else None, block or ""])
for s, widths in ((ws, (16, 12, 11, 10, 10, 9, 10, 10, 9, 10, 90)), (tk, (16, 12, 16, 16, 10, 80)), (det, (16, 12, 11, 12, 10, 10, 18))):
    for c in s[1]: c.font = Font(bold=True)
    for i, w in enumerate(widths): s.column_dimensions[chr(65 + i)].width = w
n = wb.create_sheet("منهجية"); n.sheet_view.rightToLeft = True
for line in ["تاريخ السحب 22 أكتوبر 2026. بحث ذهاب وعودة من دبي: ذهاب 1 نوفمبر، عودة 6 نوفمبر 2026، بالغ واحد، الدرجة السياحية، رحلات مباشرة لنفس الشركة فقط.",
             "المصدر: موقع كل شركة طيران مباشرة (flydubai.com، saudia.com، egyptair.com، rj.com، book-pia.crane.aero).",
             "لكل رحلة يؤخذ أرخص سعر سياحي لها. أقل سعر = أرخص رحلة في اليوم، أعلى سعر = أغلى رحلة. إذا تساويا يُترك الأعلى فارغاً.",
             "سعر التذكرة = متوسط (مجموع أقل سعر للاتجاهين، مجموع أعلى سعر للاتجاهين)، وإذا كان الأعلى فارغاً يؤخذ الأقل لذلك الاتجاه.",
             "إذا لم توجد رحلة يوم العودة يؤخذ اليوم الذي بعده.",
             "الأسعار تتغير خلال اليوم (خاصة عند آخر المقاعد)، فأي فرق صغير قد يكون من وقت السحب.",
             f"الخلاصة: مطابق {summary['مطابق']}، فرق {summary['فرق']}، لم يُسحب {summary['لم يُسحب']} (من أصل {sum(summary.values())} اتجاه)."]:
    n.append([line])
n.column_dimensions["A"].width = 140
wb.save(OUT); print(OUT, summary)
for r in ws.iter_rows(min_row=2, values_only=True):
    if r[9] != "لم يُسحب": print(r[:10])
for r in tk.iter_rows(min_row=2, values_only=True): print(r[:5])
