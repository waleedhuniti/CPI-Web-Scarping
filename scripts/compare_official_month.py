"""Our scraped item prices against the official monthly average prices, by CPI group, with charts.

    python scripts/compare_official_month.py <official prices.xlsx> <month column, e.g. أكتوبر> <crawl CSV (build_dataiku_range.py)> <out.xlsx>

Items are matched on the 9-digit CPI code. The crawl price of an item = the mean over the days of each day's mean over the shops
(accepted rows only). The price compared is in the official sale unit: when that unit is a weight or a volume (g, kg, ml, litre)
the crawl price converted to the line's quantity (price_spec); otherwise (piece, pack, bunch, count) the shelf price.
An item whose crawl price is under a third or over three times the official one is kept in the item sheet, flagged
(a different product or pack size was matched), and left out of the group averages and the charts.
"""
import csv
import re
import statistics as st
import sys
from collections import defaultdict

import openpyxl
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Font, PatternFill, Alignment

# a quantity in a weight or volume unit ("400 غ", "1.5 ليتر", "6 * 125 ml", "ا لتر"); a unit followed by a letter does not count
# (غرفه، غسالة، ملم، كيلووات). The Dataiku flow (docs/dataiku_flow_official_vs_scraped.md) uses the same pattern.
WEIGHT = re.compile(r"(?:^|[\d\s*x×.])\s*(كغم?|كجم?|كيلو(?:غرام)?|غم?|غرام|جرام|جم|ملل?|لتر|ليتر|kg|gm?|gr|ml|cl|ltr|lt|l)(?![^\W\d_])", re.I)
FAR = 3.0
SHORT = {"أجهزة أخرى (غير كهربائية) وأصناف ومنتجات معدة للعناية الشخصية": "منتجات العناية الشخصية",
         "منتجات الاغذية غير المصنفة تحت بند اخر": "أغذية أخرى", "السكر والمربي والعسل والشوكلاتة والحلوي": "السكر والحلويات",
         "مشروبات أخرى (الطاقة وغيرها)": "مشروبات أخرى", "الأسماك والاغذية البحرية": "الأسماك", "اللبن و الجبن و البيض": "الألبان والبيض",
         "مستلزمات الملابس وإكسسواراتها": "إكسسوارات الملابس", "الأدوات الصغيرة ومستلزمات المنزل": "أدوات صغيرة للمنزل"}


def short(g):                                             # chart labels: tatweel removed, long group names shortened
    g = " ".join(g.replace("ـ", "").split())
    return SHORT.get(g, g)


def official(path, month):
    ws = openpyxl.load_workbook(path, data_only=True, read_only=True).worksheets[0]
    it = ws.iter_rows(values_only=True)
    head = [str(h or "").strip() for h in next(it)]
    m = head.index(month)
    out = {}
    for r in it:
        if r[0] is None or not isinstance(r[m], (int, float)) or r[m] <= 0:
            continue
        out[str(r[0]).strip().zfill(9)] = {"desc": str(r[1] or "").strip(), "unit": str(r[2] or "").strip(), "price": float(r[m])}
    return out


def crawl(path, off):
    per, info = defaultdict(lambda: defaultdict(list)), {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        c = r["item_code"]
        if r["accepted"] != "yes" or c not in off:
            continue
        by_weight = bool(WEIGHT.search(off[c]["unit"]))
        v = (r.get("price_spec") or r.get("price")) if by_weight else r.get("price")
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        if v > 0:
            per[c][r["run_date"]].append(v)
            info[c] = {"group": r["cpi_group"], "title": r["title"], "retailer": r["retailer"], "basis": "unit of weight/volume" if by_weight else "shelf price"}
    return {c: (st.mean(st.mean(v) for v in days.values()), len(days)) for c, days in per.items()}, info


def main():
    off_path, month, crawl_path, out = sys.argv[1:5]
    off = official(off_path, month)
    cr, info = crawl(crawl_path, off)
    items = []
    for c, (avg, ndays) in cr.items():
        o = off[c]["price"]
        ratio = avg / o
        items.append({"code": c, "group": info[c]["group"], "desc": off[c]["desc"], "unit": off[c]["unit"], "official": o, "crawl": avg,
                      "diff": avg - o, "pct": (ratio - 1) * 100, "days": ndays, "far": not (1 / FAR <= ratio <= FAR),
                      "title": info[c]["title"], "retailer": info[c]["retailer"], "basis": info[c]["basis"]})
    groups = defaultdict(list)
    for x in items:
        groups[x["group"]].append(x)
    rows = []
    for g, xs in groups.items():
        ok = [x for x in xs if not x["far"]]
        if not ok:
            continue
        c_avg, o_avg = st.mean(x["crawl"] for x in ok), st.mean(x["official"] for x in ok)
        rows.append({"group": g, "n": len(ok), "excluded": len(xs) - len(ok), "crawl": c_avg, "official": o_avg, "diff": c_avg - o_avg,
                     "gap": (c_avg / o_avg - 1) * 100, "median": st.median(x["pct"] for x in ok), "days": st.mean(x["days"] for x in ok)})
    rows.sort(key=lambda r: -r["n"])
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "by_cpi_group"; ws.sheet_view.rightToLeft = True
    head = ["cpi_group", "matched_items", "crawl_oct_average_price_aed", "official_oct_avg_price_aed", "price_difference_aed",
            "group_average_gap_pct", "median_item_gap_pct", "average_days_observed", "items_left_out_(over_3x_apart)"]
    ws.append(head)
    for r in rows:
        ws.append([r["group"], r["n"], round(r["crawl"], 2), round(r["official"], 2), round(r["diff"], 2), round(r["gap"], 1), round(r["median"], 1), round(r["days"], 1), r["excluded"]])
    navy = PatternFill("solid", fgColor="14264B")
    for c in ws[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = navy; c.alignment = Alignment(wrap_text=True, vertical="center")
    for col, w in zip("ABCDEFGHI", (44, 10, 14, 14, 13, 13, 13, 11, 14)): ws.column_dimensions[col].width = w
    ws.freeze_panes = "B2"
    n = len(rows) + 1
    cs = wb.create_sheet("charts", 0)                     # the two charts on their own (left-to-right) sheet, first
    # chart 1: average price, crawl vs official, groups with an average under 100 AED (food, drinks, household goods)
    small = wb.create_sheet("chart_data_food"); small.sheet_view.rightToLeft = True
    en = {"يناير": "January", "فبراير": "February", "مارس": "March", "أبريل": "April", "مايو": "May", "يونيو": "June", "يوليو": "July", "أغسطس": "August", "سبتمبر": "September", "أكتوبر": "October", "نوفمبر": "November", "ديسمبر": "December"}.get(month, month)
    small.append(["cpi_group", "Scraped 12-29 Oct 2026 average price (AED)", f"Official {en} 2026 average price (AED)"])
    for r in sorted(rows, key=lambda r: r["group"]):
        if r["official"] < 100 and r["n"] >= 3:
            small.append([short(r["group"]), round(r["crawl"], 2), round(r["official"], 2)])
    ch = BarChart(); ch.type = "col"; ch.grouping = "clustered"; ch.height = 13; ch.width = 34
    ch.title = "Average item price by CPI group: scraped (12-29 Oct) vs official October"; ch.y_axis.title = "AED"; ch.x_axis.title = "CPI group"
    ch.add_data(Reference(small, min_col=2, max_col=3, min_row=1, max_row=small.max_row), titles_from_data=True)
    ch.set_categories(Reference(small, min_col=1, min_row=2, max_row=small.max_row))
    cs.add_chart(ch, "A1")
    # chart 2: gap in percent for every group
    gap = wb.create_sheet("chart_data_gap"); gap.sheet_view.rightToLeft = True
    gap.append(["cpi_group", "Median item gap: scraped vs official (%)"])
    for r in sorted(rows, key=lambda r: r["median"]):
        if r["n"] >= 3:
            gap.append([short(r["group"]), round(r["median"], 1)])
    c2 = BarChart(); c2.type = "bar"; c2.height = 14; c2.width = 34
    c2.title = "Median gap of scraped item prices against the official October prices, by CPI group (%, groups with 3+ items)"; c2.y_axis.title = "%"
    c2.add_data(Reference(gap, min_col=2, min_row=1, max_row=gap.max_row), titles_from_data=True)
    c2.set_categories(Reference(gap, min_col=1, min_row=2, max_row=gap.max_row))
    c2.legend = None
    cs.add_chart(c2, "A28")
    it = wb.create_sheet("items"); it.sheet_view.rightToLeft = True
    it.append(["item_code", "cpi_group", "official description", "official unit", f"official {month} (AED)", "scraped average (AED)", "difference (AED)",
               "gap %", "days observed", "price compared", "left out (over 3x apart)", "scraped product (last match)", "shop"])
    for x in sorted(items, key=lambda x: (x["group"], x["code"])):
        it.append([x["code"], x["group"], x["desc"], x["unit"], round(x["official"], 2), round(x["crawl"], 2), round(x["diff"], 2), round(x["pct"], 1),
                   x["days"], x["basis"], "yes" if x["far"] else "", x["title"], x["retailer"]])
        if x["far"]:
            it.cell(it.max_row, 11).fill = PatternFill("solid", fgColor="FCE4D6")
    for c in it[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = navy; c.alignment = Alignment(wrap_text=True)
    for col, w in zip("ABCDEFGHIJKLM", (11, 30, 34, 12, 11, 11, 11, 9, 8, 18, 10, 46, 10)): it.column_dimensions[col].width = w
    it.freeze_panes = "A2"; it.auto_filter.ref = it.dimensions
    me = wb.create_sheet("method"); me.sheet_view.rightToLeft = True
    for line in [f"المقارنة: متوسط سعر السلعة من السحب الآلي (12-29 أكتوبر 2026) مقابل متوسط السعر الرسمي لشهر {month}، لنفس رمز السلعة (9 أرقام).",
                 "سعر السحب للسلعة = متوسط الأيام، وكل يوم = متوسط المتاجر (الأسعار المقبولة فقط).",
                 "السعر يُقارن بنفس وحدة البيع الرسمية: إذا كانت الوحدة وزناً أو حجماً (غ، كغ، مل، لتر) يؤخذ سعر السحب محوّلاً لنفس الكمية؛ غير ذلك (حبة، عبوة، حزمة، عدد) يؤخذ سعر الرف كما هو.",
                 "سلعة سعرها في السحب أقل من ثلث أو أكثر من ثلاثة أضعاف السعر الرسمي تبقى في ورقة items مظللة، ولا تدخل في متوسطات المجموعات ولا الرسوم (غالباً منتج أو حجم مختلف طُوبق).",
                 "group_average_gap_pct = (متوسط السحب للمجموعة ÷ المتوسط الرسمي للمجموعة − 1) × 100. median_item_gap_pct = الوسيط لفرق السلع داخل المجموعة، أقل تأثراً بسلعة واحدة.",
                 "هذه مقارنة تجريبية لأسعار السلع، وليست رقماً قياسياً."]:
        me.append([line])
    me.column_dimensions["A"].width = 150
    wb.save(out)
    print(out, len(items), "items matched,", sum(x["far"] for x in items), "left out,", len(rows), "groups")
    for r in rows:
        print(f'{r["group"][:40]:40} n={r["n"]:3d} out={r["excluded"]:2d} crawl={r["crawl"]:9.2f} official={r["official"]:9.2f} gap={r["gap"]:6.1f}% median={r["median"]:6.1f}%')


if __name__ == "__main__":
    main()
