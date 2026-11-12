"""Add one more week to the month workbooks (weeks side by side, office layout) without rebuilding the earlier weeks.

usage: python3 add_month_week.py <week no> <tickets month.xlsx> <tickets week.xlsx> <packages month.xlsx> <packages week.xlsx>
                                 <tickets out.xlsx> <packages out.xlsx> "<tickets title>" "<packages title>"

Uses the same column blocks, notes column and cell comments as build_month_workbooks.py (DOM_BLOCK, FOR_BLOCK, PKG_COL); the
week's details, method and screenshot sheets are appended with the week in their name. No price is copied between weeks."""
import sys
import openpyxl
from openpyxl.comments import Comment
from openpyxl.styles import Alignment
import build_month_workbooks as B

W = int(sys.argv[1]) - 1
T_MONTH, T_WEEK, P_MONTH, P_WEEK, T_OUT, P_OUT, T_TITLE, P_TITLE = sys.argv[2:10]


def notes_col(ws, header_row):
    for c in range(1, ws.max_column + 1):
        if ws.cell(header_row, c).value == "ملاحظات":
            return c
    raise SystemExit(f"no notes column in {ws.title}")


def add_note(ws, r, col, c0, note):
    prev = ws.cell(r, col).value
    ws.cell(r, col).value = (prev + "\n" if prev else "") + f"أ{W + 1}: {note}"
    ws.cell(r, col).alignment = Alignment(wrap_text=True, vertical="top")
    ws.cell(r, c0).comment = Comment(str(note), "CPI")


def trip(ws, r, lo_c):
    lo, hi, av = B.L(lo_c), B.L(lo_c + 1), B.L(lo_c + 2)
    if ws[f"{lo}{r-2}"].value is not None and ws[f"{lo}{r-1}"].value is not None:
        ws[f"{lo}{r}"] = f"=SUM({lo}{r-2}:{lo}{r-1})"
        ws[f"{hi}{r}"] = f'=IF(AND({hi}{r-2}="",{hi}{r-1}=""),"",IF({hi}{r-2}="",{lo}{r-2},{hi}{r-2})+IF({hi}{r-1}="",{lo}{r-1},{hi}{r-1}))'
        ws[f"{av}{r}"] = f"=AVERAGE({lo}{r}:{hi}{r})"


def tickets():
    wb, src = openpyxl.load_workbook(T_MONTH), openpyxl.load_workbook(T_WEEK)
    dom, fore, sd, sf = wb.worksheets[0], wb.worksheets[1], src.worksheets[0], src.worksheets[1]
    dn, fn = notes_col(dom, 3), notes_col(fore, 2)
    c0 = B.DOM_BLOCK[W]
    dom.cell(1, c0).value = T_TITLE
    for (r, kind), (rs, _) in zip(B.leg_rows(dom, 4), B.leg_rows(sd, 4)):
        if str(dom.cell(r, 1).value or "").strip().lower() != str(sd.cell(rs, 1).value or "").strip().lower():
            raise SystemExit(f"domestic row mismatch {r}/{rs}")
        if kind == "leg":
            for i in (0, 1, 3, 4):
                dom.cell(r, c0 + i).value = sd.cell(rs, 3 + i).value
                if sd.cell(rs, 3 + i).fill.fgColor.rgb in ("00FFF2CC", "FFFFF2CC"):
                    dom.cell(r, c0 + i).fill = B.yellow
            if sd.cell(rs, 10).value:
                add_note(dom, r, dn, c0, sd.cell(rs, 10).value)
        else:
            trip(dom, r, c0); trip(dom, r, c0 + 3)
    c0 = B.FOR_BLOCK[W]
    fore.cell(1, c0).value = T_TITLE
    for (r, kind), (rs, _) in zip(B.leg_rows(fore, 3), B.leg_rows(sf, 3)):
        if kind == "leg":
            for i in (0, 1):
                fore.cell(r, c0 + i).value = sf.cell(rs, 3 + i).value
                if sf.cell(rs, 3 + i).fill.fgColor.rgb in ("00FFF2CC", "FFFFF2CC"):
                    fore.cell(r, c0 + i).fill = B.yellow
            if sf.cell(rs, 6).value and sf.cell(rs, 1).value:
                add_note(fore, r, fn, c0, sf.cell(rs, 6).value)
        else:
            trip(fore, r, c0)
    for name in src.sheetnames[2:]:
        B.copy_sheet(src[name], wb, f"{name} أ{W + 1}")
    wb.save(T_OUT)
    print("tickets ->", T_OUT, wb.sheetnames)


def packages():
    wb, src = openpyxl.load_workbook(P_MONTH), openpyxl.load_workbook(P_WEEK)
    ws, s = wb.worksheets[0], src.worksheets[0]
    c0 = B.PKG_COL[W]
    ws.cell(1, c0).value = P_TITLE
    for r in range(4, ws.max_row + 1):
        if not ws.cell(r, 1).value:
            continue
        if str(ws.cell(r, 1).value).strip().lower() != str(s.cell(r, 1).value or "").strip().lower():
            raise SystemExit(f"package row mismatch {r}")
        ws.cell(r, c0).value = s.cell(r, 3).value
        if s.cell(r, 3).fill.fgColor.rgb in ("00FFF2CC", "FFFFF2CC"):
            ws.cell(r, c0).fill = B.yellow
        if s.cell(r, 11).value:
            add_note(ws, r, 11, c0, s.cell(r, 11).value)
    for sh in src.worksheets[1:]:
        name = sh.title.replace("تفاصيل دناتا", "تفاصيل").replace("لقطات الشاشة", "لقطات")
        B.copy_sheet(sh, wb, f"{name} أ{W + 1}")
    wb.save(P_OUT)
    print("packages ->", P_OUT, wb.sheetnames)


tickets()
packages()
