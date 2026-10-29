"""How much of each activity (SPPI total, section H/J, 2-, 3- and 4-digit ISIC) the companies reachable online cover.

A company is classed by the best availability among its products: Scraping (at least one price collected
automatically), Online فقط (none collected, but at least one shown online), otherwise الاستمارة (survey form).
Its weight is its adjusted production in the frame (the sample's weights add up to the full frame), and it counts
towards the activity of its REGISTERED 4-digit code. A company classed Scraping may still need the form for some of
its products (e.g. an airline whose fares are only in the booking engine): the per-company sheet shows how many.
"""
from collections import Counter, defaultdict

SCRAPING, ONLINE, FORM = "Scraping", "Online فقط", "الاستمارة"
LEVEL_AR = {"total": "الإجمالي", "section": "القسم", "2-digit": "المستوى الثاني (رقمان)",
            "3-digit": "المستوى الثالث (3 أرقام)", "4-digit": "المستوى الرابع (4 أرقام)"}
PRODUCT_TO_CLASS = {"Scraping": SCRAPING, "Online فقط": ONLINE}


def company_classes(product_rows: list[dict]) -> dict:
    """ser -> (class, Counter of product availabilities)."""
    by = defaultdict(Counter)
    for p in product_rows:
        by[p["ser"]][p["availability"]] += 1
    out = {}
    for ser, c in by.items():
        cls = SCRAPING if c["Scraping"] else ONLINE if c["Online فقط"] else FORM
        out[ser] = (cls, c)
    return out


def _fnum(v) -> float:
    try:
        return float(v or 0)
    except ValueError:
        return 0.0


def company_rows(companies: dict, classes: dict, total: float) -> list[dict]:
    rows = []
    for ser, c in companies.items():
        cls, counts = classes.get(ser, (FORM, Counter()))
        prod = _fnum(c.get("production_adjusted"))
        rows.append(dict(ser=ser, section=c.get("section", ""), isic=str(c.get("isic", "")),
                         company=c.get("name_en") or c.get("name_ar", ""), collection=cls,
                         n_scraping=counts["Scraping"], n_online=counts["Online فقط"],
                         n_form=counts["لا هذا ولا ذاك"], production_adjusted=round(prod, 2),
                         weight=round(prod / total * 100, 4) if total else 0))
    return sorted(rows, key=lambda r: -r["production_adjusted"])


def activity_rows(activities: list[dict], comp_rows: list[dict]) -> list[dict]:
    """One row per activity of the frame, in frame order."""
    total = next((_fnum(a["production_adjusted"]) for a in activities if a["level"] == "total"), 0.0)
    rows = []
    for a in activities:
        code, level = a["code"], a["level"]
        if level == "total":
            members = comp_rows
        elif level == "section":
            members = [c for c in comp_rows if c["section"] == code]
        else:
            members = [c for c in comp_rows if c["isic"].startswith(code)]
        act_prod = _fnum(a["production_adjusted"])
        prod = {k: sum(c["production_adjusted"] for c in members if c["collection"] == k)
                for k in (SCRAPING, ONLINE, FORM)}
        n = Counter(c["collection"] for c in members)
        covered = prod[SCRAPING] + prod[ONLINE]
        share = (lambda v: round(v / act_prod * 100, 2) if act_prod else 0.0)
        name_ar = a.get("name_ar") or ("إجمالي SPPI (H + J)" if level == "total" else "")
        rows.append(dict(code=code, level=level, level_ar=LEVEL_AR.get(level, level), name_ar=name_ar,
                         name_en=a.get("name_en", ""),
                         weight=round(act_prod / total * 100, 4) if total else 0, n_companies=len(members),
                         n_scraping=n[SCRAPING], n_online=n[ONLINE], n_form=n[FORM],
                         weight_scraping=round(prod[SCRAPING] / total * 100, 4) if total else 0,
                         weight_online=round(prod[ONLINE] / total * 100, 4) if total else 0,
                         weight_form=round(prod[FORM] / total * 100, 4) if total else 0,
                         share_scraping=share(prod[SCRAPING]), share_online=share(prod[ONLINE]),
                         share_online_total=share(covered), share_form=share(prod[FORM]),
                         has_online="نعم" if covered > 0 else "لا",
                         check_sum=round(sum(prod.values()) - act_prod, 2)))
    return rows


def summary_lines(act_rows: list[dict]) -> list[str]:
    """Short Arabic summary for the coverage sheet."""
    total = next(r for r in act_rows if r["level"] == "total")
    divs = [r for r in act_rows if r["level"] == "2-digit"]
    with_online = [r for r in divs if r["has_online"] == "نعم"]
    lines = [
        f"الإجمالي: Scraping {total['share_scraping']:.2f}% ، Online فقط {total['share_online']:.2f}% ، "
        f"المجموع أونلاين {total['share_online_total']:.2f}% ، الاستمارة {total['share_form']:.2f}% من وزن SPPI.",
        f"الأنشطة على المستوى الثاني (رقمين): {len(with_online)} من {len(divs)} فيها شركة واحدة على الأقل أسعارها أونلاين.",
    ]
    no_online = [f"{r['code']} {r['name_ar']}" for r in divs if r["has_online"] == "لا"]
    if no_online:
        lines.append("أنشطة بلا أي تغطية أونلاين (الاستمارة فقط): " + "، ".join(no_online))
    lines += [
        "تصنيف الشركة حسب أفضل منتج لديها: Scraping إذا جُمع سعر واحد على الأقل آلياً، Online فقط إذا لم يُجمع شيء "
        "لكن السعر يظهر أونلاين، وإلا الاستمارة. وزن الشركة = إنتاجها المعدّل، ويُحسب ضمن نشاطها المسجّل (4 أرقام).",
        "تنبيه: شركة مصنفة Scraping قد تحتاج الاستمارة لبعض منتجاتها (انظر ورقة 'التغطية - الشركات': عدد المنتجات "
        "في كل طريقة). مثال: تذاكر الطيران تظهر فقط في محرك الحجز.",
    ]
    return lines
