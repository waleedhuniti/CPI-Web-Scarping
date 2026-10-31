"""Ticket sheets for one trip (out / back dates) from each airline's own site: flydubai on the domestic sheet, the national carriers
on the foreign sheet, in the layout of the manual team's workbook (their sheets are copied and the first week's cells refilled).
usage: python3 write_tickets_week.py <manual workbook> <results dir> <out.xlsx> <out date YYYY-MM-DD> <back date YYYY-MM-DD>
Results dir holds fz_res.json (fz_full.py) and air_<airline>_res.json; a missing or empty result leaves the row empty with the reason."""
import json, os, sys, datetime as dt, openpyxl
from openpyxl.styles import Font, PatternFill
SRC, RD, OUT, OUT_D, BACK_D = sys.argv[1:6]
day = lambda s: f"{dt.date.fromisoformat(s).day} نوفمبر" if s[5:7] == "11" else s
yellow = PatternFill("solid", fgColor="FFF2CC")
def load(f, k):
    try:
        v = json.load(open(os.path.join(RD, f))).get(k)
        return v if isinstance(v, dict) and (v.get("out") or v.get("back")) else None
    except FileNotFoundError:
        return None
def rows_of(ws, keys, first=3):
    out = {}
    for r in range(first, 40):
        a = str(ws.cell(r, 1).value or "").lower()
        for k in keys:
            if k in a: out[k] = r
    return out
def fill(ws, r0, res, why, note="", c0=3):
    """lowest / highest per leg in the airline's first two columns (C/D, Emirates F/G; highest empty when equal), the trip's
    formulas, and the note text (written by the caller)."""
    notes = [note] if note else []
    L, H, A = (openpyxl.utils.get_column_letter(c0 + i) for i in range(3))
    for i, leg in enumerate(("out", "back")):
        x = (res or {}).get(leg)
        lo, hi = (x["lowest"], x["highest"]) if x else (None, None)
        ws.cell(r0 + i, c0).value = lo; ws.cell(r0 + i, c0 + 1).value = hi if hi != lo else None
        if x and x.get("shifted_days"):
            ws.cell(r0 + i, c0).fill = yellow
            notes.append(f"{'الذهاب' if i == 0 else 'العودة'}: لا توجد رحلة يوم {day((OUT_D, BACK_D)[i])}، أُخذ {day(x['date'])}")
    if res and res.get("out") and res.get("back"):
        ws.cell(r0 + 2, c0).value = f"=SUM({L}{r0}:{L}{r0+1})"
        ws.cell(r0 + 2, c0 + 1).value = f'=IF(AND({H}{r0}="",{H}{r0+1}=""),"",IF({H}{r0}="",{L}{r0},{H}{r0})+IF({H}{r0+1}="",{L}{r0+1},{H}{r0+1}))'
        ws.cell(r0 + 2, c0 + 2).value = f"=AVERAGE({L}{r0+2}:{H}{r0+2})"
    elif why:
        notes.append(why)
    return " · ".join(notes)

def flights(det, airline, city, res):
    for i, leg in enumerate(("out", "back")):
        x = (res or {}).get(leg) or {}
        for f in x.get("flights", []):
            dep = str(f.get("dep", "")); dep = dep[11:16] if len(dep) >= 16 and dep[10] in "T " else dep
            det.append([airline, city, ("ذهاب", "عودة")[i], x.get("date"), f.get("flight"), dep, f.get("from")])
wb = openpyxl.load_workbook(SRC)
title = f"ذهاب {day(OUT_D)}، عودة {day(BACK_D)} 2026 (بحث ذهاب وعودة، موقع كل شركة)"
det = wb.create_sheet("الرحلات"); det.sheet_view.rightToLeft = True
det.append(["الشركة", "الوجهة", "الاتجاه", "التاريخ", "الرحلة", "الإقلاع", "أرخص سعر سياحي (درهم)"])
# domestic sheet: flydubai (C-E) and Emirates (F-H, ek_fares.py, one one-way search per leg)
src = wb["الطيران المحلى"]
dom = wb.copy_worksheet(src); dom.title = f"محلي {dt.date.fromisoformat(OUT_D).day}-{dt.date.fromisoformat(BACK_D).day} نوفمبر"; dom.sheet_view.rightToLeft = src.sheet_view.rightToLeft
dom.cell(1, 3).value = title
for r in range(4, dom.max_row + 1):
    for c in range(3, dom.max_column + 1):
        v = dom.cell(r, c).value
        if isinstance(v, (int, float)) or (isinstance(v, str) and v.startswith("=")): dom.cell(r, c).value = None
FZ = {"delhi": "DEL", "riyadh": "RUH", "karachi": "KHI", "colombo": "CMB", "istanbul": "IST", "alexandria": "ALY", "amman": "AMM"}
fz = json.load(open(os.path.join(RD, "fz_res.json"))) if os.path.exists(os.path.join(RD, "fz_res.json")) else {}
for key, r0 in rows_of(dom, FZ, 4).items():
    res = fz.get(FZ[key]); res = res if res and (res.get("out") or res.get("back")) else None
    note = fill(dom, r0, res, "لا توجد رحلات فلاي دبي على هذا الخط")
    if note: dom.cell(r0, 10).value = note; dom.cell(r0, 10).fill = yellow
    flights(det, "فلاي دبي", dom.cell(r0, 1).value, res)
EK = {"delhi": "DEL", "london": "LHR", "riyadh": "RUH", "karachi": "KHI", "new york": "JFK", "colombo": "CMB", "bangkok": "BKK",
      "istanbul": "IST", "cairo": "CAI", "amman": "AMM"}
ek = json.load(open(os.path.join(RD, "ek_res.json"), encoding="utf-8")) if os.path.exists(os.path.join(RD, "ek_res.json")) else None
for key, r0 in rows_of(dom, EK, 4).items():
    if ek is None:
        why = "موقع الإماراتية يرفض البحث من المتصفح الآلي؛ يبقى يدوياً"
        res = None
    else:
        res = ek.get(EK[key]) or {}
        why = res.get("out_error") or res.get("back_error") or "لم يكتمل السحب"
        why = "موقع الإماراتية رفض البحث في هذا السحب؛ يبقى يدوياً" if "access restricted" in why else "الإماراتية: " + why
        res = res if (res.get("out") or res.get("back")) else None
    note = fill(dom, r0, res, why, c0=6)
    if note:
        c = dom.cell(r0, 10); c.value = " · ".join(v for v in (c.value, note) if v); c.fill = yellow
    flights(det, "الإماراتية", dom.cell(r0, 1).value, res)
# foreign sheet: each country's carrier from its own site
FOREIGN = {
    "delhi": ("طيران الهند", "air_airindia_res.json", "DEL", "موقع طيران الهند يحجب المتصفح الآلي؛ يبقى يدوياً"),
    "london": ("الخطوط البريطانية", "air_ba_res.json", "LHR", "قائمة رحلات البريطانية محجوبة للمتصفح الآلي؛ يظهر أقل سعر للذهاب فقط من شريط التواريخ"),
    "riyadh": ("الخطوط السعودية", "air_saudia_res.json", "RUH", "لم يكتمل السحب"),
    "isb": ("الخطوط الباكستانية", "air_pia_res.json", "ISB", "لم يكتمل السحب"),
    "istanbul": ("الخطوط التركية", "air_turkish_res.json", "IST", "موقع الخطوط التركية يطلب تحقق بشري؛ يبقى يدوياً"),
    "cairo": ("مصر للطيران", "air_egyptair_res.json", "CAI", "موقع مصر للطيران أظهر تحقق Cloudflare قبل نموذج البحث في هذا السحب؛ لم يُسحب"),
    "amman": ("الملكية الأردنية", "air_rj_res.json", "AMM", "لم يكتمل السحب"),
}
src = wb["الطيران الاجنبى"]
fo = wb.copy_worksheet(src); fo.title = f"أجنبي {dt.date.fromisoformat(OUT_D).day}-{dt.date.fromisoformat(BACK_D).day} نوفمبر"; fo.sheet_view.rightToLeft = src.sheet_view.rightToLeft
fo.cell(1, 2).value = title
for r in range(3, 24):
    for c in range(3, fo.max_column + 1):
        v = fo.cell(r, c).value
        if isinstance(v, (int, float)) or (isinstance(v, str) and v.startswith("=")): fo.cell(r, c).value = None
for key, r0 in rows_of(fo, FOREIGN).items():
    airline, f, ap, why = FOREIGN[key]
    res = load(f, ap)
    note = fill(fo, r0, res, why)
    c = fo.cell(r0, 6); c.value = airline + (" · " + note if note else ""); c.fill = yellow if note else PatternFill()
    flights(det, airline, fo.cell(r0, 1).value, res)
for c in det[1]: c.font = Font(bold=True)
for col, w in zip("ABCDEFG", (16, 22, 9, 12, 10, 9, 18)): det.column_dimensions[col].width = w
m = wb.create_sheet("المنهجية"); m.sheet_view.rightToLeft = True
for line in [f"تاريخ السحب {dt.date.today().isoformat()}. بحث ذهاب وعودة من دبي: ذهاب {day(OUT_D)}، عودة {day(BACK_D)} 2026، بالغ واحد، الدرجة السياحية، رحلات مباشرة للشركة نفسها، بالدرهم.",
             "المصدر: موقع كل شركة مباشرة (flydubai.com، emirates.com، saudia.com، egyptair.com، rj.com، book-pia.crane.aero، britishairways.com).",
             "لكل رحلة يؤخذ أرخص سعر سياحي لها. أقل سعر = أرخص رحلة في اليوم، أعلى سعر = أغلى رحلة؛ إذا تساويا يُترك أعلى سعر فارغاً، ويحسب مجموع أعلى سعر من أقل سعر لذلك الاتجاه.",
             "إذا لم توجد رحلة يوم الذهاب أو العودة يؤخذ اليوم الذي بعده (مظلل بالأصفر مع ملاحظة).",
             "الإماراتية: بحث باتجاه واحد لكل رحلة (دبي إلى المدينة يوم الذهاب، والمدينة إلى دبي يوم العودة)، أرخص سعر سياحي لكل رحلة مباشرة وغير مباشرة كما تظهر.",
             "طيران الهند والخطوط التركية: مواقعها تحجب المتصفح الآلي أو تطلب تحقق بشري، فتبقى يدوية. البريطانية: أقل سعر للذهاب فقط.",
             "الأسعار تتغير خلال اليوم، خاصة عند آخر المقاعد."]:
    m.append([line])
m.column_dimensions["A"].width = 140
for ws in (dom, fo):                                            # the summary rows point at the other sheet: point them at our copies
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and c.value.startswith("="):
                c.value = c.value.replace("'الطيران المحلى'!", f"'{dom.title}'!").replace("'الطيران الاجنبى'!", f"'{fo.title}'!")
for name in ("الطيران المحلى", "الطيران الاجنبى"):            # keep only our sheets; the team's own sheets are the template
    wb.remove(wb[name])
wb.move_sheet(det, offset=len(wb.sheetnames) - 1 - wb.sheetnames.index(det.title) - 1)   # flights and method after the two sheets
wb.save(OUT); print(OUT, wb.sheetnames)
