#!/usr/bin/env python3
"""External benchmark indices for TrendX, rebased to mean of 2024 = 100.

    python3 scripts/trendx/build_benchmarks.py

Writes data/trendx/benchmarks/benchmarks.json and benchmarks.csv (long form: id, period, native, value_2024eq100) and
keeps every download under data/trendx/raw/benchmarks/<name>_<YYYY-MM-DD>.<ext>.

Sources (group): ours = TrendX store index; gcc = GCC-Stat Marsa SDMX (all-items CPI for the six states and the GCC aggregate,
plus the 12 COICOP divisions for the UAE), World Bank GEM monthly CPI (not seasonally adjusted) for the fresher 2026 points,
IMF CPI (SDMX 3.0) as six single-series requests; world = US CPI-U all items NSA (BLS API v1, last three years; FRED CSV for
the history when it answers), euro-area HICP (Eurostat), World Bank commodity price indices (Pink Sheet monthly file in raw/).

Rebasing: value_2024eq100 = native / mean(native, Jan-Dec 2024) * 100, only when all 12 months of 2024 exist on one base;
otherwise null and lag_note says why. Native values are kept beside the rebased ones.

Politeness: a plain descriptive User-Agent, 60 s timeout, one retry on a plain timeout only, never on 4xx/5xx, at least 2.5 s
between requests to the same host, Retry-After honoured, a host is not asked again after 5 refused pages in a row. A refused
page is recorded in "refused", never read as "no data". The four government portals that refused this machine on 9 Nov 2026
(data.gov.om, data.gov.bh, data.gov.qa, releaseeuaestat.fcsc.gov.ae) are not asked at all; they are listed as refused with a
note of what the research session saw on them through another tool.
"""
import csv
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import openpyxl
import requests

ROOT = Path(__file__).resolve().parents[2]
STORE_INDEX = ROOT / "data/trendx/store/index_2024.csv"
RAW_DIR = ROOT / "data/trendx/raw"
RAW = RAW_DIR / "benchmarks"
OUT = ROOT / "data/trendx/benchmarks"
UA = "TrendX-benchmarks/1.0 (Digital Dubai, internal statistics)"
TIMEOUT = 60
MIN_GAP = 2.5
MAX_REFUSED = 5
TODAY = dt.date.today()
START = "2015-01"

MARSA = "https://sdmx.marsa.gccstat.org/FusionRegistry/ws/public/sdmxapi/rest/"
WB_GEM = "https://api.worldbank.org/v2/sources/15/country/SAU;QAT;BHR;OMN;ARE;KWT/series/{series}/time/{time}?format=json&per_page=5000"
IMF = "https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/CPI/+/{iso3}.CPI._T.IX.M"
BLS = "https://api.bls.gov/publicAPI/v1/timeseries/data/CUUR0000SA0"
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCNS"
EUROSTAT = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_midx"
            "?geo=EA&coicop=CP00&unit=I15&sinceTimePeriod=2015-01")
GCCSTAT_TERMS = "https://www.gccstat.org/en/terms-of-use"

GCC = ["ARE", "SAU", "QAT", "KWT", "BHR", "OMN"]
COUNTRY_AR = {"ARE": "الإمارات", "SAU": "السعودية", "QAT": "قطر", "KWT": "الكويت", "BHR": "البحرين", "OMN": "عُمان",
              "GCC": "مجلس التعاون الخليجي"}
COUNTRY_EN = {"ARE": "United Arab Emirates", "SAU": "Saudi Arabia", "QAT": "Qatar", "KWT": "Kuwait", "BHR": "Bahrain",
              "OMN": "Oman", "GCC": "GCC aggregate"}
COICOP_AR = {"01": "الأغذية والمشروبات غير الكحولية", "02": "المشروبات الكحولية والتبغ", "03": "الملابس والأحذية",
             "04": "السكن والمياه والكهرباء والغاز", "05": "الأثاث والتجهيزات المنزلية", "06": "الصحة", "07": "النقل",
             "08": "الاتصالات", "09": "الترفيه والثقافة", "10": "التعليم", "11": "المطاعم والفنادق",
             "12": "سلع وخدمات متنوعة"}

LIC_GCCSTAT = ("GCC-Stat open data, attribution required (the terms page on www.gccstat.org could not be read from this "
               "machine: HTTP 404; wording per the 9 Nov 2026 source research)")
LIC_WB = "CC BY 4.0 (World Bank Open Data terms)"
LIC_IMF = "IMF terms: attribution required; automated bulk download prohibited — written permission pending"
LIC_BLS = "US federal public domain (BLS)"
LIC_FRED = "US federal public domain (BLS data redistributed by FRED, St. Louis Fed; FRED terms of use)"
LIC_EUROSTAT = "Eurostat free re-use with attribution (Commission Decision 2011/833/EU)"

# Portals that refused this machine on 9 Nov 2026 (see docs/trendx/gcc_cpi_sources_ar.md): listed, never asked.
KNOWN_REFUSED = [
    {"source": "NCSI Oman via data.gov.om (Knoema platform)", "url": "https://data.gov.om/", "status": "403",
     "note": "Refused this machine with HTTP 403; not asked again. The research session (9 Nov 2026) read it through "
             "another tool: CPI dataset `rauaefb`, 2018 = 100, monthly, latest Sep 2026 = 110.70, CSV/XLSX/JSON/SDMX, "
             "Open Government Licence."},
    {"source": "iGA Bahrain via data.gov.bh", "url": "https://www.data.gov.bh/", "status": "connection reset",
     "note": "Connection reset from this machine; not asked again. Research session saw: CPI, Apr 2019 = 100, monthly "
             "since Jan 2017, latest Sep 2026 = 104.9, JSON/CSV/XLSX API, open data portal licence."},
    {"source": "NPC Qatar via data.gov.qa", "url": "https://www.data.gov.qa/", "status": "connection reset",
     "note": "Connection reset from this machine; not asked again. Research session saw: CPI 2018 = 100, monthly Jan 2020 "
             "to Dec 2025 (Dec 2025 = 112.39), CC BY 4.0; the new 2024 = 100 series (from Jul 2026) is not on the portal "
             "yet; PPI 2018 = 100 to Apr 2026 = 119.87."},
    {"source": "FCSC UAE.Stat SDMX 2.1 REST", "url": "https://releaseeuaestat.fcsc.gov.ae/rest/", "status": "403",
     "note": "Refused this machine with HTTP 403; not asked again. Research session saw: dataflow FCSA:DF_CPI 3.3.0, "
             "2021 = 100 to Dec 2025 then 2024 = 100 from Jan 2026 (BASE_YEAR attribute), latest Jun 2026 = 107.77, "
             "SDMX-CSV/JSON/XML without a key; licence wording contradictory, written confirmation needed."},
]


# ----------------------------------------------------------------------------------------------------------------- fetching
class Fetcher:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = UA
        self.next_ok = {}      # host -> monotonic time before which we do not ask again
        self.bad = {}          # host -> refused pages in a row
        self.refused = []

    def _refuse(self, source, url, status, note, host):
        self.bad[host] = self.bad.get(host, 0) + 1
        self.refused.append({"source": source, "url": url, "status": status, "note": note})
        print(f"  REFUSED {status}: {url} ({note})", file=sys.stderr)
        return None

    def get(self, url, name, ext, source, accept=None, ok=None):
        """One request (one retry on a plain timeout). Returns bytes or None; saves the raw body under RAW/.
        `ok(body) -> error text or None` lets a caller treat a 200 body that is really a refusal (quota message) as refused:
        it is saved as <name>_<date>_refused.<ext> and listed under refused."""
        host = urlparse(url).hostname
        if self.bad.get(host, 0) >= MAX_REFUSED:
            self.refused.append({"source": source, "url": url, "status": "not asked",
                                 "note": f"{host}: {MAX_REFUSED} refused pages in a row earlier in this run"})
            return None
        headers = {"Accept": accept} if accept else {}
        for attempt in (1, 2):
            wait = self.next_ok.get(host, 0) - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self.next_ok[host] = time.monotonic() + MIN_GAP
            try:
                r = self.s.get(url, headers=headers, timeout=TIMEOUT)
            except requests.Timeout:
                if attempt == 1:
                    continue
                return self._refuse(source, url, "timeout", f"timed out twice ({TIMEOUT} s each)", host)
            except requests.ConnectionError as e:
                return self._refuse(source, url, "connection reset", f"{type(e).__name__}: {str(e)[:160]}", host)
            ra = r.headers.get("Retry-After")
            if ra and ra.strip().isdigit():
                self.next_ok[host] = time.monotonic() + max(MIN_GAP, int(ra))
            if r.status_code >= 400:
                return self._refuse(source, url, str(r.status_code),
                                    f"HTTP {r.status_code}" + (f"; Retry-After {ra}" if ra else ""), host)
            RAW.mkdir(parents=True, exist_ok=True)
            err = ok(r.content) if ok else None
            if err:
                (RAW / f"{name}_{TODAY.isoformat()}_refused.{ext}").write_bytes(r.content)
                return self._refuse(source, url, "refused (HTTP 200 body)", err, host)
            self.bad[host] = 0
            (RAW / f"{name}_{TODAY.isoformat()}.{ext}").write_bytes(r.content)
            return r.content
        return None

    @staticmethod
    def latest_raw(name, ext):
        """Newest good raw download of this name on disk (for a source that refused today), with its date, or (None, None)."""
        files = sorted(p for p in RAW.glob(f"{name}_????-??-??.{ext}") if "_refused" not in p.name)
        if not files:
            return None, None
        return files[-1].read_bytes(), files[-1].name[len(name) + 1:len(name) + 11]


# -------------------------------------------------------------------------------------------------------------- series maths
def month_range(a, b):
    y, m = map(int, a.split("-"))
    out = []
    while f"{y:04d}-{m:02d}" <= b:
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def months_between(a, b):
    ya, ma = map(int, a.split("-"))
    yb, mb = map(int, b.split("-"))
    return (yb - ya) * 12 + (mb - ma)


def rebase(obs):
    """obs: {period: native}. Returns (base_mean or None, [[period, native, rebased], ...]) on a full monthly grid."""
    obs = {p: v for p, v in obs.items() if v is not None and p >= START}
    if not obs:
        return None, []
    m2024 = [obs.get(f"2024-{i:02d}") for i in range(1, 13)]
    base = sum(m2024) / 12 if all(v is not None for v in m2024) else None
    rows = []
    for p in month_range(min(obs), max(obs)):
        v = obs.get(p)
        rows.append([p, v, round(v / base * 100, 3) if (v is not None and base) else None])
    return base, rows


def infer_base_year(obs):
    """The calendar year whose 12-month mean is 100 within rounding, if any (what an index with no base attribute tells us)."""
    years = sorted({p[:4] for p in obs})
    for y in years:
        vals = [obs.get(f"{y}-{i:02d}") for i in range(1, 13)]
        if all(v is not None for v in vals) and abs(sum(vals) / 12 - 100) < 0.06:
            return y
    return None


def series(sid, group, country, name_en, name_ar, kind, source, source_series, licence, url, native_base, obs, lag_note=""):
    base, rows = rebase(obs)
    if not rows:
        return None
    first, last = rows[0][0], rows[-1][0]
    lag = months_between(last, TODAY.strftime("%Y-%m"))
    note = f"last point {last}, {lag} month(s) before {TODAY.isoformat()}."
    if base is None:
        note += " Not rebased: the 12 months of 2024 are not all present on one base, so value_2024eq100 is null."
    if lag_note:
        note += " " + lag_note
    return {"id": sid, "group": group, "country": country, "name_en": name_en, "name_ar": name_ar, "kind": kind,
            "source": source, "source_series": source_series, "licence": licence, "url": url, "native_base": native_base,
            "frequency": "M", "first_period": first, "last_period": last, "lag_note": note, "obs": rows}


def summary(label, ss):
    ss = [s for s in ss if s]
    if not ss:
        print(f"{label}: no series")
        return
    for s in ss:
        last = next((r for r in reversed(s["obs"]) if r[1] is not None), None)
        print(f"{label}: {s['id']} {s['first_period']}..{s['last_period']} n={sum(1 for r in s['obs'] if r[1] is not None)} "
              f"last={last[1]} (2024=100: {last[2]})")


# ------------------------------------------------------------------------------------------------------------------- sources
def src_trendx():
    out = []
    if not STORE_INDEX.exists():
        print(f"ours: {STORE_INDEX} missing", file=sys.stderr)
        return out
    rows = list(csv.DictReader(open(STORE_INDEX, encoding="utf-8")))
    for sid, col, name_en, name_ar, extra in [
        ("trendx_index", "trendx_2024eq100_actual_history", "TrendX commodity index (series with real 2024 history)",
         "مؤشر TrendX للسلع (سلاسل التاريخ الحقيقي)", "Geometric mean of the 42 series with real 2024 history."),
        ("trendx_index_all", "trendx_2024eq100_all_series", "TrendX commodity index (all series, carried-back included)",
         "مؤشر TrendX للسلع (كل السلاسل، بما فيها المثبّتة رجوعاً)",
         "Includes 53 series carried back to Jan 2024 (obs_status E); not used for modelling.")]:
        obs = {r["period"]: float(r[col]) for r in rows if r.get(col)}
        m2024 = [obs.get(f"2024-{i:02d}") for i in range(1, 13)]
        mean_note = (f" Arithmetic mean of its 2024 months = {sum(m2024) / 12:.2f}, not exactly 100: the store index is a "
                     "geometric mean across series that are each 2024 = 100, so the store column is kept as is and not "
                     "divided again." if all(v is not None for v in m2024) else "")
        s = series(sid, "ours", "AE-DU", name_en, name_ar, "trendx", "TrendX store (Digital Dubai)", col,
                   "Digital Dubai internal; inputs World Bank Pink Sheet CC BY 4.0, EIA, ECB, own collection",
                   "data/trendx/store/index_2024.csv", "mean of 2024 = 100 per component series", obs,
                   extra + " Already on the 2024 base in the store; native and value_2024eq100 are the same column." + mean_note
                   + " The last month is partial (own collection so far this month).")
        if s:
            for r in s["obs"]:  # already on the target base: keep native == value_2024eq100 exactly
                r[2] = r[1]
            out.append(s)
    summary("ours", out)
    return out


def src_marsa(f):
    src = "GCC-Stat Marsa SDMX"
    out = []
    flows = f.get(MARSA + "dataflow/all/all/latest", "gccstat_dataflows", "xml", src)
    flow = None
    if flows:
        for m in re.finditer(r'<str:Dataflow\b([^>]*)>(.*?)</str:Dataflow>', flows.decode("utf-8"), re.S):
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
            name = re.search(r'<com:Name xml:lang="en">([^<]+)', m.group(2))
            if attrs.get("agencyID") == "GCCSTAT.ES" and re.search(r"consumer price|cpi", (name.group(1) if name else "") + attrs["id"], re.I):
                flow = attrs
                dsd_ref = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r"<Ref\b([^>]*)/>", m.group(2)).group(1)))
                break
    if not flow:
        print("gcc: monthly CPI dataflow of GCCSTAT.ES not found in the registry", file=sys.stderr)
        return out
    ref = f"{flow['agencyID']},{flow['id']},{flow['version']}"
    dsd = f.get(f"{MARSA}datastructure/{dsd_ref['agencyID']}/{dsd_ref['id']}/{dsd_ref['version']}?references=children",
                "gccstat_dsd_cpi", "xml", src)
    dims = []
    if dsd:
        dims = [d for d, _ in sorted(re.findall(r'<str:Dimension [^>]*id="([^"]+)"[^>]*position="(\d+)"', dsd.decode("utf-8")),
                                     key=lambda x: int(x[1]))]
    if dims != ["COUNTRY", "OBS_UNIT", "FREQUENCY", "SUBJECT"]:
        print(f"gcc: unexpected key order {dims}; expected COUNTRY.OBS_UNIT.FREQUENCY.SUBJECT", file=sys.stderr)
        if dims:
            return out
    accept = "application/vnd.sdmx.data+csv;version=1.0.0"
    url_all = f"{MARSA}data/{ref}/{'+'.join(GCC + ['GCC'])}.IDX.M.00"
    url_div = f"{MARSA}data/{ref}/ARE.IDX.M.{'+'.join(f'{i:02d}' for i in range(1, 13))}"
    data = {}
    for url, name in [(url_all, "gccstat_cpi_all_items"), (url_div, "gccstat_cpi_are_divisions")]:
        body = f.get(url, name, "csv", src, accept)
        if not body:
            continue
        for r in csv.DictReader(body.decode("utf-8-sig").splitlines()):
            c = r["COUNTRY:COUNTRY"].split(":")[0]
            subj = r["SUBJECT:INDICATOR"].split(":")[0]
            subj_name = r["SUBJECT:INDICATOR"].split(":", 1)[1].strip().strip('"')
            if r["OBS_UNIT:UNIT"].split(":")[0] != "IDX" or r["FREQUENCY:FREQUENCY"].split(":")[0] != "M":
                continue
            if r["OBS_VALUE:VALUE"] not in ("", None):
                data.setdefault((c, subj, subj_name, url), {})[r["TIME_PERIOD:TIME PERIOD"]] = float(r["OBS_VALUE:VALUE"])
    for (c, subj, subj_name, url), obs in sorted(data.items()):
        by = infer_base_year(obs)
        nb = f"as published by GCC-Stat (no base attribute in the SDMX; inferred base year {by} = 100 from the data)" if by \
            else "as published by GCC-Stat (no base attribute in the SDMX; base year not inferable from the data)"
        if subj == "00":
            s = series(f"gcc_{c.lower()}_cpi", "gcc", c, f"CPI all items, {COUNTRY_EN[c]} (GCC-Stat)",
                       f"الرقم القياسي لأسعار المستهلك، كل البنود، {COUNTRY_AR[c]} (المركز الإحصائي الخليجي)", "cpi", src,
                       f"{ref} / {c}.IDX.M.00 ({subj_name})", LIC_GCCSTAT, url, nb, obs,
                       "GCC-Stat compiles national series; published about 10 months after the reference month.")
        else:
            s = series(f"gcc_are_cpi_{subj}", "gcc", c, f"CPI division {subj} {subj_name}, UAE (GCC-Stat)",
                       f"الرقم القياسي لأسعار المستهلك، القسم {subj} {COICOP_AR.get(subj, subj_name)}، الإمارات (المركز الإحصائي الخليجي)",
                       "cpi", src, f"{ref} / ARE.IDX.M.{subj} ({subj_name})", LIC_GCCSTAT, url, nb, obs,
                       "COICOP division of the UAE federal CPI as compiled by GCC-Stat.")
        if s:
            out.append(s)
    summary("gcc", out)
    return out


def src_wb_gem(f):
    src = "World Bank Global Economic Monitor (GEM)"
    out = []
    for code, label in [("CPTOTNSXN", "not seasonally adjusted"), ("CPTOTSAXN", "seasonally adjusted (fallback)")]:
        data, urls = {}, []
        for y in range(int(START[:4]), TODAY.year + 1):
            periods = ";".join(f"{y}M{m:02d}" for m in range(1, 13))
            url = WB_GEM.format(series=code, time=periods)
            body = f.get(url, f"wb_gem_{code}_{y}", "json", src)
            if not body:
                continue
            urls.append(url)
            try:
                d = json.loads(body)
            except ValueError:
                f.refused.append({"source": src, "url": url, "status": "unreadable", "note": "body is not JSON"})
                continue
            for row in d.get("source", {}).get("data", []):
                var = {v["concept"]: v for v in row["variable"]}
                if row["value"] is None:
                    continue
                t = var["Time"]["id"]  # 2024M01
                data.setdefault(var["Country"]["id"], {})[f"{t[:4]}-{t[5:7]}"] = float(row["value"])
        if not data:
            print(f"wb: {code} returned no values", file=sys.stderr)
            continue
        for c in GCC:
            if c not in data:
                print(f"wb: {code} has no values for {c} (empty in GEM)", file=sys.stderr)
                continue
            by = infer_base_year(data[c])
            nb = (f"as published by GEM (GEM documents its CPI series as 2010 = 100; " +
                  (f"inferred base year from the data: {by})" if by else "not verifiable from the 2015+ window fetched)"))
            out.append(series(f"wb_{c.lower()}_cpi", "gcc", c, f"CPI all items, {COUNTRY_EN[c]} (World Bank GEM, {label})",
                              f"الرقم القياسي لأسعار المستهلك، {COUNTRY_AR[c]} (البنك الدولي GEM، {'غير معدّل موسمياً' if code == 'CPTOTNSXN' else 'معدّل موسمياً'})",
                              "cpi", src, f"source 15 / {code} ({label}), monthly", LIC_WB,
                              WB_GEM.format(series=code, time="<year>M01;...;<year>M12"), nb, data[c], "GEM re-indexes national CPIs; the API's `time/all` only serves the latest months, so "
                                       "the script asks one calendar year of explicit periods per request. "
                                       + ("Fallback to the seasonally adjusted series because the NSA series returned nothing."
                                          if code == "CPTOTSAXN" else "")))
        break
    summary("wb", out)
    return out


def src_imf(f):
    src = "IMF Data, CPI dataflow (SDMX 3.0)"
    out = []
    for c in GCC:
        url = IMF.format(iso3=c)
        body = f.get(url, f"imf_cpi_{c}", "json", src, "application/vnd.sdmx.data+json;version=2.0.0")
        if not body:
            continue
        d = json.loads(body)
        st = d["data"]["structures"][0]
        times = [v["value"] for v in next(x for x in st["dimensions"]["observation"] if x["id"] == "TIME_PERIOD")["values"]]
        attr_ids = [a["id"] for a in st["attributes"]["series"]]
        obs, base_attr = {}, None
        for s in d["data"]["dataSets"][0]["series"].values():
            if "COMMON_REFERENCE_PERIOD" in attr_ids:
                base_attr = s["attributes"][attr_ids.index("COMMON_REFERENCE_PERIOD")]
            for i, o in s["observations"].items():
                if o[0] is not None:
                    t = times[int(i)]  # 1995-M01
                    obs[t.replace("-M", "-")] = float(o[0])
        nb = f"{base_attr[:4]} = 100 (COMMON_REFERENCE_PERIOD = {base_attr})" if base_attr else "not stated"
        out.append(series(f"imf_{c.lower()}_cpi", "gcc", c, f"CPI all items, {COUNTRY_EN[c]} (IMF)",
                          f"الرقم القياسي لأسعار المستهلك، {COUNTRY_AR[c]} (صندوق النقد الدولي)", "cpi", src,
                          f"IMF.STA:CPI / {c}.CPI._T.IX.M", LIC_IMF, url, nb, obs,
                          "Fetched as one small single-series request; no bulk download."))
    summary("imf", out)
    return out


def src_us_cpi(f):
    out = []
    obs, used = {}, []
    body = f.get(FRED, "fred_CPIAUCNS", "csv", "FRED (St. Louis Fed) CPIAUCNS")
    if body:
        for r in csv.DictReader(body.decode("utf-8").splitlines()):
            v = r.get("CPIAUCNS", ".")
            if v not in (".", ""):
                obs[r["observation_date"][:7]] = float(v)
        used.append(f"FRED CPIAUCNS ({len(obs)} months)")
    def bls_ok(body):
        try:
            d = json.loads(body)
        except ValueError:
            return "body is not JSON"
        return None if d.get("status") == "REQUEST_SUCCEEDED" else f"{d.get('status')}: {' '.join(d.get('message', []))[:200]}"

    body = f.get(BLS, "bls_CUUR0000SA0", "json", "BLS public API v1", ok=bls_ok)
    bls_from = "live request today"
    if not body:
        body, date = f.latest_raw("bls_CUUR0000SA0", "json")
        bls_from = f"the live request was refused today; values read from the raw file saved {date}" if body else None
    gaps = []
    if body:
        n = 0
        for r in json.loads(body)["Results"]["series"][0]["data"]:
            if not r["period"].startswith("M") or r["period"] == "M13":
                continue
            if re.fullmatch(r"-?\d+(\.\d+)?", r["value"] or ""):
                obs[f"{r['year']}-{r['period'][1:]}"] = float(r["value"])
                n += 1
            else:
                gaps.append(f"{r['year']}-{r['period'][1:]} ({'; '.join(fn.get('text', '') for fn in r.get('footnotes', []) if fn)})")
        used.append(f"BLS v1 CUUR0000SA0 ({n} months, last three years; {bls_from})")
    if obs:
        fred_note = ("" if len(used) == 2 else
                     " FRED (history before the BLS window) did not answer this run and is listed under refused.")
        gap_note = f" Missing at source: {', '.join(gaps)}." if gaps else ""
        out.append(series("us_cpi_u_nsa", "world", "US", "US CPI-U all items, NSA (BLS CUUR0000SA0)",
                          "الرقم القياسي لأسعار المستهلك الحضري، كل البنود، غير معدّل موسمياً، الولايات المتحدة (BLS)", "cpi",
                          "BLS" + (" + FRED" if len(used) == 2 else ""), "CUUR0000SA0 / CPIAUCNS",
                          LIC_BLS if len(used) == 1 else LIC_BLS + "; " + LIC_FRED, BLS if len(used) == 1 else f"{BLS} ; {FRED}",
                          "1982-84 = 100", obs,
                          "Built from: " + "; ".join(used) + ". BLS v1 serves only the last three years." + fred_note + gap_note))
    summary("us", out)
    return out


def src_eurostat(f):
    out = []
    body = f.get(EUROSTAT, "eurostat_prc_hicp_midx_EA", "json", "Eurostat prc_hicp_midx")
    if body:
        d = json.loads(body)
        ids, size = d["id"], d["size"]
        if any(n != 1 for i, n in zip(ids, size) if i != "time"):
            print("ea: more than one geo/coicop/unit in the Eurostat answer, not parsed", file=sys.stderr)
            return out
        tindex = d["dimension"]["time"]["category"]["index"]
        obs = {p: float(d["value"][str(i)]) for p, i in tindex.items() if str(i) in d["value"]}
        geo = list(d["dimension"]["geo"]["category"]["label"].values())[0]
        out.append(series("ea_hicp", "world", "EA", "Euro area HICP all items (Eurostat prc_hicp_midx, CP00)",
                          "المؤشر المنسق لأسعار المستهلك، كل البنود، منطقة اليورو (يوروستات)", "cpi", "Eurostat",
                          f"prc_hicp_midx / geo=EA ({geo}), coicop=CP00, unit=I15", LIC_EUROSTAT, EUROSTAT, "2015 = 100", obs,
                          f"Dataset 'updated' stamp in the API answer: {d.get('updated')}; the API served nothing after the "
                          f"last period shown here (checked with lastTimePeriod=3 on 9 Nov 2026)."))
    summary("ea", out)
    return out


def src_wb_cmo():
    out = []
    files = sorted(RAW_DIR.glob("WB_CMO-Historical-Data-Monthly_*.xlsx"))
    if not files:
        print("cmo: no WB_CMO-Historical-Data-Monthly_*.xlsx under data/trendx/raw", file=sys.stderr)
        return out
    path = files[-1]
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True)["Monthly Indices"]
    rows = list(ws.iter_rows(values_only=True))
    first_data = next(i for i, r in enumerate(rows) if r[0] and re.fullmatch(r"\d{4}M\d{2}", str(r[0])))
    header_rows = rows[max(0, first_data - 4):first_data]
    norm = lambda s: re.sub(r"\s+", " ", str(s).replace("**", "")).strip().lower()
    cols = {}
    for j in range(1, len(rows[first_data])):
        labels = [norm(h[j]) for h in header_rows if j < len(h) and h[j] and str(h[j]).strip()]
        if labels:
            cols[labels[-1]] = j
    base_note = next((str(r[0]) for r in rows[:first_data] if r[0] and "=100" in str(r[0]).replace(" ", "")), "2010 = 100")
    wanted = [("energy", "wb_cmo_energy", "Energy", "الطاقة"), ("non-energy", "wb_cmo_nonenergy", "Non-energy", "غير الطاقة"),
              ("agriculture", "wb_cmo_agriculture", "Agriculture", "الزراعة"), ("food", "wb_cmo_food", "Food", "الغذاء"),
              ("metals & minerals", "wb_cmo_metals_minerals", "Metals & minerals", "المعادن والخامات"),
              ("precious metals", "wb_cmo_precious_metals", "Precious metals", "المعادن النفيسة")]
    for key, sid, name_en, name_ar in wanted:
        if key not in cols:
            print(f"cmo: column '{key}' not found; header labels: {sorted(cols)}", file=sys.stderr)
            continue
        j = cols[key]
        obs = {}
        for r in rows[first_data:]:
            if r[0] and re.fullmatch(r"\d{4}M\d{2}", str(r[0])) and j < len(r) and isinstance(r[j], (int, float)):
                obs[f"{str(r[0])[:4]}-{str(r[0])[5:7]}"] = float(r[j])
        out.append(series(sid, "world", "WLD", f"World Bank commodity price index: {name_en} (nominal USD)",
                          f"مؤشر البنك الدولي لأسعار السلع: {name_ar} (بالدولار الاسمي)", "commodity_index",
                          "World Bank Commodity Price Data (Pink Sheet)", f"Monthly Indices / {name_en}", LIC_WB,
                          f"https://www.worldbank.org/en/research/commodity-markets (file {path.name} in data/trendx/raw)",
                          f"2010 = 100, nominal US dollars ({base_note})", obs,
                          f"Read from the local Pink Sheet file {path.name}; the monthly file is published in the first week "
                          "of each month with the previous month."))
    summary("cmo", out)
    return out


# ---------------------------------------------------------------------------------------------------------------------- main
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    f = Fetcher()
    all_series = []
    all_series += src_trendx()
    all_series += src_marsa(f)
    all_series += src_wb_gem(f)
    all_series += src_imf(f)
    all_series += src_us_cpi(f)
    all_series += src_eurostat(f)
    all_series += src_wb_cmo()
    # GCC-Stat terms of use: one fetch, quoted in the licence if readable
    terms = f.get(GCCSTAT_TERMS, "gccstat_terms", "html", "GCC-Stat terms of use page")
    if terms:
        text = re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", "", terms.decode("utf-8", "replace"), flags=re.S))
        text = re.sub(r"\s+", " ", text).strip()
        m = re.search(r"(?i)(terms of use.{0,600})", text)
        if m:
            for s in all_series:
                if s["source"].startswith("GCC-Stat"):
                    s["licence"] = "GCC-Stat terms of use: " + m.group(1)[:400]
    all_series = [s for s in all_series if s]
    refused = KNOWN_REFUSED + f.refused
    rebased = sum(1 for s in all_series if any(r[2] is not None for r in s["obs"]))
    doc = {
        "built": TODAY.isoformat(),
        "base": "mean of 2024 = 100",
        "note": ("External price indices beside the TrendX index. value_2024eq100 = native / mean(native, Jan-Dec 2024) * 100, "
                 "only where the 12 months of 2024 exist on one base; otherwise null (see lag_note). Native values and bases "
                 "are kept. obs rows are [period, native, value_2024eq100] on a full monthly grid from 2015-01 or the first "
                 "available month, null where the source has no value. The GCC national portals that refused this machine "
                 "are listed under refused and were not asked. World Bank GEM has no values for Kuwait (KWT). Official "
                 f"Dubai basket data are not part of this file. {len(all_series)} series, {rebased} rebased, "
                 f"{len(refused)} refused entries."),
        "series": all_series,
        "refused": refused,
    }
    (OUT / "benchmarks.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(OUT / "benchmarks.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "period", "native", "value_2024eq100"])
        for s in all_series:
            for p, v, r in s["obs"]:
                w.writerow([s["id"], p, "" if v is None else v, "" if r is None else r])
    print(f"wrote {OUT / 'benchmarks.json'} and benchmarks.csv: {len(all_series)} series, {rebased} rebased to 2024 = 100, "
          f"{len(refused)} refused; raw files under {RAW}")


if __name__ == "__main__":
    main()
