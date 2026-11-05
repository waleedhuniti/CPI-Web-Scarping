"""SPPI sample (extended shape, build brief section 9 + 14.6) from the November month workbooks and the weekly workbooks they
were built from.

usage: python3 -I build_sppi_sample.py <out.json>

Numbers come from the month workbooks (data/exports/tickets_Nov_2026_weeks_1-3.xlsx, dnata_packages_Nov_2026_weeks_1-3.xlsx),
read by column POSITION with DOM_BLOCK / FOR_BLOCK / PKG_COL parsed from scripts/oneoff/dnata/build_month_workbooks.py.
Leg notes, flight details, matched hotels, boards, stay dates and blocked reasons come from the weekly workbooks listed in that
script. Legs only (no totals). No price is ever copied from one week or outlet to another.
"""
import datetime as dt
import json
import re
import sys

import openpyxl

REPO = "/home/user/CPI-Web-Scarping/"
EX = REPO + "data/exports/"
MONTH_T = EX + "tickets_Nov_2026_weeks_1-3.xlsx"
MONTH_P = EX + "dnata_packages_Nov_2026_weeks_1-3.xlsx"

# ---- column map, parsed from the month builder so the two never drift ---------------------------------------------------
_src = open(REPO + "scripts/oneoff/dnata/build_month_workbooks.py", encoding="utf-8").read()
def _const(name):
    return json.loads(re.search(rf"^{name}\s*=\s*(\[[^\]]*\])", _src, re.M).group(1))
DOM_BLOCK, FOR_BLOCK, PKG_COL = _const("DOM_BLOCK"), _const("FOR_BLOCK"), _const("PKG_COL")
assert DOM_BLOCK == [3, 10, 16, 22] and FOR_BLOCK == [3, 7, 11, 15] and PKG_COL == [3, 5, 7, 9], (DOM_BLOCK, FOR_BLOCK, PKG_COL)
DOM_NOTE_W, FOR_NOTE_W, PKG_NOTE_W = 10, 6, 11          # weekly note columns J / F / K (as the month builder reads them)

YELLOW = ("00FFF2CC", "FFFFF2CC")

WEEKS = [
    dict(id="2026-11-W1", n=1, out="2026-11-01", back="2026-11-06", checkin="2026-11-01", checkout="2026-11-05", collected="2026-10-22",
         t_file=EX + "tickets_1-6_Nov_2026_airline_sites.xlsx", t_dom="محلي 1-6 نوفمبر (فلاي دبي)", t_for="أجنبي 1-6 نوفمبر",
         t_det_dom="تفاصيل الرحلات", t_det_for="رحلات الأجنبي", t_method="منهجية",
         p_file=EX + "dnata_packages_1-5_Nov_2026_4nights.xlsx", p_sheet="نوفمبر 2026", p_det="تفاصيل دناتا 1-5 نوفمبر", p_method="المنهجية"),
    dict(id="2026-11-W2", n=2, out="2026-11-06", back="2026-11-13", checkin="2026-11-06", checkout="2026-11-10", collected="2026-10-29",
         t_file=EX + "tickets_6-13_Nov_2026.xlsx", t_dom=0, t_for=1, t_det_dom=None, t_det_for="الرحلات", t_method="المنهجية",
         p_file=EX + "dnata_packages_6-10_Nov_2026.xlsx", p_sheet=0, p_det="تفاصيل دناتا 6-10 نوفمبر", p_method="المنهجية"),
    dict(id="2026-11-W3", n=3, out="2026-11-13", back="2026-11-20", checkin="2026-11-13", checkout="2026-11-17", collected="2026-11-05",
         t_file=EX + "tickets_13-20_Nov_2026.xlsx", t_dom=0, t_for=1, t_det_dom=None, t_det_for="الرحلات", t_method="المنهجية",
         p_file=EX + "dnata_packages_13-17_Nov_2026.xlsx", p_sheet=0, p_det="تفاصيل دناتا 13-17 نوفمبر", p_method="المنهجية"),
]

# ---- basket ---------------------------------------------------------------------------------------------------------------
OUTLETS = [  # code, name_en, name_ar (as the workbooks write it), kind, market, url, access
    ("flydubai", "flydubai", "فلاي دبي", "airline", "domestic", "https://www.flydubai.com/", "auto"),
    ("emirates", "Emirates", "الإماراتية", "airline", "domestic", "https://www.emirates.com/ae/english/", "pc_only"),
    ("saudia", "Saudia", "الخطوط السعودية", "airline", "foreign", "https://www.saudia.com/en-AE", "auto"),
    ("egyptair", "EgyptAir", "مصر للطيران", "airline", "foreign", "https://www.egyptair.com/", "auto"),
    ("rj", "Royal Jordanian", "الملكية الأردنية", "airline", "foreign", "https://www.rj.com/en", "auto"),
    ("pia", "PIA", "الخطوط الباكستانية", "airline", "foreign", "https://book-pia.crane.aero/", "auto"),
    ("ba", "British Airways", "الخطوط البريطانية", "airline", "foreign", "https://www.britishairways.com/", "auto"),
    ("airindia", "Air India", "طيران الهند", "airline", "foreign", "https://www.airindia.com/", "manual"),
    ("turkish", "Turkish Airlines", "الخطوط التركية", "airline", "foreign", "https://www.turkishairlines.com/en-ae/", "manual"),
    ("dnata", "dnata Travel", "دناتا", "travel_agent", None, "https://www.dnatatravel.com/", "auto"),
    ("ekholidays", "Emirates Holidays", "الإماراتية للعطلات", "tour_operator", None, "https://www.emiratesholidays.com/", "manual"),
]
OUTLET_AR = {o[0]: o[2] for o in OUTLETS}

# route key (lower-case token found in the sheet's column A label) -> item fields
ROUTES = {
    "delhi": ("DEL", "India - Delhi", "الهند - دلهي", "Delhi", "India"),
    "london": ("LHR", "UK - London", "بريطانيا - لندن", "London", "United Kingdom"),
    "riyadh": ("RUH", "Saudi Arabia - Riyadh", "السعودية - الرياض", "Riyadh", "Saudi Arabia"),
    "karachi": ("KHI", "Pakistan - Karachi", "باكستان - كراتشي", "Karachi", "Pakistan"),
    "isb": ("ISB", "Pakistan - Islamabad (ISB)", "باكستان - إسلام آباد", "Islamabad", "Pakistan"),
    "new york": ("JFK", "USA - New York", "الولايات المتحدة - نيويورك", "New York", "USA"),
    "colombo": ("CMB", "Sri Lanka - Colombo", "سريلانكا - كولومبو", "Colombo", "Sri Lanka"),
    "bangkok": ("BKK", "Thailand - Bangkok", "تايلاند - بانكوك", "Bangkok", "Thailand"),
    "istanbul": ("IST", "Turkey - Istanbul", "تركيا - إسطنبول", "Istanbul", "Turkey"),
    "cairo": ("CAI", "Egypt - Cairo", "مصر - القاهرة", "Cairo", "Egypt"),
    "alexandria": ("ALY", "Egypt - Alexandria", "مصر - الإسكندرية", "Alexandria", "Egypt"),
    "amman": ("AMM", "Jordan - Amman", "الأردن - عمان", "Amman", "Jordan"),
}
# who sells which route, as scripts/oneoff/dnata/write_tickets_week.py does it (FZ / EK maps; foreign: one national carrier)
FZ_ROUTES = {"delhi", "riyadh", "karachi", "colombo", "istanbul", "alexandria", "amman"}
EK_ROUTES = {"delhi", "london", "riyadh", "karachi", "new york", "colombo", "bangkok", "istanbul", "cairo", "amman"}
FOREIGN = {"delhi": "airindia", "london": "ba", "riyadh": "saudia", "isb": "pia", "istanbul": "turkish", "cairo": "egyptair",
           "amman": "rj"}
DETAIL_AIRLINE = {"فلاي دبي": "flydubai", "الإماراتية": "emirates", "الخطوط السعودية": "saudia", "مصر للطيران": "egyptair",
                  "الملكية الأردنية": "rj", "الخطوط الباكستانية": "pia", "الخطوط البريطانية": "ba", "طيران الهند": "airindia",
                  "الخطوط التركية": "turkish"}

# A hotel the workbook itself calls "a different hotel / another branch" in one week is the same substitute in the other
# weeks that match the same dnata property. One case has no note at all and is flagged here (reported in meta.build_notes).
EXTRA_OTHER_HOTEL = {("H05", "2026-11-W3"): "dnata matched Dosso Dossi Hotel Sultanahmet, not the basket's Golden Horn "
                                            "(no note in the workbook; flagged by the sample build)"}
# W3 Summer Island: the delivered workbooks have neither a price nor a note; the W3 run result says why.
EXTRA_PKG_NOTE = {("H22", "2026-11-W3"): "hotel not found on dnata for these dates (run result "
                                          "scripts/oneoff/dnata/runs_13_20/pkg_main.json; no note in the delivered workbook)"}

COLLECTION = {"frequency": "monthly", "lead_days": None, "note": "to be determined"}


def num(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return int(v) if float(v).is_integer() else float(v)
    raise ValueError(f"not a number: {v!r}")


def sheet(wb, ref):
    return wb.worksheets[ref] if isinstance(ref, int) else wb[ref]


def is_yellow(c):
    return c.fill is not None and c.fill.fgColor is not None and c.fill.fgColor.rgb in YELLOW


def route_key(label):
    a = str(label or "").lower()
    hits = [k for k in ROUTES if k in a]
    assert len(hits) == 1, (label, hits)
    return hits[0]


def leg_blocks(ws, first):
    """[(route key, out row)] for every route block: column B 'الذهاب' then 'العودة' (then the total row, not read)."""
    out = []
    for r in range(first, ws.max_row + 1):
        if str(ws.cell(r, 2).value or "").strip() == "الذهاب" and ws.cell(r, 1).value:
            assert str(ws.cell(r + 1, 2).value or "").strip() == "العودة", r
            out.append((route_key(ws.cell(r, 1).value), r))
    return out


def segs(text):
    return [s.strip() for s in str(text or "").split(" · ") if s.strip()]


def clean_dep(v):
    s = str(v or "").strip()
    m = re.match(r"\d{4}-\d{2}-\d{2}[ T](\d{2}:\d{2})", s)
    return m.group(1) if m else s


# ---- status rules (5.1 vocabulary; every rule is a phrase the workbooks use) ----------------------------------------------
BLOCK_WORDS = ("يحجب", "تحجب", "يرفض", "تحقق", "Cloudflare", "محجوب", "Access Denied", "403")
FAILED_WORDS = ("لم يكتمل السحب", "لم يستجب")


def ticket_status(lo, hi, note):
    if lo is not None:
        if "يُراجع" in note:
            return "to_review"
        if hi is None and "أقل سعر للذهاب فقط" in note:
            return "partial"
        return "ok"
    if any(w in note for w in FAILED_WORDS):
        return "failed"
    if any(w in note for w in BLOCK_WORDS):
        return "blocked"
    if "لا توجد رحلات" in note:
        return "not_available"
    raise ValueError(f"no price and no reason: lo={lo} hi={hi} note={note!r}")


def build():
    report = {"mismatch": [], "build_notes": []}
    mt = openpyxl.load_workbook(MONTH_T)
    mdom, mfor = mt.worksheets[0], mt.worksheets[1]
    mp = openpyxl.load_workbook(MONTH_P)
    mpkg = mp.worksheets[0]

    dom_blocks, for_blocks = leg_blocks(mdom, 4), leg_blocks(mfor, 3)
    assert len(dom_blocks) == 11 and len(for_blocks) == 7, (len(dom_blocks), len(for_blocks))

    # ---- items ----------------------------------------------------------------------------------------------------------
    items, sort = [], 0
    for market, blocks, prefix in (("domestic", dom_blocks, "TD"), ("foreign", for_blocks, "TF")):
        for key, r in blocks:
            iata, en, ar, city, country = ROUTES[key]
            sort += 1
            items.append(dict(code=f"{prefix}-{iata}", kind="route", market=market, name_en=en, name_ar=ar, city=city,
                              country=country, stars=None, board_rule=None, sort=sort, status="active",
                              source_label=str((mdom if market == "domestic" else mfor).cell(r, 1).value).strip(),
                              collection=dict(COLLECTION)))
    route_code = {(i["market"], route_key(i["source_label"])): i["code"] for i in items}

    w1 = openpyxl.load_workbook(WEEKS[0]["p_file"])
    det1 = w1[WEEKS[0]["p_det"]]
    hdr1 = {str(c.value).strip(): c.column for c in det1[1] if c.value}
    det1_rows = {int(det1.cell(r, 1).value): r for r in range(2, det1.max_row + 1) if det1.cell(r, 1).value}
    hotel_rows = [r for r in range(4, mpkg.max_row + 1) if mpkg.cell(r, 1).value]
    assert len(hotel_rows) == 28, len(hotel_rows)
    hotels = {}
    for r in hotel_rows:
        dr = det1_rows[r]
        name_en = str(det1.cell(dr, hdr1["الفندق بالملف"]).value).strip()
        b = str(mpkg.cell(r, 2).value or "").strip().replace("\xa0", " ")
        name_ar = b if re.search(r"[؀-ۿ]", b) else name_en
        dest = str(det1.cell(dr, hdr1["المدينة"]).value)
        parts = [p.strip() for p in re.sub(r"\s*\(\d+\)\s*$", "", dest).split(",")]
        city = parts[0]
        country = parts[-1] if parts[-1] not in ("None", "") else city
        sort += 1
        code = f"H{r:02d}"
        hotels[r] = code
        items.append(dict(code=code, kind="hotel", market=None, name_en=name_en, name_ar=name_ar, city=city, country=country,
                          stars=None, board_rule=str(det1.cell(dr, hdr1["قاعدة الوجبة"]).value or "").strip() or None,
                          sort=sort, status="active", source_label=str(mpkg.cell(r, 1).value).strip(),
                          collection=dict(COLLECTION)))
        if name_ar == name_en:
            report["build_notes"].append(f"{code}: the workbook gives no Arabic name; name_ar repeats the English name")

    # ---- sample -----------------------------------------------------------------------------------------------------------
    since = WEEKS[0]["collected"]
    sample = []
    for key, _ in dom_blocks:
        for o, routes in (("flydubai", FZ_ROUTES), ("emirates", EK_ROUTES)):
            if key in routes:
                sample.append(dict(survey="tickets", outlet=o, item=route_code[("domestic", key)], legs=["out", "back"], since=since))
    for key, _ in for_blocks:
        sample.append(dict(survey="tickets", outlet=FOREIGN[key], item=route_code[("foreign", key)], legs=["out", "back"], since=since))
    for r in hotel_rows:
        for o in ("dnata", "ekholidays"):
            sample.append(dict(survey="packages", outlet=o, item=hotels[r], legs=["package"], since=since))

    # ---- observations ---------------------------------------------------------------------------------------------------
    observations = {}
    stars_seen = {}
    other_hotel_names = {}           # hotel code -> dnata names the workbook itself calls a substitute
    pkg_cache = []
    for w, W in enumerate(WEEKS):
        rows = []
        tw = openpyxl.load_workbook(W["t_file"])
        wdom, wfor = sheet(tw, W["t_dom"]), sheet(tw, W["t_for"])
        method = " ".join(str(c.value) for c in tw[W["t_method"]]["A"] if c.value)
        method_lines = [str(c.value) for c in tw[W["t_method"]]["A"] if c.value]
        # flights per (outlet, route key, leg)
        flights = {}
        def add_flight(outlet, key, leg, date, no, dep, fare):
            flights.setdefault((outlet, key, leg), []).append(dict(date=str(date)[:10], no=str(no).strip(), dep=clean_dep(dep), fare=num(fare)))
        if W["t_det_dom"]:
            d = tw[W["t_det_dom"]]
            for r in range(2, d.max_row + 1):
                if d.cell(r, 1).value:
                    leg = "out" if str(d.cell(r, 2).value).startswith("ذهاب") else "back"
                    add_flight("flydubai", route_key(d.cell(r, 1).value), leg, d.cell(r, 3).value, d.cell(r, 4).value,
                               d.cell(r, 5).value, d.cell(r, 6).value)
        d = tw[W["t_det_for"]]
        for r in range(2, d.max_row + 1):
            if d.cell(r, 1).value:
                o = DETAIL_AIRLINE[str(d.cell(r, 1).value).strip()]
                leg = "out" if str(d.cell(r, 3).value).startswith("ذهاب") else "back"
                add_flight(o, route_key(d.cell(r, 2).value), leg, d.cell(r, 4).value, d.cell(r, 5).value, d.cell(r, 6).value,
                           d.cell(r, 7).value)
        wdom_rows = dict(leg_blocks(wdom, 4))
        wfor_rows = dict(leg_blocks(wfor, 3))

        def method_note(outlet):
            hits = [l for l in method_lines if OUTLET_AR[outlet] in l and any(x in l for x in BLOCK_WORDS)]
            return hits[0] if hits else ""

        def ticket_rows(outlet, market, key, mws, mr, c_lo, wws, wr, c_wlo, note):
            for i, leg in enumerate(("out", "back")):
                lo, hi = num(mws.cell(mr + i, c_lo).value), num(mws.cell(mr + i, c_lo + 1).value)
                wlo, whi = num(wws.cell(wr + i, c_wlo).value), num(wws.cell(wr + i, c_wlo + 1).value)
                if (lo, hi) != (wlo, whi):
                    report["mismatch"].append(f"{W['id']} {outlet} {key} {leg}: month {lo}/{hi} vs week {wlo}/{whi}")
                try:
                    status = ticket_status(lo, hi, note)
                except ValueError as e:
                    raise ValueError(f"{W['id']} {outlet} {key} {leg}: {e}")
                win = W["out"] if leg == "out" else W["back"]
                fl = flights.get((outlet, key, leg), [])
                row = dict(week=W["id"], survey="tickets", outlet=outlet, item=route_code[(market, key)], leg=leg,
                           lowest=lo, highest=hi, currency="AED", status=status, flags=[], source="scraped")
                if lo is not None:
                    dates = sorted({f["date"] for f in fl if f["date"]})
                    used = dates[0] if len(dates) == 1 else win
                    row["date_used"] = used
                    if used != win:                         # yellow alone only marks "has a note" (e.g. Riyadh W3 review)
                        row["flags"].append("next_day")
                    if fl:
                        row["flights"] = [dict(no=f["no"], dep=f["dep"], fare=f["fare"]) for f in fl]
                elif fl:
                    report["build_notes"].append(f"{W['id']} {outlet} {key} {leg}: flight details without a price (not used)")
                if note:
                    row["note"] = note
                rows.append(row)

        for key, mr in dom_blocks:
            wr = wdom_rows[key]
            wnote = segs(wdom.cell(wr, DOM_NOTE_W).value)
            ek_note = " · ".join(s for s in wnote if "الإماراتية" in s)
            fz_note = " · ".join(s for s in wnote if "الإماراتية" not in s)
            if key in FZ_ROUTES:
                ticket_rows("flydubai", "domestic", key, mdom, mr, DOM_BLOCK[w], wdom, wr, 3, fz_note)
            if key in EK_ROUTES:
                ticket_rows("emirates", "domestic", key, mdom, mr, DOM_BLOCK[w] + 3, wdom, wr, 6, ek_note or method_note("emirates"))
            for c in range(DOM_BLOCK[w], DOM_BLOCK[w] + 6):        # nothing priced outside the sample
                for i in (0, 1):
                    if mdom.cell(mr + i, c).value is not None and (c < DOM_BLOCK[w] + 3 and key not in FZ_ROUTES or
                                                                   c >= DOM_BLOCK[w] + 3 and key not in EK_ROUTES):
                        report["mismatch"].append(f"{W['id']} {key}: price outside the sample at {mdom.cell(mr + i, c).coordinate}")
        for key, mr in for_blocks:
            o = FOREIGN[key]
            wr = wfor_rows[key]
            s = segs(wfor.cell(wr, FOR_NOTE_W).value)
            assert s and s[0] == OUTLET_AR[o], (W["id"], key, s)
            note = " · ".join(s[1:]) or method_note(o)
            ticket_rows(o, "foreign", key, mfor, mr, FOR_BLOCK[w], wfor, wr, 3, note)

        # packages
        pw = openpyxl.load_workbook(W["p_file"])
        ps, pd = sheet(pw, W["p_sheet"]), pw[W["p_det"]]
        hdr = {str(c.value).strip(): c.column for c in pd[1] if c.value}
        det = {int(pd.cell(r, 1).value): r for r in range(2, pd.max_row + 1) if pd.cell(r, 1).value}
        pmethod = [str(c.value) for c in pw[W["p_method"]]["A"] if c.value]
        eh_line = next(l for l in pmethod if "Emirates Holidays" in l)
        for r in hotel_rows:
            code = hotels[r]
            assert str(ps.cell(r, 1).value).strip().lower() == str(mpkg.cell(r, 1).value).strip().lower(), (W["id"], r)
            v = num(mpkg.cell(r, PKG_COL[w]).value)
            wv = num(ps.cell(r, 3).value)
            dr = det.get(r)
            g = (lambda h: pd.cell(dr, hdr[h]).value if dr and h in hdr else None)
            final = num(g("السعر النهائي كما يظهر بالصفحة (درهم)"))
            if v != wv or (final is not None and final != v):
                report["mismatch"].append(f"{W['id']} dnata {code}: month {v} vs week sheet {wv} vs details {final}")
            note = str(ps.cell(r, PKG_NOTE_W).value or "").strip()
            extra = EXTRA_PKG_NOTE.get((code, W["id"]))
            if extra and not note:
                note = extra
            dnote = str(g("ملاحظات") or "").strip()
            matched = str(g("الفندق على دناتا") or "").strip() or None
            flags = []
            if v is not None:
                status = "to_review" if ("تنبيه" in note or "يُراجع" in note) else "ok"
            elif "غير متوفر" in note or "غير معروض" in note or "not found" in note:
                status = "not_available"
            else:
                raise ValueError(f"{W['id']} {code}: no price and no reason")
            if v is not None and ("فندق مختلف" in note or "استُخدم فرع" in note):   # an unpriced "nearest other hotel" is not a substitute
                flags.append("other_hotel")
                if matched:
                    other_hotel_names.setdefault(code, set()).add(matched)
            if v is not None and "بدون فطور" in note:
                flags.append("no_bb")
            checkin = str(g("الدخول") or "")[:10] or W["checkin"]
            checkout = str(g("الخروج") or "")[:10] or W["checkout"]
            nights = (dt.date.fromisoformat(checkout) - dt.date.fromisoformat(checkin)).days
            if v is not None and (nights > 4 or "مُدّد السفر يوماً" in note or "لضمان 4 ليالي" in note):
                flags.append("plus_one_day")
            if "شامل نقل المنتجع" in note:
                flags.append("transfer_incl")
            row = dict(week=W["id"], survey="packages", outlet="dnata", item=code, leg="package", price=v, currency="AED",
                       status=status, flags=flags, source="scraped")
            if v is not None:
                row["date_used"] = checkin
                if matched:
                    row["matched_name"] = matched
                ekf = str(g("رحلة الإماراتية بدون توقف (ذهاب / عودة)") or "").strip()
                fl = []
                for part in [p.strip() for p in ekf.split("/") if p.strip()]:
                    m = re.match(r"(\S+)\s+(\d{2}:\d{2})", part)
                    if m:
                        fl.append(dict(no=m.group(1), dep=m.group(2)))
                if fl:
                    row["flights"] = fl
                st = num(g("النجوم"))
                if st:
                    stars_seen.setdefault(code, []).append((W["id"], matched, st))
            if note:
                row["note"] = note
            elif dnote:
                row["note"] = dnote
            if checkin != W["checkin"] or checkout != W["checkout"]:
                row["note"] = (row.get("note", "") + f" (stay {checkin} to {checkout})").strip()
            rows.append(row)
            pkg_cache.append(row)
            # Emirates Holidays column: empty in every week; the method sheet says whether it was blocked or just not collected
            if num(mpkg.cell(r, PKG_COL[w] + 1).value) is not None:
                report["mismatch"].append(f"{W['id']} ekholidays {code}: unexpected price")
            if any(x in eh_line for x in BLOCK_WORDS):
                rows.append(dict(week=W["id"], survey="packages", outlet="ekholidays", item=code, leg="package", price=None,
                                 currency="AED", status="blocked", flags=[], note=eh_line, source="scraped"))
        observations[W["id"]] = {"rows": rows}

    # a matched dnata property the workbook calls a substitute in one week is the same substitute in every week
    for row in pkg_cache:
        names = other_hotel_names.get(row["item"], set())
        if row.get("matched_name") in names and "other_hotel" not in row["flags"]:
            row["flags"].append("other_hotel")
            report["build_notes"].append(f"{row['week']} {row['item']}: other_hotel carried by matched name {row['matched_name']}")
        if (row["item"], row["week"]) in EXTRA_OTHER_HOTEL and row["price"] is not None:
            row["flags"].append("other_hotel")
            row["note"] = (row.get("note", "") + " · " + EXTRA_OTHER_HOTEL[(row["item"], row["week"])]).strip(" ·")
            report["build_notes"].append(f"{row['week']} {row['item']}: other_hotel set by the build (no workbook note)")
    for (code, wk), txt in EXTRA_PKG_NOTE.items():
        report["build_notes"].append(f"{wk} {code}: not_available from the run result, the workbook is silent")
    # stars: the dnata star rating of the basket hotel itself (substitutes excluded)
    for it in items:
        if it["kind"] == "hotel":
            sub = other_hotel_names.get(it["code"], set())
            vals = [s for wk, m, s in stars_seen.get(it["code"], []) if m not in sub and (it["code"], wk) not in EXTRA_OTHER_HOTEL]
            it["stars"] = vals[0] if vals and len(set(vals)) == 1 else None

    # tidy rows: drop empty optional fields
    for wk in observations.values():
        for row in wk["rows"]:
            if not row["flags"]:
                del row["flags"]
            for k in ("lowest", "highest", "price"):
                if k in row and row[k] is None:
                    del row[k]

    weeks = []
    for W in WEEKS:
        weeks.append(dict(id=W["id"], month="2026-11", period="2026-11", n=W["n"],
                          label_en=f"Collection {W['n']}", label_ar=f"الجمع {W['n']}",
                          tickets=dict(out=W["out"], back=W["back"]),
                          packages=dict(checkin=W["checkin"], checkout=W["checkout"], nights=4),
                          collected_on=W["collected"], status="open" if W["n"] == 3 else "complete"))
    collectors = [
        dict(code="fz_full", outlet="flydubai", survey="tickets", script="scripts/oneoff/dnata/fz_full.py", run_location="cloud"),
        dict(code="ek_fares", outlet="emirates", survey="tickets", script="scripts/oneoff/dnata/run_ek_windows.cmd (ek_fares.py)", run_location="pc"),
        dict(code="air_saudia", outlet="saudia", survey="tickets", script="scripts/oneoff/dnata/air_saudia.py", run_location="cloud"),
        dict(code="air_egyptair", outlet="egyptair", survey="tickets", script="scripts/oneoff/dnata/air_egyptair.py", run_location="cloud"),
        dict(code="air_rj", outlet="rj", survey="tickets", script="scripts/oneoff/dnata/air_rj.py", run_location="cloud"),
        dict(code="air_pia", outlet="pia", survey="tickets", script="scripts/oneoff/dnata/air_pia.py", run_location="cloud"),
        dict(code="air_ba", outlet="ba", survey="tickets", script="scripts/oneoff/dnata/air_ba.py", run_location="cloud"),
        dict(code="air_airindia", outlet="airindia", survey="tickets", script=None, run_location="manual"),
        dict(code="air_turkish", outlet="turkish", survey="tickets", script=None, run_location="manual"),
        dict(code="dnata_packages", outlet="dnata", survey="packages", script="scripts/oneoff/dnata/dnata_packages.py + shots.py", run_location="cloud"),
        dict(code="ekholidays_manual", outlet="ekholidays", survey="packages", script=None, run_location="manual"),
    ]
    meta = dict(
        name="SPPI", description="Services producer prices: air tickets (domestic and foreign carriers) and holiday packages "
                                 "(flight + hotel), November 2026 sample from the office workbooks.",
        currency="AED",
        periods=[dict(id="2026-11", month="2026-11", label_en="Nov 2026", label_ar="نوفمبر 2026", status="open",
                      collections=[W["id"] for W in WEEKS])],
        weeks=weeks,
        outlets=[dict(code=c, name_en=en, name_ar=ar, kind=k, market=m, url=u, access=a, status="active")
                 for c, en, ar, k, m, u, a in OUTLETS],
        items=items, sample=sample, collectors=collectors,
        source=dict(month_workbooks=[MONTH_T.replace(REPO, ""), MONTH_P.replace(REPO, "")],
                    weekly_workbooks=sorted({W["t_file"].replace(REPO, "") for W in WEEKS} | {W["p_file"].replace(REPO, "") for W in WEEKS}),
                    column_map="scripts/oneoff/dnata/build_month_workbooks.py DOM_BLOCK/FOR_BLOCK/PKG_COL",
                    built=dt.date.today().isoformat()),
        conventions=dict(
            ticket_legs="lowest / highest per leg (highest omitted when equal to lowest, as in the office method); no per-leg "
                        "price: trip totals and the ticket price are computed by the page (total low = out + back, high falls "
                        "back to low per leg, price = average of the totals)",
            packages="price = dnata 'Total holiday' (flight + hotel, 1 adult, 4 nights); lowest/highest not used",
            failed="status 'failed' = our run did not complete (site search button did not respond); not a site refusal",
            emirates_holidays_W1="not collected and no reason given in the W1 method sheet: no rows (Not read)",
        ),
        build_notes=report["build_notes"],
    )
    return dict(meta=meta, observations=observations), report


if __name__ == "__main__":
    out = sys.argv[1]
    doc, report = build()
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("written", out)
    for m in report["mismatch"]:
        print("MISMATCH", m)
    for n in report["build_notes"]:
        print("NOTE", n)
