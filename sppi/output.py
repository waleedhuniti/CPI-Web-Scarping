"""Run outputs: tidy CSVs (English headers) and one Excel workbook for the officer (Arabic, RTL, Arial, #283593)."""
import csv
from pathlib import Path

PRICE_COLS = ["run_date", "ser", "company", "source_id", "item", "spec", "price", "currency", "unit", "price_type",
              "vat", "effective_date", "price_text", "source_url", "fetched_at", "http_status", "status", "snapshot",
              "sha256", "note"]
MENTION_COLS = ["run_date", "ser", "company", "source_id", "source_url", "where", "currency", "amount", "snippet"]
SOURCE_COLS = ["source_id", "ser", "company", "url", "final_url", "http_status", "robots", "outcome", "n_prices",
               "n_mentions", "seconds", "fetched_at", "snapshot", "sha256", "note"]
FETCH_COLS = ["url", "final_url", "redirects", "mode", "http_status", "robots", "outcome", "fetched_at", "seconds",
              "bytes", "sha256", "note"]

ARABIC = {
    "run_date": "تاريخ التشغيل", "ser": "رقم المنشأة", "company": "الشركة", "source_id": "المصدر", "item": "البند",
    "spec": "المواصفة", "price": "السعر", "currency": "العملة", "unit": "الوحدة", "price_type": "نوع السعر",
    "vat": "الضريبة", "effective_date": "تاريخ السريان", "price_text": "نص السعر كما ورد", "source_url": "رابط المصدر",
    "fetched_at": "وقت الجلب (UTC)", "http_status": "حالة HTTP", "status": "طريقة الاستخراج", "snapshot": "اللقطة المحفوظة",
    "sha256": "بصمة sha256", "note": "ملاحظات", "where": "الموضع", "amount": "المبلغ", "snippet": "النص المحيط",
    "url": "الرابط", "final_url": "الرابط النهائي", "robots": "robots.txt", "outcome": "النتيجة", "n_prices": "عدد الأسعار",
    "n_mentions": "إشارات أسعار", "seconds": "الزمن (ث)", "redirects": "إعادات التوجيه", "mode": "طريقة الجلب",
    "bytes": "الحجم (بايت)",
}

SHEETS = [("الأسعار", "prices", PRICE_COLS), ("ملخص المصادر", "sources", SOURCE_COLS),
          ("إشارات الأسعار", "mentions", MENTION_COLS), ("سجل الجلب", "fetch_log", FETCH_COLS)]

HEADER_COLOR = "283593"


def write_csv(path: Path, cols: list[str], rows: list[dict]):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_xlsx(path: Path, tables: dict, method_lines: list[str]):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    wb.remove(wb.active)
    head_font = Font(name="Arial", bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor=HEADER_COLOR)
    body_font = Font(name="Arial")
    for title, key, cols in SHEETS:
        ws = wb.create_sheet(title)
        ws.sheet_view.rightToLeft = True
        ws.append([ARABIC.get(c, c) for c in cols])
        for cell in ws[1]:
            cell.font, cell.fill = head_font, head_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for row in tables[key]:
            ws.append([row.get(c, "") for c in cols])
        for r in ws.iter_rows(min_row=2):
            for cell in r:
                cell.font = body_font
        for i, c in enumerate(cols, 1):
            longest = max([len(str(ws.cell(row=j, column=i).value or "")) for j in range(1, min(ws.max_row, 300) + 1)])
            ws.column_dimensions[get_column_letter(i)].width = min(max(10, longest + 2), 60)
        if "price" in cols:
            col = get_column_letter(cols.index("price") + 1)
            for cell in ws[col][1:]:
                cell.number_format = "#,##0.00####"
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
    ws = wb.create_sheet("المنهجية")
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 140
    for line in method_lines:
        ws.append([line])
    for r in ws.iter_rows():
        for cell in r:
            cell.font = body_font
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws["A1"].font = Font(name="Arial", bold=True, color="FFFFFF")
    ws["A1"].fill = head_fill
    wb.save(path)
