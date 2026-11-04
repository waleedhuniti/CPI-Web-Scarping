import json, sys
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
d = json.load(open(sys.argv[1])); s = d["summary"]; out = sys.argv[2]
navy = PatternFill("solid", fgColor="14264B"); amber = PatternFill("solid", fgColor="FFF2CC")
TIER_AR = {"exact": "منتج مطابق (باركود / اسم)", "product set": "تقدير مجموعة منتجات (ليس سعراً)"}
r1 = lambda v: None if v is None else round(v, 1)
def head(ws, cols, widths):
    ws.append(cols); ws.sheet_view.rightToLeft = True; ws.freeze_panes = "A2"
    for c in ws[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = navy; c.alignment = Alignment(wrap_text=True, vertical="center")
    for i, w in enumerate(widths): ws.column_dimensions[openpyxl.utils.get_column_letter(i + 1)].width = w
wb = openpyxl.Workbook()
ws = wb.active; ws.title = "الملخص"
head(ws, ["الفئة", "عدد البنود", "الفرق: أسعارنا أكتوبر ÷ الرسمي سبتمبر (متوسط هندسي %)", "الفرق الموزون بأوزان CPI %",
          "الفرق للبند الوسيط %", "البنود ضمن ±10%", "تغير الرسمي أكتوبر/سبتمبر % (نفس البنود)", "بنود مستبعدة (أكثر من 3 أضعاف)"],
     [30, 10, 20, 14, 12, 12, 18, 14])
for k, name in (("exact", TIER_AR["exact"]), ("product set", TIER_AR["product set"]), ("all", "كل البنود (للاطلاع فقط)")):
    a = s[k]; ws.append([name, a["n"], r1(a["geo"]), r1(a["wgeo"]), r1(a["med"]), f"{a['within10']:.0f}%", r1(a["offchg"]), a["far"]])
ws.append([]); ws.append(["النتيجة المعتمدة: صف «منتج مطابق» فقط. صف «تقدير مجموعة منتجات» غير صالح للمقارنة، لأن رقمه تقدير متسلسل على مجموعة منتجات قد تضم أصنافاً مختلفة وممتازة (مثلاً مجموعة «تفاح أصفر» تضم أناناس وكيوي وفلفل أصفر)."])
ws.append([]); notes = [
    "المقارنة: السعر الرسمي لشهر سبتمبر 2026 لكل بند مقابل متوسط أسعارنا المجموعة من 12 إلى 29 أكتوبر 2026 (17 يوماً، الأسطر المقبولة فقط).",
    "الأغذية فقط (رمز 011، بدون المشروبات). سعرنا للبند = متوسط الأيام لمتوسط المتاجر في كل يوم.",
    "إذا كانت وحدة البند الرسمية وزناً أو حجماً، حُوّل سعرنا لنفس الكمية بسعر الوحدة؛ وحدة لا تتحول بشكل صحيح (مثلاً قطعة مقابل غرام) استُبعدت.",
    "البنود التي سعرنا فيها أقل من ثلث أو أكثر من 3 أضعاف الرسمي تظهر في ورقة البنود (مظللة) ولا تدخل المتوسطات: غالباً منتج أو عبوة مختلفة.",
    "تغير الرسمي من سبتمبر لأكتوبر معروض للمقارنة: الفرق المتوقع بين أسعارنا لأكتوبر والرسمي لسبتمبر يقارب هذا التغير.",
    "الأوزان: أوزان مؤشر أسعار المستهلك لكل فئة من 7 أرقام (Book1)، مقسومة بالتساوي على بنودها ضمن الفئة."]
for n in notes: ws.append([n])
g = wb.create_sheet("حسب المجموعة")
head(g, ["المجموعة", "عدد البنود (الكل)", "الفرق % (الكل)", "الفرق للبند الوسيط % (الكل)", "ضمن ±10% (الكل)",
         "عدد البنود (منتج مطابق)", "الفرق % (منتج مطابق)", "ضمن ±10% (منتج مطابق)", "تغير الرسمي أكتوبر/سبتمبر %", "مستبعدة"],
     [36, 10, 11, 12, 11, 12, 12, 12, 14, 9])
for name, v in sorted(s["groups"].items(), key=lambda kv: -(kv[1]["all"] or {"n": 0})["n"]):
    a, e = v["all"], v["exact"]
    if not a: continue
    g.append([name, a["n"], r1(a["geo"]), r1(a["med"]), f"{a['within10']:.0f}%", e["n"] if e else 0, r1(e["geo"]) if e else None,
              f"{e['within10']:.0f}%" if e else None, r1(a["offchg"]), a["far"]])
it = wb.create_sheet("البنود")
head(it, ["رمز السلعة", "المجموعة", "وصف السلعة", "وحدة البيع", "الرسمي سبتمبر", "الرسمي أكتوبر", "أسعارنا أكتوبر (متوسط)",
          "الفرق عن سبتمبر %", "تغير الرسمي %", "مصدر سعرنا", "المتاجر", "أيام", "المنتجات التي التُقطت (الأكثر تكراراً)", "تفاصيل المجموعة", "ملاحظة"],
     [12, 26, 34, 10, 10, 10, 12, 11, 10, 20, 16, 6, 60, 40, 22])
for x in sorted(d["items"], key=lambda x: (x["group"], x["code"])):
    it.append([x["code"], x["group"], x["desc"], x["unit"], round(x["sep"], 2), round(x["oct_off"], 2) if x["oct_off"] else None,
               round(x["ours"], 2), r1(x["pct"]), r1(x["off_chg"]), TIER_AR.get(x["tier"], x["tier"]), x["shops"], x["days"], x["titles"], x["note"] if x["tier"] == "product set" else "",
               "مستبعد: منتج أو عبوة مختلفة" if x["far"] else ""])
    if x["far"]:
        for c in it[it.max_row]: c.fill = amber
wb.save(out); print("saved", out)
