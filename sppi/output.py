"""Run outputs: tidy CSVs (English headers) and one Excel workbook for the officer (Arabic, RTL, Arial, #283593)."""
import csv
from pathlib import Path

PRICE_COLS = ["run_date", "ser", "section", "company", "isic_registered", "red", "type", "product_id", "product",
              "isic_product", "in_sample", "item", "spec", "price", "currency", "unit", "price_type", "vat",
              "effective_date", "price_text", "source_url", "fetched_at", "http_status", "status", "page_id",
              "snapshot", "sha256", "note"]
PRODUCT_COLS = ["product_id", "ser", "section", "company", "isic_registered", "red", "type", "product",
                "isic_product", "isic_product_name", "availability", "verified", "n_prices", "currency",
                "price_range", "price_sources", "reason", "source_url"]
PAGE_COLS = ["page_id", "ser", "section", "company", "availability", "url", "final_url", "parser", "http_status",
             "robots", "outcome", "n_raw", "n_prices", "n_mentions", "seconds", "fetched_at", "note"]
MENTION_COLS = ["run_date", "ser", "section", "company", "page_id", "source_url", "where", "currency", "amount",
                "snippet"]
FETCH_COLS = ["page_id", "ser", "section", "company", "availability", "url", "final_url", "redirects", "mode",
              "http_status", "robots", "outcome", "fetched_at", "seconds", "bytes", "sha256", "note"]

ARABIC = {
    "run_date": "تاريخ التشغيل", "ser": "الرقم المتسلسل", "section": "القسم (H/J)", "company": "الشركة",
    "isic_registered": "رمز النشاط المسجّل", "red": "ضمن الحمراء؟", "type": "النوع", "product_id": "رقم البند",
    "product": "اسم المنتج / الخدمة", "isic_product": "رمز ISIC الفعلي للبند", "isic_product_name": "اسم النشاط الفعلي",
    "in_sample": "ضمن قائمة المنتجات؟", "item": "البند كما ورد في الصفحة", "spec": "المواصفة", "price": "السعر",
    "currency": "العملة", "unit": "الوحدة", "price_type": "نوع السعر", "vat": "الضريبة",
    "effective_date": "تاريخ السريان", "price_text": "نص السعر كما ورد", "source_url": "رابط المصدر",
    "fetched_at": "وقت الجلب (UTC)", "http_status": "حالة HTTP", "status": "طريقة الاستخراج", "page_id": "الصفحة",
    "snapshot": "اللقطة المحفوظة", "sha256": "بصمة sha256", "note": "ملاحظات",
    "availability": "إمكانية الحصول على السعر", "verified": "تم التحقق", "n_prices": "عدد الأسعار",
    "price_range": "نطاق السعر", "price_sources": "مصادر السعر", "reason": "السبب / الملاحظة",
    "url": "الرابط", "final_url": "الرابط النهائي", "parser": "المحلل", "robots": "robots.txt", "outcome": "النتيجة",
    "n_raw": "مبالغ مستخرجة", "n_mentions": "إشارات أسعار", "seconds": "الزمن (ث)", "where": "الموضع",
    "amount": "المبلغ", "snippet": "النص المحيط", "redirects": "إعادات التوجيه", "mode": "طريقة الجلب",
    "bytes": "الحجم (بايت)",
}

SHEETS = [("المنتجات", "products", PRODUCT_COLS), ("الأسعار", "prices", PRICE_COLS),
          ("ملخص الصفحات", "pages", PAGE_COLS), ("سجل الجلب", "fetch_log", FETCH_COLS),
          ("إشارات الأسعار", "mentions", MENTION_COLS)]
CSV_NAMES = {"products": "products_availability.csv", "prices": "prices.csv", "pages": "pages.csv",
             "fetch_log": "fetch_log.csv", "mentions": "price_mentions.csv"}

HEADER_COLOR = "283593"
AVAIL_COLORS = {"Scraping": "C8E6C9", "Online فقط": "FFF3C4", "لا هذا ولا ذاك": "F5F5F5"}


def write_csv(path: Path, cols: list[str], rows: list[dict]):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_tables(run_dir: Path, run_date: str, tables: dict, method_lines: list[str]):
    for _, key, cols in SHEETS:
        write_csv(run_dir / CSV_NAMES[key], cols, tables[key])
    write_xlsx(run_dir / f"SPPI_HJ_prices_{run_date}.xlsx", tables, method_lines)


def write_xlsx(path: Path, tables: dict, method_lines: list[str]):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    wb.remove(wb.active)
    head_font = Font(name="Arial", bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor=HEADER_COLOR)
    body_font = Font(name="Arial")
    fills = {k: PatternFill("solid", fgColor=v) for k, v in AVAIL_COLORS.items()}
    for title, key, cols in SHEETS:
        ws = wb.create_sheet(title)
        ws.sheet_view.rightToLeft = True
        ws.append([ARABIC.get(c, c) for c in cols])
        for cell in ws[1]:
            cell.font, cell.fill = head_font, head_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for row in tables[key]:
            ws.append([row.get(c, "") for c in cols])
        avail_col = cols.index("availability") + 1 if "availability" in cols else None
        for r in ws.iter_rows(min_row=2):
            for cell in r:
                cell.font = body_font
            if avail_col and r[avail_col - 1].value in fills:
                r[avail_col - 1].fill = fills[r[avail_col - 1].value]
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
