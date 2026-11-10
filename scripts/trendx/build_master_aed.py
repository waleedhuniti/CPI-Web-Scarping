"""TrendX master price sheet in UAE dirhams: one row per commodity, years on row 1, months on row 2, one column per month.

    python3 scripts/trendx/build_master_aed.py <TE days dir> <ECB eurofxref-hist.csv> <out.xlsx> [store dir]

- Monthly columns (Jan 2024 to the month before our daily collection starts): the official monthly history in the store
  (World Bank, EIA, IMF, USDA, NBS, Ember, SSB, StatCan), real observations only. Carried-back values and the BLS index
  proxies are not prices, so they are left empty.
- Months covered by our daily collection: the average of that month's daily Trading Economics closes (one per quote date,
  a stale quote never counted twice), each converted at its day's rate. The history is built the same way (World Bank and
  EIA monthly values are averages of daily prices), so every column is a monthly average. The current month is marked partial.
- Currency: every price is converted to AED at the fixed peg 3.6725 AED per USD and the ECB reference rate of that day (daily
  columns) or the mean of that month (monthly columns); the physical unit is kept (AED/Bbl, AED/T, AED/Bu...).
  Cents and pence are divided by 100 first.
- ISIC Rev.4: every commodity carries the class of the activity that produces it (sheet ISIC: section, division, group, class).
"""
import csv
import glob
import json
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

AED_PER_USD = 3.6725
MONTHS_AR = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]

# ISIC Rev.4 class of the producing activity, per TrendX commodity (TE name). note: why, where a choice was needed.
ISIC = {
    "Crude Oil": ("0610", ""), "Brent": ("0610", ""), "Urals Oil": ("0610", ""),
    "Natural gas": ("0620", ""), "EU Gas": ("0620", ""), "German Gas": ("0620", ""), "UK Gas": ("0620", ""),
    "LNG JKM": ("0620", "liquefied natural gas: the product of 0620 (liquefaction for transport is support activity 0910)"),
    "Gasoline": ("1920", ""), "Heating Oil": ("1920", ""), "Naphtha": ("1920", ""), "Bitumen": ("1920", ""),
    "Propane": ("1920", "refinery LPG; propane from gas-field fractionation would be 0620"),
    "Coal": ("0510", ""), "Coking Coal": ("0510", ""), "Uranium": ("0721", ""),
    "Methanol": ("2011", ""), "Ethanol": ("2011", "fuel ethanol (undenatured beverage alcohol would be 1101)"),
    "Gold": ("2420", "refined metal (ore mining would be 0729)"), "Silver": ("2420", ""), "Platinum": ("2420", ""), "Palladium": ("2420", ""), "Rhodium": ("2420", ""),
    "Copper": ("2420", ""), "Aluminum": ("2420", ""), "Lead": ("2420", ""), "Tin": ("2420", ""), "Zinc": ("2420", ""), "Nickel": ("2420", ""),
    "Cobalt": ("2420", ""), "Molybdenum": ("2420", ""), "Titanium": ("2420", ""), "Magnesium": ("2420", ""), "Aluminum Alloy": ("2420", ""),
    "Gallium": ("2420", ""), "Germanium": ("2420", ""), "Indium": ("2420", ""),
    "Tellurium": ("2011", "metalloid, chemical element (HS 2804)"), "Silicon": ("2011", "silicon, chemical element (HS 2804)"),
    "Lithium": ("2011", "lithium carbonate, inorganic chemical (HS 2836)"), "Cobalt Hydroxide": ("2011", "cobalt hydroxide, inorganic chemical (HS 2822)"),
    "Neodymium": ("2011", "rare-earth metal, chemical element (HS 2805)"), "Manganese": ("0729", "manganese ore 44% Mn"),
    "Iron Ore": ("0710", ""), "Iron Ore CNY": ("0710", ""), "Steel": ("2410", "rebar"), "HRC Steel": ("2410", "hot-rolled coil"),
    "Scrap Steel": ("3830", "materials recovery"), "Scrap Aluminum": ("3830", "materials recovery"),
    "Soybeans": ("0111", ""), "Wheat": ("0111", ""), "Corn": ("0111", ""), "Oat": ("0111", ""), "Barley": ("0111", ""), "Rapeseed": ("0111", ""), "Canola": ("0111", ""),
    "Rice": ("0112", "rough (paddy) rice; milled rice would be 1061"), "Cotton": ("0116", "raw cotton (ginning is 0163)"),
    "Coffee": ("0127", "green coffee"), "Cocoa": ("0127", "cocoa beans"), "Tea": ("0127", ""), "Rubber": ("0129", "natural rubber"),
    "Palm Oil": ("1040", "crude palm oil"), "Sunflower Oil": ("1040", ""), "Sugar": ("1072", "raw sugar"), "Orange Juice": ("1030", "frozen concentrated orange juice"),
    "Lumber": ("1610", ""), "Butter": ("1050", ""), "Cheese": ("1050", ""), "Milk": ("0141", "raw cow milk (Class III price)"), "Wool": ("0144", "greasy wool"),
    "Beef": ("0141", "live cattle (Brazilian arroba)"), "Live Cattle": ("0141", ""), "Feeder Cattle": ("0141", ""), "Lean Hogs": ("0145", "live hogs"),
    "Poultry": ("1010", "chicken meat"), "Eggs US": ("0146", ""), "Eggs CH": ("0146", ""), "Salmon": ("0321", "farmed Atlantic salmon"),
    "Urea": ("2012", ""), "Di-ammonium": ("2012", "diammonium phosphate"), "Phosphorus": ("2011", "yellow phosphorus"),
    "Polyethylene": ("2013", ""), "Polyvinyl": ("2013", "PVC"), "Polypropylene": ("2013", ""), "Synthetic Rubber": ("2013", ""),
    "Styrene": ("2011", "monomer, basic organic chemical"), "Soda Ash": ("2011", ""), "Sulfur": ("2011", ""), "Kraft Pulp": ("1701", ""),
    "United Kingdom": ("3510", "wholesale day-ahead electricity"), "Germany": ("3510", ""), "France": ("3510", ""), "Italy": ("3510", ""), "Spain": ("3510", ""),
}
SECTION = {"A": ("Agriculture, forestry and fishing", "الزراعة والحراجة وصيد الأسماك"), "B": ("Mining and quarrying", "التعدين واستغلال المحاجر"),
           "C": ("Manufacturing", "الصناعات التحويلية"), "D": ("Electricity, gas, steam and air conditioning supply", "إمدادات الكهرباء والغاز والبخار وتكييف الهواء"),
           "E": ("Water supply; sewerage, waste management and remediation activities", "إمدادات المياه وأنشطة الصرف الصحي وإدارة النفايات ومعالجتها")}
DIVISION = {"01": ("A", "Crop and animal production, hunting and related service activities", "زراعة المحاصيل والإنتاج الحيواني والصيد والأنشطة الخدمية المتصلة بها"),
            "03": ("A", "Fishing and aquaculture", "صيد الأسماك وتربية المائيات"), "05": ("B", "Mining of coal and lignite", "تعدين الفحم والليغنيت"),
            "06": ("B", "Extraction of crude petroleum and natural gas", "استخراج النفط الخام والغاز الطبيعي"), "07": ("B", "Mining of metal ores", "تعدين ركازات الفلزات"),
            "10": ("C", "Manufacture of food products", "صناعة المنتجات الغذائية"), "16": ("C", "Manufacture of wood and of products of wood and cork, except furniture", "صناعة الخشب ومنتجات الخشب والفلين، باستثناء الأثاث"),
            "17": ("C", "Manufacture of paper and paper products", "صناعة الورق ومنتجات الورق"), "19": ("C", "Manufacture of coke and refined petroleum products", "صناعة فحم الكوك والمنتجات النفطية المكررة"),
            "20": ("C", "Manufacture of chemicals and chemical products", "صناعة المواد الكيميائية والمنتجات الكيميائية"), "24": ("C", "Manufacture of basic metals", "صناعة الفلزات القاعدية"),
            "35": ("D", "Electricity, gas, steam and air conditioning supply", "إمدادات الكهرباء والغاز والبخار وتكييف الهواء"),
            "38": ("E", "Waste collection, treatment and disposal activities; materials recovery", "أنشطة جمع النفايات ومعالجتها والتخلص منها؛ استرجاع المواد")}
GROUP = {"011": ("Growing of non-perennial crops", "زراعة المحاصيل غير الدائمة"), "012": ("Growing of perennial crops", "زراعة المحاصيل الدائمة"),
         "014": ("Animal production", "الإنتاج الحيواني"), "032": ("Aquaculture", "تربية المائيات"), "051": ("Mining of hard coal", "تعدين الفحم الصلب"),
         "061": ("Extraction of crude petroleum", "استخراج النفط الخام"), "062": ("Extraction of natural gas", "استخراج الغاز الطبيعي"),
         "071": ("Mining of iron ores", "تعدين ركازات الحديد"), "072": ("Mining of non-ferrous metal ores", "تعدين ركازات الفلزات غير الحديدية"),
         "101": ("Processing and preserving of meat", "تجهيز اللحوم وحفظها"), "103": ("Processing and preserving of fruit and vegetables", "تجهيز الفاكهة والخضر وحفظها"),
         "104": ("Manufacture of vegetable and animal oils and fats", "صناعة الزيوت والدهون النباتية والحيوانية"), "105": ("Manufacture of dairy products", "صناعة منتجات الألبان"),
         "107": ("Manufacture of other food products", "صناعة منتجات غذائية أخرى"), "161": ("Sawmilling and planing of wood", "نشر الخشب وتسويته"),
         "170": ("Manufacture of paper and paper products", "صناعة الورق ومنتجات الورق"), "192": ("Manufacture of refined petroleum products", "صناعة المنتجات النفطية المكررة"),
         "201": ("Manufacture of basic chemicals, fertilizers and nitrogen compounds, plastics and synthetic rubber in primary forms", "صناعة الكيماويات الأساسية والأسمدة ومركبات النيتروجين واللدائن والمطاط الصناعي في أشكالها الأولية"),
         "241": ("Manufacture of basic iron and steel", "صناعة الحديد والصلب القاعدية"), "242": ("Manufacture of basic precious and other non-ferrous metals", "صناعة الفلزات النفيسة والفلزات غير الحديدية القاعدية"),
         "351": ("Electric power generation, transmission and distribution", "توليد الطاقة الكهربائية ونقلها وتوزيعها"), "383": ("Materials recovery", "استرجاع المواد")}
CLASS = {"0111": ("Growing of cereals (except rice), leguminous crops and oil seeds", "زراعة الحبوب (عدا الأرز) والمحاصيل البقولية والبذور الزيتية"),
         "0112": ("Growing of rice", "زراعة الأرز"), "0116": ("Growing of fibre crops", "زراعة محاصيل الألياف"), "0127": ("Growing of beverage crops", "زراعة محاصيل المشروبات"),
         "0129": ("Growing of other perennial crops", "زراعة محاصيل دائمة أخرى"), "0141": ("Raising of cattle and buffaloes", "تربية الأبقار والجاموس"),
         "0144": ("Raising of sheep and goats", "تربية الأغنام والماعز"), "0145": ("Raising of swine/pigs", "تربية الخنازير"), "0146": ("Raising of poultry", "تربية الدواجن"),
         "0321": ("Marine aquaculture", "تربية الأحياء البحرية"), "0510": ("Mining of hard coal", "تعدين الفحم الصلب"), "0610": ("Extraction of crude petroleum", "استخراج النفط الخام"),
         "0620": ("Extraction of natural gas", "استخراج الغاز الطبيعي"), "0710": ("Mining of iron ores", "تعدين ركازات الحديد"),
         "0721": ("Mining of uranium and thorium ores", "تعدين ركازات اليورانيوم والثوريوم"), "0729": ("Mining of other non-ferrous metal ores", "تعدين ركازات فلزات أخرى غير حديدية"),
         "1010": ("Processing and preserving of meat", "تجهيز اللحوم وحفظها"), "1030": ("Processing and preserving of fruit and vegetables", "تجهيز الفاكهة والخضر وحفظها"),
         "1040": ("Manufacture of vegetable and animal oils and fats", "صناعة الزيوت والدهون النباتية والحيوانية"), "1050": ("Manufacture of dairy products", "صناعة منتجات الألبان"),
         "1072": ("Manufacture of sugar", "صناعة السكر"), "1610": ("Sawmilling and planing of wood", "نشر الخشب وتسويته"),
         "1701": ("Manufacture of pulp, paper and paperboard", "صناعة عجينة الورق والورق والورق المقوى"), "1920": ("Manufacture of refined petroleum products", "صناعة المنتجات النفطية المكررة"),
         "2011": ("Manufacture of basic chemicals", "صناعة الكيماويات الأساسية"), "2012": ("Manufacture of fertilizers and nitrogen compounds", "صناعة الأسمدة ومركبات النيتروجين"),
         "2013": ("Manufacture of plastics and synthetic rubber in primary forms", "صناعة اللدائن والمطاط الصناعي في أشكالها الأولية"),
         "2410": ("Manufacture of basic iron and steel", "صناعة الحديد والصلب القاعدية"), "2420": ("Manufacture of basic precious and other non-ferrous metals", "صناعة الفلزات النفيسة والفلزات غير الحديدية القاعدية"),
         "3510": ("Electric power generation, transmission and distribution", "توليد الطاقة الكهربائية ونقلها وتوزيعها"), "3830": ("Materials recovery", "استرجاع المواد")}


def item_codes():
    """unique 6-digit item code: the ISIC Rev.4 class (4 digits) + a 2-digit serial within that class, in the order of ISIC
    above. New commodities take the next serial in their class; existing codes never change."""
    seen, out = defaultdict(int), {}
    for name, (cls, _) in ISIC.items():
        seen[cls] += 1; out[name] = f"{cls}{seen[cls]:02d}"
    return out


def isic_rows():
    """one row per commodity with the full ISIC Rev.4 path."""
    out = []; codes = item_codes()
    for name, (cls, note) in ISIC.items():
        div, grp = cls[:2], cls[:3]; sec = DIVISION[div][0]
        out.append(dict(item_code=codes[name], commodity=name, section=sec, section_en=SECTION[sec][0], section_ar=SECTION[sec][1], division=div, division_en=DIVISION[div][1], division_ar=DIVISION[div][2],
                        group=grp, group_en=GROUP[grp][0], group_ar=GROUP[grp][1], isic_class=cls, class_en=CLASS[cls][0], class_ar=CLASS[cls][1], note=note))
    return out


def read_fx(path):
    """{date: {cur: units per EUR}} and a per-month mean."""
    day = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        rates = {}
        for k, v in r.items():
            try: rates[k] = float(v)
            except (TypeError, ValueError): pass
        if "USD" in rates: day[r["Date"]] = rates
    mon = defaultdict(lambda: defaultdict(list))
    for d, rates in day.items():
        for k, v in rates.items(): mon[d[:7]][k].append(v)
    return day, {m: {k: statistics.fmean(v) for k, v in c.items()} for m, c in mon.items()}


def aed_per(cur, rates):
    """AED per one unit of `cur`, from ECB rates (units per EUR)."""
    if cur == "USD": return AED_PER_USD
    if cur == "EUR": return AED_PER_USD * rates["USD"]
    return AED_PER_USD * rates["USD"] / rates[cur] if cur in rates else None


def parse_unit(u):
    """TE unit -> (currency, multiplier to whole currency units, AED unit label)."""
    u = (u or "").strip()
    if u.startswith("USD Cents"): return "USD", 0.01, "AED/" + u.split("/")[-1].strip()
    cur, _, phys = u.partition("/")
    cur = cur.strip(); phys = phys.strip()
    if cur == "USd": return "USD", 0.01, f"AED/{phys}"
    if cur == "GBp": return "GBP", 0.01, f"AED/{phys}"
    return cur.upper(), 1.0, f"AED/{phys}"


def main(days_dir, ecb_csv, out_path, store="data/trendx/store"):
    store = Path(store)
    S = list(csv.DictReader(open(store / "series.csv", encoding="utf-8")))
    fxd, fxm = read_fx(ecb_csv); fx_days = sorted(fxd)
    def fx_on(d):
        c = [x for x in fx_days if x <= d]; return fxd[c[-1]] if c else None
    # daily capture: (commodity, quote date) -> price, last run wins
    daily, runs = {}, []
    for f in sorted(glob.glob(str(Path(days_dir) / "*.json"))):
        doc = json.load(open(f, encoding="utf-8")); doc = doc.get("data", doc); cols = doc["cols"]; run = doc.get("run_date") or Path(f).stem
        runs.append(run[:10])
        for r in doc["rows"]:
            r = dict(zip(cols, r))
            if r.get("category") == "Index" or r.get("price") in (None, ""): continue
            daily[(r["commodity"], (r.get("price_date") or run)[:10])] = float(r["price"])
    # the daily part starts with the month of our first run; older quote dates seen on the first days were stale quotes
    first_daily_month = min(runs)[:7]
    daily = {k: v for k, v in daily.items() if k[1][:7] >= first_daily_month}
    day_list = sorted({d for _, d in daily})
    # monthly history: real observations from the external sources, before the daily collection starts
    monthly = {}
    for o in csv.DictReader(open(store / "observations.csv", encoding="utf-8")):
        if o["obs_status"] != "A" or o["source"] in ("te", "carried_back", "bls") or o["period"] >= first_daily_month: continue
        monthly[(o["commodity"], o["period"])] = float(o["value"])
    months = sorted({p for _, p in monthly})
    ym_daily = sorted({d[:7] for d in day_list})

    wb = Workbook(); ws = wb.active; ws.title = "Prices AED"
    F = Font(name="Arial", size=10); FB = Font(name="Arial", size=10, bold=True); FH = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    HF = PatternFill("solid", fgColor="1B2A52"); AV = PatternFill("solid", fgColor="FFF3D6"); thin = Side(style="thin", color="CBD5E1")
    C = Alignment(horizontal="center", vertical="center"); BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
    LEAD = ["رمز الصنف", "الصنف", "الوحدة (درهم)", "ISIC Rev.4"]
    codes = item_codes(); S = sorted(S, key=lambda s: codes.get(s["commodity"], "999999"))
    partial_month = ym_daily[-1] if ym_daily and ym_daily[-1] >= date.today().isoformat()[:7] else None

    def header(sh, layout, nrows):
        """row 1 year, row 2 month (merged over their columns), row 3 day (daily sheet only)."""
        for j, h in enumerate(LEAD, 1):
            sh.cell(1, j, h)
            if nrows > 1: sh.merge_cells(start_row=1, start_column=j, end_row=nrows, end_column=j)
        def merge_runs(row, keyf):
            runs_ = []
            for c_, _, key in layout:
                k = keyf(key)
                if runs_ and runs_[-1][2] == k: runs_[-1][1] = c_
                else: runs_.append([c_, c_, k])
            for a_, b_, k in runs_:
                sh.cell(row, a_, k)
                if b_ > a_: sh.merge_cells(start_row=row, start_column=a_, end_row=row, end_column=b_)
        merge_runs(1, lambda key: int(key[:4]))
        merge_runs(2, lambda key: MONTHS_AR[int(key[5:7]) - 1] + (" (جزئي)" if nrows == 2 and key[:7] == partial_month else ""))
        if nrows == 3:
            for c_, _, key in layout: sh.cell(3, c_, int(key[8:10]))
        last = layout[-1][0] if layout else len(LEAD)
        for r in range(1, nrows + 1):
            for c_ in range(1, last + 1):
                cell = sh.cell(r, c_); cell.font = FH; cell.fill = HF; cell.alignment = C; cell.border = BOX
        sh.freeze_panes = sh.cell(nrows + 1, len(LEAD) + 1)
        for col_, w_ in zip("ABCD", (10, 20, 18, 10)): sh.column_dimensions[col_].width = w_
        for c_, _, _ in layout: sh.column_dimensions[get_column_letter(c_)].width = 11 if nrows == 2 else 9

    # Monthly sheet: one column per month, same format for every year; months covered by the daily collection are the
    # average of their daily columns (formula into the Daily sheet), the history is the official monthly average
    mlay = [(len(LEAD) + 1 + j, "M", m) for j, m in enumerate(months)]
    mlay += [(len(LEAD) + 1 + len(months) + j, "A", ym) for j, ym in enumerate(ym_daily)]
    header(ws, mlay, 2)
    for i, s in enumerate(S):
        name = s["commodity"]; cur, mult, aed_unit = parse_unit(s["unit"]); rm, rd = 3 + i, 4 + i
        ws.cell(rm, 1, codes.get(name, "")).font = FB; ws.cell(rm, 2, name).font = FB; ws.cell(rm, 3, aed_unit).font = F; ws.cell(rm, 4, ISIC.get(name, ("", ""))[0]).font = F
        for c_, kind, key in mlay:
            cell = ws.cell(rm, c_)
            if kind == "M":
                v = monthly.get((name, key)); rates = fxm.get(key); k = aed_per(cur, rates) if rates else None
                if v is None or k is None: continue
                cell.value = round(v * mult * k, 4); cell.font = F
            else:   # the month's average of our daily closes, each converted to AED at that day's rate
                vals = []
                for d in day_list:
                    if not d.startswith(key) or (name, d) not in daily: continue
                    rates = fx_on(d); k = aed_per(cur, rates) if rates else None
                    if k is not None: vals.append(daily[(name, d)] * mult * k)
                if not vals: continue
                cell.value = round(statistics.fmean(vals), 4); cell.fill = AV; cell.font = F
            cell.number_format = "#,##0.00"

    # ISIC sheet
    isx = wb.create_sheet("ISIC"); isx.sheet_view.rightToLeft = True
    H = ["رمز الصنف", "الصنف", "القسم (Section)", "اسم القسم", "Section", "الشعبة (Division)", "اسم الشعبة", "Division", "المجموعة (Group)", "اسم المجموعة", "Group", "الفئة (Class)", "اسم الفئة", "Class", "ملاحظة"]
    keys = ["item_code", "commodity", "section", "section_ar", "section_en", "division", "division_ar", "division_en", "group", "group_ar", "group_en", "isic_class", "class_ar", "class_en", "note"]
    for j, h in enumerate(H, 1):
        c = isx.cell(1, j, h); c.font = FH; c.fill = HF; c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    rows = {r["commodity"]: r for r in isic_rows()}
    for i, s in enumerate(S, 2):
        r = rows.get(s["commodity"])
        for j, k in enumerate(keys, 1):
            c = isx.cell(i, j, r[k] if r else ""); c.font = F; c.alignment = Alignment(vertical="top", wrap_text=k.endswith(("_ar", "_en", "note")))
    for j, w in enumerate([10, 18, 8, 30, 30, 8, 36, 36, 8, 40, 40, 8, 40, 40, 40], 1): isx.column_dimensions[get_column_letter(j)].width = w
    isx.freeze_panes = "B2"; isx.auto_filter.ref = f"A1:{get_column_letter(len(H))}{len(S) + 1}"

    # notes
    nt = wb.create_sheet("ملاحظات"); nt.sheet_view.rightToLeft = True; nt.column_dimensions["A"].width = 130
    notes = [f"بُني {date.today().isoformat()}. الصفوف: {len(S)} سلعة. الأعمدة: {len(months)} شهراً من التاريخ الرسمي ({months[0]} → {months[-1]})، ثم {len(day_list)} يوماً من جمعنا ({day_list[0]} → {day_list[-1]}) مع متوسط لكل شهر.",
             "ورقة Prices AED: عمود لكل شهر بالشكل نفسه لكل السنوات (السنة في الصف 1، الشهر في الصف 2). حتى سبتمبر 2026: المتوسط الشهري الرسمي (البنك الدولي، EIA، IMF، USDA، NBS، Ember، الإحصاء النرويجي والكندي). من أكتوبر 2026: متوسط أيام الشهر من جمعنا اليومي (مظلل).",
             "أكتوبر ونوفمبر 2026 (مظللان): متوسط أسعار الإغلاق اليومية من جمعنا خلال الشهر، كل سعر محوّل بسعر صرف يومه. المتوسط لا المجموع، كما في التاريخ الرسمي. الشهر الجاري مكتوب «(جزئي)» ويتحدث مع كل تشغيل.",
             "التحويل إلى الدرهم: 3.6725 درهم لكل دولار (الربط الرسمي)، والعملات الأخرى عبر أسعار البنك المركزي الأوروبي المرجعية لليوم نفسه (اليومي) أو متوسط الشهر (الشهري). السنت والبنس يُقسمان على 100 أولاً. الوحدة الفيزيائية لا تتغير (برميل، طن، بوشل...).",
             "خانة فارغة = لا سعر حقيقي: لا تثبيت رجوعي ولا ترحيل. السلاسل المُثبّتة الـ 13 فارغة قبل أكتوبر 2026. خردة الحديد والألمنيوم فارغة قبل أكتوبر لأن مصدرها مؤشر BLS لا سعر.",
             "السلاسل البديلة (منتج أو سوق قريب) مذكورة في data/trendx/store/series.csv عمود proxy_of. ترميز ISIC Rev.4 في ورقة ISIC: نشاط إنتاج السلعة حتى الفئة (4 أرقام).",
             "رمز الصنف: 6 أرقام فريدة لكل سلعة = فئة ISIC Rev.4 (4 أرقام) + تسلسل من رقمين داخل الفئة. مثال: 242001 الذهب، 242002 الفضة. الصنف الجديد يأخذ التسلسل التالي في فئته ولا تتغير الرموز القائمة."]
    for i, t in enumerate(notes, 1): nt.cell(i, 1, t).font = F; nt.cell(i, 1).alignment = Alignment(wrap_text=True, horizontal="right")
    wb.save(out_path)
    print(f"{len(S)} rows, {len(months)} monthly + {len(day_list)} daily columns ({day_list[0]} to {day_list[-1]}) -> {out_path}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
