import json, glob, os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

docs = []
for f in glob.glob("all/days/*.json"):
    d = json.load(open(f)); d = d if "rows" in d else d.get("data", d)
    if "rows" in d and "run_date" in d: docs.append(d)
docs.sort(key=lambda d: d["run_date"])
HDR = ["Run Date","Category","Commodity","Unit","Price","Change","Change (%)","Weekly (%)","Monthly (%)","YTD (%)","YoY (%)","Price Date"]
FMT = [None,None,None,None,"#,##0.00","#,##0.00;-#,##0.00","0.00","0.00","0.00","0.00","0.00",None]
W = [12,13,24,16,12,11,11,11,11,10,10,12]
wb = Workbook(); wb.remove(wb.active)

def sheet(name, ds):
    ws = wb.create_sheet(name); ws.append(HDR)
    for d in ds:
        for r in d["rows"]: ws.append([d["run_date"]] + r)
    for c in ws[1]:
        c.font = Font(name="Arial", bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F4E78"); c.alignment = Alignment(horizontal="center")
    for row in ws.iter_rows(min_row=2):
        for c, f in zip(row, FMT):
            c.font = Font(name="Arial")
            if f: c.number_format = f
    for i, w in enumerate(W, 1): ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions

sheet("All Days", docs)
for d in reversed(docs): sheet(d["run_date"], [d])
ws = wb.create_sheet("Notes")
for line in ["Source: Trading Economics commodities page (https://tradingeconomics.com/commodities)",
             "% columns are percentage points as shown on the site (e.g. -0.73 = -0.73%).",
             "Run Date = Dubai date of capture; Price Date = date of the quoted price."]:
    ws.append([line]); ws.cell(ws.max_row, 1).font = Font(name="Arial")
os.makedirs("/mnt/user-data/outputs", exist_ok=True)
out = "/mnt/user-data/outputs/Commodity_Price_Log.xlsx"
wb.save(out)
print(out, len(docs), "days", sum(len(d["rows"]) for d in docs), "rows")
