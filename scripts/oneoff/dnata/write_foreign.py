"""Fill the manual team's foreign-airlines sheet (week 1) from each airline's own site, next to the flydubai sheet.
usage: python3 write_foreign.py <workbook with the manual sheets> <out.xlsx>
Reads air_<airline>_res.json from this folder; airlines without a result keep their row empty with the reason."""
import json, os, sys, openpyxl
from openpyxl.styles import Font, PatternFill
SRC, OUT = sys.argv[1:3]
wb = openpyxl.load_workbook(SRC)
src = wb["الطيران الاجنبى"]
yellow = PatternFill("solid", fgColor="FFF2CC")
# row label in the sheet -> (airline, result file, airport key, note when there is no result)
LINES = {
    "delhi": ("طيران الهند", "air_airindia_res.json", "DEL", "موقع طيران الهند يحجب المتصفح الآلي (Akamai Access Denied) بعد أول زيارة"),
    "london": ("الخطوط البريطانية", "air_ba_res.json", "LHR", "قائمة رحلات البريطانية محجوبة للمتصفح الآلي؛ العودة تظهر فقط بعد اختيار رحلة الذهاب"),
    "riyadh": ("الخطوط السعودية", "air_saudia_res.json", "RUH", ""),
    "isb": ("الخطوط الباكستانية", "air_pia_res.json", "ISB", ""),
    "istanbul": ("الخطوط التركية", "air_turkish_res.json", "IST", "موقع الخطوط التركية يطلب تحقق بشري (Press & Hold) قبل البحث"),
    "cairo": ("مصر للطيران", "air_egyptair_res.json", "CAI", ""),
    "amman": ("الملكية الأردنية", "air_rj_res.json", "AMM", ""),
}
NOTE = {
    "london": "جزئي: أقل سعر للذهاب فقط، من شريط التواريخ في موقع البريطانية؛ أعلى سعر والعودة لم تظهر (قائمة الرحلات محجوبة)",
    "amman": "الذهاب: أرخص سعر كان 585 في أول سحب ثم نفد وصار 735؛ أعلى سعر 1105 عند الشباب = سعر Flex لرحلة RJ613، وأغلى رحلة الآن RJ611 بـ 1335",
    "isb": "العودة 750 = سعرها داخل بحث ذهاب وعودة؛ نفس الرحلة كبحث ذهاب فقط 975. الذهاب: آخر 3 مقاعد بالسعر الأرخص",
    "riyadh": "الشباب تركوا أعلى سعر للذهاب فارغاً؛ رحلة SV563 بسعر 580",
}
def load(f, k):
    try:
        v = json.load(open(f)).get(k)
        return v if isinstance(v, dict) and (v.get("out") or v.get("back")) else None
    except FileNotFoundError:
        return None
rows = {}
for r in range(3, 40):
    a = str(src.cell(r, 1).value or "").lower()
    for key in LINES:
        if key in a: rows[key] = r
ws = wb.copy_worksheet(src); ws.title = "أجنبي 1-6 نوفمبر"; ws.sheet_view.rightToLeft = src.sheet_view.rightToLeft
ws.cell(1, 2).value = "الأسبوع الأول: ذهاب 1 نوفمبر، عودة 6 نوفمبر 2026 (بحث ذهاب وعودة، موقع كل شركة)"
for r in range(3, 24):
    for c in range(3, ws.max_column + 1):
        v = ws.cell(r, c).value
        if isinstance(v, (int, float)) or (isinstance(v, str) and v.startswith("=")): ws.cell(r, c).value = None
cmp_ = wb.create_sheet("مقارنة الأجنبي مع اليدوي"); cmp_.sheet_view.rightToLeft = True
cmp_.append(["الشركة", "الوجهة", "الاتجاه", "يدوي أقل", "آلي أقل", "فرق الأقل", "يدوي أعلى", "آلي أعلى", "فرق الأعلى", "النتيجة", "ملاحظة"])
det = wb.create_sheet("رحلات الأجنبي"); det.sheet_view.rightToLeft = True
det.append(["الشركة", "الوجهة", "الاتجاه", "التاريخ", "الرحلة", "الإقلاع", "أرخص سعر سياحي (درهم)"])
green, red, grey = (PatternFill("solid", fgColor=c) for c in ("E2EFDA", "FCE4D6", "EDEDED"))
num = lambda v: float(v) if isinstance(v, (int, float)) else None
for key, r0 in rows.items():
    airline, f, ap, why = LINES[key]
    res = load(f, ap)
    for i, (leg, label) in enumerate((("out", "ذهاب 1/11"), ("back", "عودة 6/11"))):
        x = (res or {}).get(leg)
        lo, hi = (x["lowest"], x["highest"]) if x else (None, None)
        if hi is not None and hi == lo: hi = None
        ws.cell(r0 + i, 3).value = lo; ws.cell(r0 + i, 4).value = hi
        if x and x.get("shifted_days"): ws.cell(r0 + i, 3).fill = yellow
        ml, mh = num(src.cell(r0 + i, 3).value), num(src.cell(r0 + i, 4).value)
        mh_eff = mh if mh is not None and mh != ml else None
        if lo is None: status, fill = "لم يُسحب", grey
        elif ml is None: status, fill = "جديد (فارغ عند الشباب)", grey
        else:
            same = ml == lo and (mh_eff or ml) == (hi or lo)
            status, fill = ("مطابق", green) if same else ("فرق", red)
        cmp_.append([airline, src.cell(r0, 1).value, label, ml, lo, round(lo - ml) if lo is not None and ml is not None else None, mh, hi,
                     round((hi or lo) - (mh_eff or ml)) if lo is not None and ml is not None and (hi or mh_eff) else None, status,
                     (NOTE.get(key, "") or why) if i == 0 else ("" if res else why)])
        cmp_.cell(cmp_.max_row, 10).fill = fill
        for fl in (x or {}).get("flights", []):
            dep = str(fl.get("dep", "")); dep = dep[11:16] if "T" in dep else dep
            det.append([airline, src.cell(r0, 1).value, label, x.get("date"), fl.get("flight"), dep, fl.get("from")])
    if res and res.get("out") and res.get("back"):
        ws.cell(r0 + 2, 3).value = f"=SUM(C{r0}:C{r0+1})"
        ws.cell(r0 + 2, 4).value = f'=IF(AND(D{r0}="",D{r0+1}=""),"",IF(D{r0}="",C{r0},D{r0})+IF(D{r0+1}="",C{r0+1},D{r0+1}))'
        ws.cell(r0 + 2, 5).value = f"=AVERAGE(C{r0+2}:D{r0+2})"
    c = ws.cell(r0, 6); c.value = airline + (" · " + (NOTE.get(key) or "") if res and NOTE.get(key) else "" if res else " · " + why); c.fill = yellow if (not res or NOTE.get(key)) else PatternFill()
for s, w in ((cmp_, (16, 18, 11, 10, 10, 9, 10, 10, 9, 18, 90)), (det, (16, 18, 11, 12, 10, 9, 18))):
    for c in s[1]: c.font = Font(bold=True)
    for i, x in enumerate(w): s.column_dimensions[chr(65 + i)].width = x
m = wb["منهجية"] if "منهجية" in wb.sheetnames else wb.create_sheet("منهجية")
for line in ["الطيران الأجنبي: من موقع كل شركة مباشرة (saudia.com، egyptair.com، rj.com، book-pia.crane.aero، britishairways.com)، بحث ذهاب وعودة 1 و6 نوفمبر، رحلات مباشرة للشركة نفسها، الدرجة السياحية، بالدرهم.",
             "طيران الهند والخطوط التركية والإماراتية: مواقعها تحجب المتصفح الآلي (حجب الشبكة أو تحقق بشري)، فتبقى يدوية."]:
    m.append([line])
wb.save(OUT); print(OUT)
for row in cmp_.iter_rows(min_row=2, values_only=True): print(row[:10])
