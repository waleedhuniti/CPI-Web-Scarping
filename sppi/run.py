"""One collection run over the SPPI H & J sample.

Everything about the sample - companies, products, serials, ISIC codes, which page belongs to which product, the
availability reasons - lives in data/sppi/ (config/, sample/, runs/), which is git-ignored: it never goes to the
repository.

  1. Every page in data/sppi/config/sppi_pages.json is fetched (robots.txt first) and parsed.
  2. Every source URL of the products sheet (data/sppi/sample/products.csv) that is not already a page is probed,
     so each company has at least one logged request.
  3. Each extracted price is linked to the sample products by the page's map rules (product_id + section H/J +
     registered ISIC + product ISIC come from the products sheet).
  4. Every product gets an availability: Scraping (price collected here) / Online فقط (shown to a person but not
     collectable automatically, data/sppi/config/sppi_status.json) / لا هذا ولا ذاك (no public price found).
"""
import csv
import gzip
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from .fetch import FetchResult, Net
from . import coverage
from .output import CSV_NAMES, write_tables
from .sources import airfares, generic, megayachts, oracle, pinas, probe, rta, tables, ups

ROOT = Path(__file__).resolve().parent.parent
STALE_DAYS = 365        # a tariff whose effective date is older than this is flagged: look for a newer edition
REPEAT_MIN_PAGES = 3    # a (context, price text) seen on this many pages of one host, and on half of them, is chrome

SCRAPING, ONLINE, NEITHER = "Scraping", "Online فقط", "لا هذا ولا ذاك"
EXT = {"pdf": "pdf", "json": "json", "jpeg": "jpg", "png": "png", "html": "html"}


# ---- inputs --------------------------------------------------------------------------------------------
def load_products(path: Path | None = None) -> dict:
    path = path or ROOT / "data/sppi/sample/products.csv"
    return {r["product_id"]: r for r in csv.DictReader(open(path, encoding="utf-8-sig"))}


def load_companies(path: Path | None = None) -> dict:
    path = path or ROOT / "data/sppi/sample/companies.csv"
    return {r["ser"]: r for r in csv.DictReader(open(path, encoding="utf-8-sig"))}


def load_pages(products: dict, path: Path | None = None) -> tuple[list[dict], str]:
    cfg = json.load(open(path or ROOT / "data/sppi/config/sppi_pages.json", encoding="utf-8"))
    pages = cfg["pages"]
    for page in pages:
        for rule in page.get("map", []):
            pid = rule["product"]
            if not pid.startswith("+") and pid not in products:
                raise ValueError(f"page {page['id']}: unknown product_id {pid}")
    known = {p["url"] for p in pages}
    n = defaultdict(int)
    for prod in products.values():
        url = prod["source_url"]
        if url.startswith("http") and url not in known:
            known.add(url)
            n[prod["ser"]] += 1
            pages.append(dict(id=f"probe_{prod['ser']}_{n[prod['ser']]}", ser=prod["ser"], url=url, parser="probe",
                              map=[]))
    return pages, cfg.get("drop_labels", "")


# ---- fetching & parsing --------------------------------------------------------------------------------
def save_snapshot(res: FetchResult, run_dir: Path, name: str) -> str:
    if not res.body:
        return ""
    ext = next((e for k, e in EXT.items() if k in (res.content_type or "").lower()), "bin")
    rel = Path("snapshots") / f"{name}.{ext}.gz"
    (run_dir / rel).parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(run_dir / rel, "wb") as f:
        f.write(res.body)
    return rel.as_posix()


def _stale(effective: str, run_date: str) -> str:
    if not effective:
        return ""
    age = (date.fromisoformat(run_date) - date.fromisoformat(effective)).days
    return f"effective {effective} is {age} days old - check for a newer edition" if age > STALE_DAYS else ""


def evidence(res: FetchResult, snap: str) -> dict:
    return dict(source_url=res.final_url or res.url, fetched_at=res.fetched_at, http_status=res.status,
                snapshot=snap, sha256=res.sha256 if res.body else "")


def parse_page(page: dict, res: FetchResult, net: Net, run_dir: Path, run_date: str, readings: dict,
               drop_labels: str) -> tuple[list[dict], list[dict], list[str]]:
    """(raw price records, price mentions, notes). Records carry item/spec/price/... and their evidence."""
    ev = evidence(res, save_snapshot(res, run_dir, page["id"]))
    parser, notes, mentions = page["parser"], [], []
    if not res.ok:
        return [], [], notes
    if parser == "rta_nol":
        recs = [dict(r, status="parsed_page") for r in rta.parse_nol(res.text())]
    elif parser == "rta_taxi":
        recs = [dict(r, status="parsed_page") for r in rta.parse_taxi(res.text())]
    elif parser == "megayachts":
        recs = [dict(r, status="parsed_page") for r in megayachts.parse(res.text())]
    elif parser == "ups_tariff":
        parsed, unparsed, effective = ups.parse(res.body)
        recs = [dict(r, status="parsed_pdf") for r in parsed]
        notes.append(f"effective date {effective or 'not found'}")
        if unparsed:
            notes.append(f"{len(unparsed)} rate lines did not fit the layout: {' || '.join(unparsed[:5])}")
        if stale := _stale(effective, run_date):
            notes.append(stale)
    elif parser == "oracle_api":
        parsed, updated = oracle.parse(res.body)
        recs = [dict(r, status="api") for r in parsed]
        notes.append(f"price list lastUpdated {updated}")
    elif parser == "pinas_images":
        recs, img_notes = _pinas(page, res, net, run_dir, readings.get("pinas_cargo", []))
        notes += img_notes
        mentions = probe.mentions(res.text())
    elif parser == "emirates_featured":
        dep = page.get("departure", "DXB")
        parsed, seen = airfares.emirates_featured(res.text(), dep)
        recs = [dict(r, status="parsed_page") for r in parsed]
        if not parsed:
            notes.append(f"no {dep} departures on the page (it lists departures for the visitor's country: "
                         f"{', '.join(sorted(seen)) or 'none'}) - run from a UAE network")
    elif parser == "flydubai_routes":
        recs = _flydubai_routes(page, res, net, run_dir, notes)
    elif parser == "tables":
        recs = [dict(r, status="parsed_page") for r in tables.parse(res.text(), page.get("unit", ""))]
    elif parser == "generic":
        recs = []
        for g in generic.extract(res.text(), include_chrome=page.get("include_chrome", False)):
            if drop_labels and re.search(drop_labels, g["label"], re.I):
                continue
            recs.append(dict(item=" | ".join(x for x in (g["context"], g["label"]) if x), spec=g["after"], price=g["price"],
                             currency=g["currency"], unit=g["unit"], price_type="as published",
                             price_text=g["price_text"], vat="as published", effective_date="", note="",
                             status="parsed_page", _context=g["context"]))
    else:   # probe
        return [], [dict(m) for m in probe.mentions(res.text())], notes
    out = []
    for r in recs:
        # keep looks at everything shown for the price; drop only at its own label and context (item, spec), so a
        # sentence that mentions VAT or an exit charge next to a real price does not remove that price
        text = f"{r['item']} | {r.get('spec', '')} | {r['price_text']}"
        if page.get("keep") and not re.search(page["keep"], text, re.I):
            continue
        if page.get("drop") and re.search(page["drop"], f"{r['item']} | {r.get('spec', '')}", re.I):
            continue
        out.append(r if "source_url" in r else dict(ev, **r))
    return out, mentions, notes


def _flydubai_routes(page: dict, res: FetchResult, net: Net, run_dir: Path, notes: list[str]) -> list[dict]:
    """The 'Lowest fares' page gives the route pages; each route page gives its lowest one-way / return fare.
    page['routes'] (optional) fixes the basket of route slugs, e.g. ["baku", "tbilisi"]."""
    links = airfares.flydubai_route_links(res.text())
    if page.get("routes"):
        wanted = {f"/en-ae/flights-from-dubai-to-{r}/" for r in page["routes"]}
        missing = wanted - {link.rstrip("/") + "/" for link in links}
        if missing:
            notes.append(f"routes not linked from the page: {', '.join(sorted(missing))}")
        links = sorted(wanted)
    records = []
    for link in links:
        url = urljoin(res.final_url or res.url, link)
        r = net.get(url, tag=page["id"])
        snap = save_snapshot(r, run_dir, f"{page['id']}__{link.strip('/').split('/')[-1]}")
        if not r.ok:
            notes.append(f"{link}: {r.outcome} {r.status}")
            continue
        found = airfares.flydubai_route(r.text())
        if not found:
            notes.append(f"{link}: no 'Route information' fares on the page")
        records += [dict(evidence(r, snap), **x, status="parsed_page") for x in found]
    notes.append(f"{len(links)} route pages read")
    return records


def _pinas(page: dict, res: FetchResult, net: Net, run_dir: Path, readings: list[dict]):
    on_page = pinas.image_urls(res.text())
    records, notes = [], []
    for reading in readings:
        if reading["image_url"] not in on_page:
            notes.append(f"{reading['id']}: image no longer on the page - read the new rate card")
            continue
        img = net.get(reading["image_url"], tag=page["id"])
        snap = save_snapshot(img, run_dir, f"{page['id']}__{reading['id']}")
        if not img.ok:
            notes.append(f"{reading['id']}: image fetch {img.outcome} {img.status}")
            continue
        if img.sha256 != reading["sha256"]:
            notes.append(f"{reading['id']}: image_changed (sha256 {img.sha256[:12]}... vs read "
                         f"{reading['sha256'][:12]}...) - no prices emitted; read the new image and update "
                         "data/sppi/config/sppi_image_transcriptions.json")
            continue
        check = pinas.ocr_agreement(reading, pinas.ocr_numbers(img.body))
        notes.append(f"{reading['id']}: image unchanged; {check}")
        for r in pinas.records_from_reading(reading):
            records.append(dict(evidence(img, snap), **r, status="image_reading"))
    return records, notes


def drop_repeated(raw: dict) -> dict:
    """Remove generic records whose (context, price text) repeats on many pages of the same host (site chrome)."""
    by_host = defaultdict(list)
    for pid, recs in raw.items():
        if recs and "_context" in recs[0]:
            by_host[urlsplit(recs[0]["source_url"]).netloc].append(pid)
    for host, pids in by_host.items():
        seen = defaultdict(set)
        for pid in pids:
            for r in raw[pid]:
                seen[(r["_context"], r["price_text"])].add(pid)
        chrome = {k for k, v in seen.items() if len(v) >= REPEAT_MIN_PAGES and len(v) * 2 >= len(pids)}
        for pid in pids:
            raw[pid] = [r for r in raw[pid] if (r["_context"], r["price_text"]) not in chrome]
    return raw


# ---- linking prices to products ------------------------------------------------------------------------
def product_fields(pid: str, ser: str, products: dict, companies: dict) -> dict:
    if pid.startswith("+"):
        c = companies.get(ser, {})
        return dict(product_id="", ser=ser, section=c.get("section", ""), company=c.get("name_en") or c.get("name_ar", ""),
                    isic_registered=c.get("isic", ""), red=c.get("red", ""), type="", product=pid[1:],
                    isic_product="", in_sample="لا - بند إضافي غير موجود في قائمة المنتجات")
    p = products[pid]
    return dict(product_id=pid, ser=p["ser"], section=p["section"], company=p["company"],
                isic_registered=p["isic_registered"], red=p["red"], type=p["type"], product=p["product"],
                isic_product=p["isic_product"], in_sample="نعم")


def map_records(page: dict, recs: list[dict], products: dict, companies: dict, run_date: str) -> list[dict]:
    """Link each record to every product whose rule matches (a record identical to one already linked to the same
    product - same item, spec, price and text - is linked once)."""
    out, seen = [], set()
    for r in recs:
        text = f"{r['item']} | {r.get('spec', '')}"
        for rule in page.get("map", []):
            if rule.get("match") and not re.search(rule["match"], text, re.I):
                continue
            key = (rule["product"], r["item"], r.get("spec", ""), r["price"], r["price_text"])
            if key in seen:
                continue
            seen.add(key)
            note = "; ".join(x for x in (r.get("note"), rule.get("note")) if x)
            row = {k: v for k, v in r.items() if not k.startswith("_")}
            out.append(dict(row, **product_fields(rule["product"], page["ser"], products, companies),
                            run_date=run_date, page_id=page["id"], note=note))
    return out


def availability(products: dict, companies: dict, prices: list[dict], status_cfg: dict) -> list[dict]:
    priced = defaultdict(list)
    for p in prices:
        if p["product_id"]:
            priced[p["product_id"]].append(p)
    rows = []
    for pid, p in products.items():
        got = priced.get(pid, [])
        st = status_cfg["products"].get(pid) or status_cfg["companies"].get(p["ser"])
        if got:
            avail, reason, verified = SCRAPING, "", "yes"
        elif st:
            avail = ONLINE if st["status"] == "online" else NEITHER
            reason, verified = st["reason"], st.get("verified", "")
        else:
            c = companies.get(p["ser"], {})
            avail, verified = NEITHER, ""
            reason = c.get("scraping_reason") or "No public price found on the pages checked."
        values = sorted({(x["currency"], x["price"]) for x in got})
        cur = {c for c, _ in values}
        rng = ""
        if values and len(cur) == 1:
            lo, hi = values[0][1], values[-1][1]
            rng = f"{lo:,.2f}" if lo == hi else f"{lo:,.2f} - {hi:,.2f}"
        rows.append(dict(p, availability=avail, verified=verified, n_prices=len(got),
                         currency="/".join(sorted(cur)), price_range=rng,
                         price_sources=" ; ".join(sorted({x["source_url"] for x in got}))[:1000], reason=reason))
    return rows


# ---- run -----------------------------------------------------------------------------------------------
METHOD = [
    "المنهجية - جمع أسعار SPPI للقسمين H و J (كل شركات العينة) باستخدام Scrapling",
    "1) قائمة الشركات والمنتجات مأخوذة من ملف العينة (scripts/sppi_import_products.py): الرقم المتسلسل (h/j...)، القسم H/J، رمز النشاط المسجل، رمز ISIC الفعلي للبند. هذه البيانات تبقى في data/sppi/ ولا تُرفع إلى المستودع.",
    "2) قبل أي طلب يُقرأ robots.txt (قواعد Google عبر protego). 2xx = تُطبَّق القواعد؛ 4xx = لا قواعد؛ 5xx أو تعذّر القراءة = لا يُجلب.",
    "3) طلب واحد لكل موقع كل ثانيتين على الأقل. لا يتم تجاوز أي حماية (Cloudflare / CAPTCHA) ولا تسجيل دخول.",
    "4) كل صفحة/ملف يُحفظ مضغوطاً في snapshots مع بصمة sha256، وكل سعر يحمل الرابط وحالة HTTP ووقت الجلب ونص السعر كما ورد.",
    "5) ربط السعر بالمنتج يتم بقواعد مكتوبة في data/sppi/config/sppi_pages.json (رابط الصفحة + نمط نصي) وليس بالتخمين. بند يبدأ بـ '+' سعر منشور لخدمة غير موجودة في قائمة المنتجات.",
    "6) إمكانية الحصول على السعر: Scraping = جُمع آلياً في هذا التشغيل؛ Online فقط = يظهر للشخص على الموقع/التطبيق لكن لا يمكن جمعه آلياً (robots.txt يمنع، حماية، خطوة حجز أو تسجيل)؛ لا هذا ولا ذاك = لا يوجد سعر منشور (عرض سعر/عقد B2B أو لا يوجد موقع).",
    "7) عمود 'تم التحقق' في حالة Online فقط: yes = شوهد السعر فعلاً، no = متوقع من طبيعة الخدمة ويحتاج تأكيداً يدوياً.",
    "8) عنوان IP المستخدم في التشغيل ليس إماراتياً؛ المواقع التي تغيّر المحتوى حسب الدولة (مثل OSN) مذكورة في الملاحظات.",
    "9) السعر المنشور سعر قائمة وليس بالضرورة سعر معاملة؛ يجب تثبيت مواصفة خدمة ثابتة لكل شركة قبل إدخالها في المؤشر.",
]


def run(run_date: str | None = None, only: list[str] | None = None, out_root: Path | None = None) -> Path:
    run_date = run_date or date.today().isoformat()
    products, companies = load_products(), load_companies()
    pages, drop_labels = load_pages(products)
    status_cfg = json.load(open(ROOT / "data/sppi/config/sppi_status.json", encoding="utf-8"))
    readings = json.load(open(ROOT / "data/sppi/config/sppi_image_transcriptions.json", encoding="utf-8"))
    if only:
        pages = [p for p in pages if p["id"] in only or p["ser"] in only]
    run_dir = (out_root or ROOT / "data/sppi/runs") / run_date
    run_dir.mkdir(parents=True, exist_ok=True)
    net = Net()
    raw, page_rows, mentions = {}, {}, []
    for page in pages:
        res = net.get(page["url"], page.get("fetch", "http"), tag=page["id"])
        recs, ment, notes = parse_page(page, res, net, run_dir, run_date, readings, drop_labels)
        raw[page["id"]] = recs
        c = companies.get(page["ser"], {})
        mentions += [dict(m, ser=page["ser"], section=c.get("section", ""), company=c.get("name_en", ""),
                          page_id=page["id"], source_url=res.final_url or page["url"], run_date=run_date)
                     for m in ment]
        page_rows[page["id"]] = dict(page_id=page["id"], ser=page["ser"], section=c.get("section", ""),
                                     company=c.get("name_en", ""), url=page["url"], final_url=res.final_url,
                                     parser=page["parser"], http_status=res.status, robots=res.robots,
                                     outcome=res.outcome, n_raw=len(recs), n_mentions=len(ment),
                                     seconds=res.seconds, fetched_at=res.fetched_at,
                                     note=" | ".join(x for x in [page.get("note", ""), res.note,
                                                                 "; ".join(res.redirects)] + notes if x))
        print(f"[{page['id']}] {res.outcome} http={res.status} robots={res.robots} raw={len(recs)} "
              f"mentions={len(ment)} {res.seconds}s", flush=True)
    raw = drop_repeated(raw)
    prices = []
    by_id = {p["id"]: p for p in pages}
    for pid, recs in raw.items():
        mapped = map_records(by_id[pid], recs, products, companies, run_date)
        prices += mapped
        page_rows[pid]["n_prices"] = len(mapped)
    prod_rows = availability(products, companies, prices, status_cfg)
    avail_by_product = {r["product_id"]: r["availability"] for r in prod_rows}
    for pid, row in page_rows.items():
        targets = [r["product"] for r in by_id[pid].get("map", [])]
        if row.get("n_prices"):
            row["availability"] = SCRAPING
        elif any(avail_by_product.get(t) == ONLINE for t in targets) or \
                status_cfg["companies"].get(row["ser"], {}).get("status") == "online":
            row["availability"] = ONLINE
        else:
            row["availability"] = NEITHER
    fetch_log = []
    for r in net.log:
        page = page_rows.get(r.tag, {})
        fetch_log.append(dict(page_id=r.tag, ser=page.get("ser", ""), section=page.get("section", ""),
                              company=page.get("company", ""), availability=page.get("availability", ""),
                              url=r.url, final_url=r.final_url, redirects="; ".join(r.redirects), mode=r.mode,
                              http_status=r.status, robots=r.robots, outcome=r.outcome, fetched_at=r.fetched_at,
                              seconds=r.seconds, bytes=len(r.body), sha256=r.sha256 if r.body else "", note=r.note))
    tables = dict(prices=prices, products=prod_rows, pages=list(page_rows.values()), mentions=mentions,
                  fetch_log=fetch_log)
    write_tables(run_dir, run_date, dict(tables, **coverage_tables(prod_rows, companies)), METHOD)
    return run_dir


def coverage_tables(prod_rows: list[dict], companies: dict) -> dict:
    """Coverage by activity and by company, when the sample has production figures (activities.csv)."""
    path = ROOT / "data/sppi/sample/activities.csv"
    if not path.exists() or not any(c.get("production_adjusted") for c in companies.values()):
        return {}
    activities = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    total = next((float(a["production_adjusted"]) for a in activities if a["level"] == "total"), 0.0)
    comp = coverage.company_rows(companies, coverage.company_classes(prod_rows), total)
    act = coverage.activity_rows(activities, comp)
    return dict(coverage=act, coverage_companies=comp, coverage_summary=coverage.summary_lines(act))


def rebuild(run_date: str) -> Path:
    """Rewrite a run's workbook (and coverage CSVs) from its CSVs and the current sample - no fetching."""
    run_dir = ROOT / "data/sppi/runs" / run_date
    read = (lambda key: list(csv.DictReader(open(run_dir / CSV_NAMES[key], encoding="utf-8-sig"))))
    tables = {k: read(k) for k in ("prices", "products", "pages", "fetch_log", "mentions")}
    for r in tables["prices"]:
        r["price"] = float(r["price"])
    for r in tables["products"]:
        r["n_prices"] = int(r["n_prices"] or 0)
    write_tables(run_dir, run_date, dict(tables, **coverage_tables(tables["products"], load_companies())), METHOD)
    return run_dir
