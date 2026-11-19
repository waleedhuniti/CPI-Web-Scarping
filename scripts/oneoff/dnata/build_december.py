"""December 2026 month files in the office layout: prices and screenshots only (no details, flights or method sheets).

usage: python3 build_december.py <week no 1-4> <office packages template.xlsx> <office tickets template.xlsx>
                                 <week packages.xlsx> <week tickets.xlsx> <packages out.xlsx> <tickets out.xlsx>
                                 "<packages week title>" "<tickets week title>"

Week 1 starts from the office templates with every price cleared; later weeks open the existing December files (when the
out file exists it is the base). The week's numbers come from that week's workbooks (write_pkg_week.py,
write_tickets_week.py); a week's notes become cell comments. Columns as in build_month_workbooks.py: packages dnata C/E/G/I
(Emirates Holidays next to it, left for the office), tickets flydubai C/J/P/V and Emirates F/M/S/Y, foreign C/G/K/O."""
import os, sys
import openpyxl
from openpyxl.comments import Comment
from openpyxl.styles import PatternFill
import build_month_workbooks as B

W = int(sys.argv[1]) - 1
P_TPL, T_TPL, P_WEEK, T_WEEK, P_OUT, T_OUT, P_TITLE, T_TITLE = sys.argv[2:10]
dec = lambda s: str(s).replace("نوفمبر", "ديسمبر")
NOFILL = PatternFill()


def unhide(ws):
    for d in ws.column_dimensions.values():
        if d.hidden:
            d.hidden = False
            d.width = max(d.width or 0, 11)


def packages():
    fresh = not os.path.exists(P_OUT)
    wb = openpyxl.load_workbook(P_TPL if fresh else P_OUT)
    ws = wb.worksheets[0]
    rows = [r for r in range(4, ws.max_row + 1) if ws.cell(r, 1).value]
    if fresh:
        for sh in wb.worksheets[1:]:
            wb.remove(sh)
        ws.title = "ديسمبر 2026"
        for r in rows:
            for c in range(3, 11):
                ws.cell(r, c).value = None; ws.cell(r, c).comment = None
            for c in range(11, 16):
                if not isinstance(ws.cell(r, c), openpyxl.cell.cell.MergedCell):
                    ws.cell(r, c).value = None
        for i, t in enumerate(("الأسبوع الأول", "الأسبوع الثاني", "الأسبوع الثالث", "الأسبوع الرابع")):
            ws.cell(1, B.PKG_COL[i]).value = t
        unhide(ws)
    src = openpyxl.load_workbook(P_WEEK); s = src.worksheets[0]
    c0 = B.PKG_COL[W]
    ws.cell(1, c0).value = P_TITLE
    for r in rows:
        if str(ws.cell(r, 1).value).strip().lower() != str(s.cell(r, 1).value or "").strip().lower():
            raise SystemExit(f"package row mismatch {r}")
        ws.cell(r, c0).value = s.cell(r, 3).value
        ws.cell(r, c0).fill = B.yellow if s.cell(r, 3).fill.fgColor.rgb in ("00FFF2CC", "FFFFF2CC") else NOFILL
        note = s.cell(r, 11).value
        ws.cell(r, c0).comment = Comment(dec(note), "CPI") if note else None
    for sh in src.worksheets:
        if sh.title.startswith("لقطات"):
            name = f"لقطات أ{W + 1}"
            if name in wb.sheetnames:
                wb.remove(wb[name])
            B.copy_sheet(sh, wb, name)
    wb.save(P_OUT)
    print("packages ->", P_OUT, wb.sheetnames)


def trip(ws, r, lo_c):
    lo, hi, av = B.L(lo_c), B.L(lo_c + 1), B.L(lo_c + 2)
    if ws[f"{lo}{r-2}"].value is not None and ws[f"{lo}{r-1}"].value is not None:
        ws[f"{lo}{r}"] = f"=SUM({lo}{r-2}:{lo}{r-1})"
        ws[f"{hi}{r}"] = f'=IF(AND({hi}{r-2}="",{hi}{r-1}=""),"",IF({hi}{r-2}="",{lo}{r-2},{hi}{r-2})+IF({hi}{r-1}="",{lo}{r-1},{hi}{r-1}))'
        ws[f"{av}{r}"] = f"=AVERAGE({lo}{r}:{hi}{r})"
    else:
        for c in (lo, hi, av):
            ws[f"{c}{r}"] = None


def tickets():
    fresh = not os.path.exists(T_OUT)
    wb = openpyxl.load_workbook(T_TPL if fresh else T_OUT)
    dom, fore = wb.worksheets[0], wb.worksheets[1]
    dom_rows, for_rows = B.leg_rows(dom, 4), B.leg_rows(fore, 3)
    if fresh:
        for sh in wb.worksheets[2:]:
            wb.remove(sh)
        for r, _ in dom_rows:
            for c in range(3, 28):
                dom.cell(r, c).value = None; dom.cell(r, c).comment = None; dom.cell(r, c).fill = NOFILL
        for r, _ in for_rows:
            for c in range(3, 21):
                fore.cell(r, c).value = None; fore.cell(r, c).comment = None; fore.cell(r, c).fill = NOFILL
        unhide(dom); unhide(fore)
    src = openpyxl.load_workbook(T_WEEK); sd, sf = src.worksheets[0], src.worksheets[1]
    c0 = B.DOM_BLOCK[W]
    dom.cell(1, c0).value = T_TITLE
    for (r, kind), (rs, _) in zip(dom_rows, B.leg_rows(sd, 4)):
        if kind == "leg":
            for i in (0, 1, 3, 4):
                dom.cell(r, c0 + i).value = sd.cell(rs, 3 + i).value
                dom.cell(r, c0 + i).fill = B.yellow if sd.cell(rs, 3 + i).fill.fgColor.rgb in ("00FFF2CC", "FFFFF2CC") else NOFILL
            note = sd.cell(rs, 10).value
            dom.cell(r, c0).comment = Comment(dec(note), "CPI") if note else None
        else:
            trip(dom, r, c0); trip(dom, r, c0 + 3)
    c0 = B.FOR_BLOCK[W]
    fore.cell(1, c0 - (1 if W == 0 else 0)).value = T_TITLE
    for (r, kind), (rs, _) in zip(for_rows, B.leg_rows(sf, 3)):
        if kind == "leg":
            for i in (0, 1):
                fore.cell(r, c0 + i).value = sf.cell(rs, 3 + i).value
                fore.cell(r, c0 + i).fill = B.yellow if sf.cell(rs, 3 + i).fill.fgColor.rgb in ("00FFF2CC", "FFFFF2CC") else NOFILL
            note = sf.cell(rs, 6).value
            fore.cell(r, c0).comment = Comment(dec(note), "CPI") if note and sf.cell(rs, 1).value else None
        else:
            trip(fore, r, c0)
    wb.save(T_OUT)
    print("tickets ->", T_OUT, wb.sheetnames)


if P_WEEK != "-": packages()
if T_WEEK != "-": tickets()
