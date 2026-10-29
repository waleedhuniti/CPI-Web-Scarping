"""One collection run over config/sppi_sources.json: fetch, keep the evidence, parse, write the tables."""
import gzip
import json
from datetime import date
from pathlib import Path

from .fetch import FetchResult, Net
from .output import FETCH_COLS, MENTION_COLS, PRICE_COLS, SOURCE_COLS, write_csv, write_xlsx
from .sources import megayachts, oracle, pinas, probe, rta, ups

ROOT = Path(__file__).resolve().parent.parent
STALE_DAYS = 365        # a tariff whose effective date is older than this is flagged: look for a newer edition

EXT = {"pdf": "pdf", "json": "json", "jpeg": "jpg", "png": "png", "html": "html"}


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


def collect_source(src: dict, net: Net, run_dir: Path, run_date: str, readings: dict):
    """(price records, price mentions, source summary row) for one configured source."""
    res = net.get(src["url"], src.get("fetch", "http"))
    snap = save_snapshot(res, run_dir, src["id"])
    base = dict(run_date=run_date, ser=src["ser"], company=src["company"], source_id=src["id"],
                source_url=res.final_url or src["url"], fetched_at=res.fetched_at, http_status=res.status,
                snapshot=snap, sha256=res.sha256 if res.body else "")
    notes = [n for n in (src.get("notes", ""), res.note, "; ".join(res.redirects)) if n]
    summary = dict(source_id=src["id"], ser=src["ser"], company=src["company"], url=src["url"],
                   final_url=res.final_url, http_status=res.status, robots=res.robots, outcome=res.outcome,
                   seconds=res.seconds, fetched_at=res.fetched_at, snapshot=snap, sha256=base["sha256"])
    records, mentions = [], []
    parser = src["parser"]
    if res.ok:
        if parser == "rta_nol":
            records = [dict(base, **r, status="parsed_page") for r in rta.parse_nol(res.text())]
        elif parser == "rta_taxi":
            records = [dict(base, **r, status="parsed_page") for r in rta.parse_taxi(res.text())]
        elif parser == "megayachts":
            records = [dict(base, **r, status="parsed_page") for r in megayachts.parse(res.text())]
        elif parser == "ups_tariff":
            recs, unparsed, effective = ups.parse(res.body)
            records = [dict(base, **r, status="parsed_pdf") for r in recs]
            notes.append(f"effective date {effective or 'not found'}")
            if unparsed:
                notes.append(f"{len(unparsed)} rate lines did not fit the layout: {' || '.join(unparsed[:5])}")
            if stale := _stale(effective, run_date):
                notes.append(stale)
        elif parser == "oracle_api":
            recs, updated = oracle.parse(res.body)
            records = [dict(base, **r, status="api") for r in recs]
            notes.append(f"price list lastUpdated {updated}")
        elif parser == "pinas_images":
            records, img_notes = _pinas(res, net, run_dir, base, readings.get("pinas_cargo", []))
            notes += img_notes
            mentions = probe.mentions(res.text())
        elif parser == "probe":
            mentions = probe.mentions(res.text())
        if parser != "probe" and not records:
            summary["outcome"] = "parsed_zero"
            notes.append("dedicated parser found no prices - the page layout may have changed")
    mentions = [dict(base, **m) for m in mentions]
    summary.update(n_prices=len(records), n_mentions=len(mentions), note=" | ".join(notes))
    return records, mentions, summary


def _pinas(page: FetchResult, net: Net, run_dir: Path, base: dict, readings: list[dict]):
    on_page = pinas.image_urls(page.text())
    records, notes = [], []
    for reading in readings:
        if reading["image_url"] not in on_page:
            notes.append(f"{reading['id']}: image no longer on the page - read the new rate card")
            continue
        img = net.get(reading["image_url"])
        snap = save_snapshot(img, run_dir, f"{base['source_id']}__{reading['id']}")
        if not img.ok:
            notes.append(f"{reading['id']}: image fetch {img.outcome} {img.status}")
            continue
        if img.sha256 != reading["sha256"]:
            notes.append(f"{reading['id']}: image_changed (sha256 {img.sha256[:12]}... vs read "
                         f"{reading['sha256'][:12]}...)"
                         " - no prices emitted; read the new image and update config/sppi_image_transcriptions.json")
            continue
        check = pinas.ocr_agreement(reading, pinas.ocr_numbers(img.body))
        notes.append(f"{reading['id']}: image unchanged; {check}")
        img_base = dict(base, source_url=img.final_url, fetched_at=img.fetched_at, http_status=img.status,
                        snapshot=snap, sha256=img.sha256)
        for r in pinas.records_from_reading(reading):
            records.append(dict(img_base, **r, status="image_reading"))
    return records, notes


METHOD = [
    "المنهجية - جمع أسعار SPPI للقسمين H و J باستخدام Scrapling",
    "1) قبل أي طلب يُقرأ robots.txt للموقع (قواعد Google عبر protego). 2xx = تُطبَّق القواعد؛ 4xx = لا قواعد؛ 5xx أو تعذّر القراءة = لا يُجلب.",
    "2) طلب واحد لكل موقع كل ثانيتين على الأقل (أو Crawl-delay إن كان أكبر). إعادات التوجيه تُتبع يدوياً ويُفحص robots.txt لكل نطاق جديد.",
    "3) لا يتم تجاوز أي حماية (Cloudflare / CAPTCHA): الصفحة تُسجَّل blocked_bot_protection ويُطلب السعر من مصدر رسمي آخر أو بالمسح.",
    "4) كل صفحة/ملف يُحفظ مضغوطاً في snapshots مع بصمة sha256، وكل سعر يحمل الرابط وحالة HTTP ووقت الجلب ونص السعر كما ورد.",
    "5) طرق الاستخراج: parsed_page = جدول/بطاقة HTML؛ parsed_pdf = جداول PDF (كل صف يجب أن يحوي قيمة لكل منطقة وإلا يُبلَّغ عنه)؛ api = واجهة أسعار رسمية؛ image_reading = قراءة صورة محفوظة ببصمتها، تُستخدم فقط إذا لم تتغير الصورة.",
    "6) ورقة 'إشارات الأسعار' ليست أسعاراً للمؤشر: هي كل مبلغ ظاهر في صفحات بلا محلل مخصص، لتقييم معيار 'السعر ظاهر للعامة'.",
    "7) عنوان IP المستخدم في التشغيل قد لا يكون إماراتياً؛ المواقع التي تغيّر المحتوى حسب الدولة (مثل OSN) تظهر في الملاحظات.",
    "8) السعر المنشور سعر قائمة وليس بالضرورة سعر معاملة؛ يجب تثبيت مواصفة خدمة ثابتة لكل شركة قبل إدخالها في المؤشر.",
]


def run(run_date: str | None = None, only: list[str] | None = None, out_root: Path | None = None) -> Path:
    run_date = run_date or date.today().isoformat()
    sources = json.load(open(ROOT / "config/sppi_sources.json", encoding="utf-8"))["sources"]
    readings = json.load(open(ROOT / "config/sppi_image_transcriptions.json", encoding="utf-8"))
    if only:
        sources = [s for s in sources if s["id"] in only]
    run_dir = (out_root or ROOT / "data/sppi/runs") / run_date
    run_dir.mkdir(parents=True, exist_ok=True)
    net = Net()
    prices, mentions, summary = [], [], []
    for src in sources:
        print(f"[{src['id']}] {src['url']}", flush=True)
        p, m, s = collect_source(src, net, run_dir, run_date, readings)
        print(f"    -> {s['outcome']} http={s['http_status']} robots={s['robots']} prices={s['n_prices']} "
              f"mentions={s['n_mentions']} {s['seconds']}s", flush=True)
        prices += p
        mentions += m
        summary.append(s)
    fetch_log = [dict(url=r.url, final_url=r.final_url, redirects="; ".join(r.redirects), mode=r.mode,
                      http_status=r.status, robots=r.robots, outcome=r.outcome, fetched_at=r.fetched_at,
                      seconds=r.seconds, bytes=len(r.body), sha256=r.sha256 if r.body else "", note=r.note)
                 for r in net.log]
    write_csv(run_dir / "prices.csv", PRICE_COLS, prices)
    write_csv(run_dir / "price_mentions.csv", MENTION_COLS, mentions)
    write_csv(run_dir / "sources.csv", SOURCE_COLS, summary)
    write_csv(run_dir / "fetch_log.csv", FETCH_COLS, fetch_log)
    write_xlsx(run_dir / f"SPPI_HJ_prices_{run_date}.xlsx",
               dict(prices=prices, sources=summary, mentions=mentions, fetch_log=fetch_log), METHOD)
    return run_dir
