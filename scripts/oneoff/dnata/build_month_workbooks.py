"""One workbook per survey for the month (week 1, week 2, week 3 ... side by side in the office's own layout), built from the
weekly workbooks already delivered.

usage: python3 build_month_workbooks.py <tickets template.xlsx> <packages template.xlsx> <out tickets.xlsx> <out packages.xlsx>

Weeks (November 2026):
  tickets   W1 out 1 / back 6 Nov, W2 6 / 13 Nov, W3 13 / 20 Nov   (domestic sheet: flydubai | Emirates; foreign: national carrier)
  packages  W1 1-5 Nov, W2 6-10 Nov, W3 13-17 Nov (4 nights; Bangkok and Kuala Lumpur as noted in each week's details)
Each week's numbers are copied from that week's delivered workbook (first block of its sheet); the notes go to a notes
column and to a comment on the week's cell; the weekly details, method and screenshot sheets are appended with the week
in their name."""
import copy, io, sys
import openpyxl
from openpyxl.comments import Comment
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Font, PatternFill, Alignment

EX = "/home/user/CPI-Web-Scarping/data/exports/"
TICKET_WEEKS = [
    ("الأسبوع الأول: ذهاب 1، عودة 6 نوفمبر", EX + "tickets_1-6_Nov_2026_airline_sites.xlsx", "محلي 1-6 نوفمبر (فلاي دبي)", "أجنبي 1-6 نوفمبر",
     ["تفاصيل الرحلات", "رحلات الأجنبي", "منهجية"]),
    ("الأسبوع الثاني: ذهاب 6، عودة 13 نوفمبر", EX + "tickets_6-13_Nov_2026.xlsx", 0, 1, ["الرحلات", "المنهجية"]),
    ("الأسبوع الثالث: ذهاب 13، عودة 20 نوفمبر", EX + "tickets_13-20_Nov_2026.xlsx", 0, 1, ["الرحلات", "المنهجية"]),
]
PKG_WEEKS = [
    ("الأسبوع الأول: 1-5 نوفمبر (4 ليالي)", EX + "dnata_packages_1-5_Nov_2026_4nights.xlsx", "نوفمبر 2026"),
    ("الأسبوع الثاني: 6-10 نوفمبر (4 ليالي)", EX + "dnata_packages_6-10_Nov_2026.xlsx", 0),
    ("الأسبوع الثالث: 13-17 نوفمبر (4 ليالي)", EX + "dnata_packages_13-17_Nov_2026.xlsx", 0),
]
DOM_BLOCK = [3, 10, 16, 22]          # C, J, P, V: flydubai lo/hi/ticket, Emirates lo/hi/ticket
FOR_BLOCK = [3, 7, 11, 15]           # C, G, K, O: lo / hi / average
PKG_COL = [3, 5, 7, 9]               # C, E, G, I: dnata (Emirates Holidays next to it)
L = openpyxl.utils.get_column_letter
yellow = PatternFill("solid", fgColor="FFF2CC")


def sheet(wb, ref):
    return wb.worksheets[ref] if isinstance(ref, int) else wb[ref]


def copy_sheet(src, wb, title):
    """Values, formats, widths, merges and pictures of one sheet into another workbook."""
    ws = wb.create_sheet(title[:31])
    ws.sheet_view.rightToLeft = src.sheet_view.rightToLeft
    for row in src.iter_rows():
        for c in row:
            if c.value is None and not c.has_style:
                continue
            n = ws.cell(c.row, c.column, c.value)
            if c.has_style:
                n.font, n.fill, n.border = copy.copy(c.font), copy.copy(c.fill), copy.copy(c.border)
                n.alignment, n.number_format = copy.copy(c.alignment), c.number_format
    for k, d in src.column_dimensions.items():
        ws.column_dimensions[k].width = d.width
    for k, d in src.row_dimensions.items():
        if d.height:
            ws.row_dimensions[k].height = d.height
    for m in src.merged_cells.ranges:
        ws.merge_cells(str(m))
    for img in src._images:
        new = XLImage(io.BytesIO(img._data()))
        new.width, new.height, new.anchor = img.width, img.height, img.anchor
        ws.add_image(new)
    return ws


def leg_rows(ws, first, label_col=2):
    """rows of the form (start row, kind) for every route: kind 'leg' or 'total' by the label in column B."""
    out = []
    for r in range(first, ws.max_row + 1):
        b = str(ws.cell(r, label_col).value or "").strip()
        if b in ("الذهاب", "العودة"):
            out.append((r, "leg"))
        elif b.startswith("الذهاب والعودة"):
            out.append((r, "total"))
    return out


def tickets(tpl, out):
    wb = openpyxl.load_workbook(tpl)
    dom, fore = wb.worksheets[0], wb.worksheets[1]
    dom_rows, for_rows = leg_rows(dom, 4), leg_rows(fore, 3)
    for r, _ in dom_rows:                                   # the template's own (manual) numbers leave: our weeks replace them
        for c in range(3, 28):
            dom.cell(r, c).value = None
    for r, _ in for_rows:
        for c in range(3, 18):
            fore.cell(r, c).value = None
    dom_note, for_note = dom.max_column + 2, fore.max_column + 2   # notes per week, right of the template
    dom.cell(3, dom_note).value = "ملاحظات"; fore.cell(2, for_note).value = "ملاحظات"
    for w, (title, path, dsh, fsh, extra) in enumerate(TICKET_WEEKS):
        src = openpyxl.load_workbook(path)
        sd, sf = sheet(src, dsh), sheet(src, fsh)
        dom.cell(1, DOM_BLOCK[w]).value = title; fore.cell(1, FOR_BLOCK[w] - (1 if w == 0 else 0)).value = title
        for (r, kind), (rs, _) in zip(dom_rows, leg_rows(sd, 4)):
            c0 = DOM_BLOCK[w]
            if kind == "leg":
                for i in (0, 1, 3, 4):                      # lo / hi of flydubai and of Emirates
                    v = sd.cell(rs, 3 + i).value
                    dom.cell(r, c0 + i).value = v
                    if sd.cell(rs, 3 + i).fill.fgColor.rgb in ("00FFF2CC", "FFFFF2CC"):
                        dom.cell(r, c0 + i).fill = yellow
            else:
                for j in (0, 3):                            # trip formulas, as in the weekly files
                    lo, hi, av = L(c0 + j), L(c0 + j + 1), L(c0 + j + 2)
                    if dom[f"{lo}{r-2}"].value is not None and dom[f"{lo}{r-1}"].value is not None:
                        dom[f"{lo}{r}"] = f"=SUM({lo}{r-2}:{lo}{r-1})"
                        dom[f"{hi}{r}"] = f'=IF(AND({hi}{r-2}="",{hi}{r-1}=""),"",IF({hi}{r-2}="",{lo}{r-2},{hi}{r-2})+IF({hi}{r-1}="",{lo}{r-1},{hi}{r-1}))'
                        dom[f"{av}{r}"] = f"=AVERAGE({lo}{r}:{hi}{r})"
            note = sd.cell(rs, 10).value                    # weekly note column J
            if note:
                prev = dom.cell(r, dom_note).value
                dom.cell(r, dom_note).value = (prev + "\n" if prev else "") + f"أ{w+1}: {note}"
                dom.cell(r, c0).comment = Comment(str(note), "CPI")
        for (r, kind), (rs, _) in zip(for_rows, leg_rows(sf, 3)):
            c0 = FOR_BLOCK[w]
            if kind == "leg":
                for i in (0, 1):
                    dom_v = sf.cell(rs, 3 + i).value
                    fore.cell(r, c0 + i).value = dom_v
                    if sf.cell(rs, 3 + i).fill.fgColor.rgb in ("00FFF2CC", "FFFFF2CC"):
                        fore.cell(r, c0 + i).fill = yellow
            else:
                lo, hi, av = L(c0), L(c0 + 1), L(c0 + 2)
                if fore[f"{lo}{r-2}"].value is not None and fore[f"{lo}{r-1}"].value is not None:
                    fore[f"{lo}{r}"] = f"=SUM({lo}{r-2}:{lo}{r-1})"
                    fore[f"{hi}{r}"] = f'=IF(AND({hi}{r-2}="",{hi}{r-1}=""),"",IF({hi}{r-2}="",{lo}{r-2},{hi}{r-2})+IF({hi}{r-1}="",{lo}{r-1},{hi}{r-1}))'
                    fore[f"{av}{r}"] = f"=AVERAGE({lo}{r}:{hi}{r})"
            note = sf.cell(rs, 6).value                     # weekly note column F
            if note:
                prev = fore.cell(r, for_note).value
                fore.cell(r, for_note).value = (prev + "\n" if prev else "") + f"أ{w+1}: {note}"
                fore.cell(r, c0).comment = Comment(str(note), "CPI")
        for name in extra:
            if name in src.sheetnames:
                copy_sheet(src[name], wb, f"{name} أ{w+1}")
    for ws, col in ((dom, dom_note), (fore, for_note)):
        ws.column_dimensions[L(col)].width = 70
        for r in range(1, ws.max_row + 1):
            ws.cell(r, col).alignment = Alignment(wrap_text=True, vertical="top")
    dom.title, fore.title = "الطيران المحلى", "الطيران الاجنبى"
    wb.save(out)
    print("tickets ->", out, wb.sheetnames)


def packages(tpl, out):
    wb = openpyxl.load_workbook(tpl)
    ws = wb.worksheets[0]
    ws.title = "نوفمبر 2026"
    rows = [r for r in range(4, ws.max_row + 1) if ws.cell(r, 1).value]
    for r in rows:
        for c in range(3, 12):
            ws.cell(r, c).value = None
    for w, (title, path, ref) in enumerate(PKG_WEEKS):
        src = openpyxl.load_workbook(path)
        s = sheet(src, ref)
        ws.cell(1, PKG_COL[w]).value = title
        by_name = {str(s.cell(r, 1).value).strip(): r for r in range(4, s.max_row + 1) if s.cell(r, 1).value}
        for r in rows:
            rs = by_name.get(str(ws.cell(r, 1).value).strip())
            if not rs:
                continue
            v = s.cell(rs, 3).value
            ws.cell(r, PKG_COL[w]).value = v
            if s.cell(rs, 3).fill.fgColor.rgb in ("00FFF2CC", "FFFFF2CC"):
                ws.cell(r, PKG_COL[w]).fill = yellow
            note = s.cell(rs, 11).value
            if note:
                prev = ws.cell(r, 11).value
                ws.cell(r, 11).value = (prev + "\n" if prev else "") + f"أ{w+1}: {note}"
                ws.cell(r, PKG_COL[w]).comment = Comment(str(note), "CPI")
        for i, sh in enumerate(src.worksheets):
            if i == (src.sheetnames.index(ref) if isinstance(ref, str) else ref) or sh.title.startswith("سبتمبر"):
                continue
            name = sh.title.replace("تفاصيل دناتا", "تفاصيل").replace("لقطات الشاشة", "لقطات")
            copy_sheet(sh, wb, f"{name} أ{w+1}" if f"أ{w+1}" not in name else name)
    ws.cell(3, 11).value = "ملاحظات"
    ws.column_dimensions["K"].width = 80
    for r in rows:
        ws.cell(r, 11).alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(out)
    print("packages ->", out, wb.sheetnames)


if __name__ == "__main__":
    t_tpl, p_tpl, t_out, p_out = sys.argv[1:5]
    tickets(t_tpl, t_out)
    packages(p_tpl, p_out)
