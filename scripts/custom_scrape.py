"""Run one of the panel's own scrapers (collection `scrapers` of the Scraping Projects panel) with Scrapling.

    python scripts/custom_scrape.py run <scraper.json> <out dir> [started ISO]   # -> run.json, rows/c000.json ..., log.txt, last.json
    python scripts/custom_scrape.py due <dir of scraper docs> <now ISO>          # the ids to run now, one per line

The scraper document is the one the panel's form saves (target_urls, list_script, details_script, link_selector,
browser_type, wait_until, target_items, active, auto, run_request, last_run ...); a file may also be an ArtifactData
listing entry ({"data": {...}}).

browser_type "http" reads each page with Scrapling's FetcherSession (Chrome's TLS fingerprint, no JavaScript) and shows
the HTML to a local Chromium page that has no network and runs none of the site's own JavaScript; "chromium" opens the
page in headless Chromium (Playwright), waiting for wait_until. Either way list_script and details_script run in the
page (page.evaluate), so one script works in both modes. list_script returns an array of objects; an object's `url` is
visited as a detail page, where details_script returns one object that is merged into the item. When list_script gives
no `url`, the links matched by link_selector are the detail pages (one item each; the list's own objects stay items
too). With only a details script, each target URL is one item. target_items stops the run (0 = no limit).

Polite: one page at a time, at least 2 s (+ up to 1 s) between two requests to the same host; 429 / 503 wait for
Retry-After or 30, 90, 180 s. A page that cannot be read (refused, challenge page, timeout) is logged and counted as
not read, never as an empty result; an item whose detail page was not read keeps its list values and gets
`detail_error`. No challenge solving, no proxy of our own, no stealth tricks. The run is "error" when a listing page
was not read or its script failed, or when more than 5% of the detail pages were not read or more than 5% of them had a
script error; otherwise "done".

Writes into <out dir>, in the panel's storage format (scrapers/<id>/runs/<run id> and .../rows/cNNN):
  run.json        {startedAt, finishedAt, status, count, chunks, log, engine, pages: the counts of new_pages()}
  rows/cNNN.json  {rows: [{...item, source_url, scraped_at}], i}, about 40 KB each
  log.txt         the whole log
  last.json       {last_run, last_scraped, run_request: null}: the update of the scraper document
Prints RUN_ID <id> status <done|error> items <n> chunks <c> pages read <r>, not read <f>, script errors <e>
(read = fetched; not read = could not be fetched; script errors = a script failed on a page that was read).
"""
import json
import logging
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

GAP, JITTER = 2.0, 1.0                 # seconds between two requests to one host
WAITS = (30, 90, 180)                  # waits after a 429 / 503 without Retry-After
MAX_RETRY_AFTER = 600                  # a site asking for a longer pause is left for the next run
PAGE_TIMEOUT = 45
SCRIPT_TIMEOUT = 30
CHUNK = 40_000                         # bytes of JSON per rows document, as panel_run.py and the panel's saveChunks
LOG_KEEP = 200                         # log lines kept in run.json (log.txt has all of them)
DETAIL_FAIL_SHARE = 0.05               # more detail pages than this not read -> the run is an error
WAIT_UNTIL = ("load", "domcontentloaded", "networkidle")
# what a challenge / block page looks like when it comes back with status 200
CHALLENGE = re.compile(r"<title>[^<]{0,80}(just a moment|attention required|access denied|are you a robot|captcha|"
                       r"pardon our interruption|request unsuccessful|security check)[^<]{0,80}</title>|cf_chl_opt|"
                       r"cf-chl-widget|_Incapsula_Resource|px-captcha", re.I)


def now_utc():
    return datetime.now(timezone.utc)


def iso(t):
    return t.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_time(v):
    if not v:
        return None
    try:
        t = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def unwrap(d):
    return d.get("data", d) if isinstance(d.get("data"), dict) else d


# ------------------------------------------------------------ the scraper document
def check(doc):
    """The scraper document with defaults filled in, and the list of problems that stop it from running."""
    d = dict(doc)
    urls = d.get("target_urls") or []
    if isinstance(urls, str):
        urls = urls.splitlines()
    d["target_urls"] = [u.strip() for u in urls if u and u.strip()]
    d["browser_type"] = d.get("browser_type") or "http"
    d["wait_until"] = d.get("wait_until") or "load"
    for k in ("list_script", "details_script", "link_selector"):
        d[k] = (d.get(k) or "").strip()
    problems = []
    try:
        d["target_items"] = int(d.get("target_items") or 0)
        if d["target_items"] < 0:
            raise ValueError
    except (TypeError, ValueError):
        problems.append(f"target_items must be a whole number >= 0, not {doc.get('target_items')!r}")
    if not d["target_urls"]:
        problems.append("no target URL")
    problems += [f"not an http(s) URL: {u}" for u in d["target_urls"] if urlsplit(u).scheme not in ("http", "https")
                 or not urlsplit(u).netloc]
    if d["browser_type"] not in ("http", "chromium"):
        problems.append(f"browser_type must be http or chromium, not {d['browser_type']!r}")
    if d["wait_until"] not in WAIT_UNTIL:
        problems.append(f"wait_until must be one of {', '.join(WAIT_UNTIL)}, not {d['wait_until']!r}")
    if not (d["list_script"] or d["details_script"] or d["link_selector"]):
        problems.append("nothing to collect: no list script, details script or link selector")
    return d, problems


# ------------------------------------------------------------ reading pages
class Pacer:
    """At least `gap` seconds (+ random jitter) from the end of one request to the start of the next, per host."""

    def __init__(self, gap=GAP, jitter=JITTER, sleep=time.sleep, clock=time.monotonic):
        self.gap, self.jitter, self.sleep, self.clock, self.last = gap, jitter, sleep, clock, {}

    def wait(self, url):
        host = urlsplit(url).netloc.lower()
        if host in self.last:
            left = self.last[host] + self.gap + random.uniform(0, self.jitter) - self.clock()
            if left > 0:
                self.sleep(left)

    def done(self, url):
        self.last[urlsplit(url).netloc.lower()] = self.clock()


@dataclass
class Page:
    ok: bool
    url: str
    status: int = 0
    reason: str = ""
    at: str = ""


def retry_after(headers):
    """Seconds asked for by a Retry-After header (a number or an HTTP date), or None."""
    v = (headers or {}).get("retry-after")
    if not v:
        return None
    if str(v).strip().isdigit():
        return max(1, int(v))
    try:
        return max(1, int((parsedate_to_datetime(v) - now_utc()).total_seconds()))
    except (TypeError, ValueError):
        return None


def short(e):
    return str(e).replace("Page.evaluate: ", "").replace("Page.goto: ", "").strip().splitlines()[0][:300] if str(e) else type(e).__name__


def launch(pw):
    """Playwright's own Chromium, or else the newest one under PLAYWRIGHT_BROWSERS_PATH (a preinstalled build)."""
    try:
        return pw.chromium.launch(headless=True)
    except Exception as e:
        if "Executable doesn't exist" not in str(e):
            raise
        missing = e
    root = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or Path.home() / ".cache/ms-playwright")
    version = lambda p: int(re.sub(r"\D", "", p.parts[len(root.parts)]) or 0)
    found = sorted(root.glob("chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"), key=version, reverse=True)
    found += sorted(root.glob("chromium-*/chrome-linux*/chrome"), key=version, reverse=True)
    if not found:
        raise missing
    return pw.chromium.launch(headless=True, executable_path=str(found[0]))


class Reader:
    """One Chromium page for the scripts; pages come from Scrapling (http) or from Chromium itself (chromium)."""

    def __init__(self, mode="http", wait_until="load", pacer=None, log=print, timeout=PAGE_TIMEOUT):
        self.mode, self.wait_until, self.log, self.timeout = mode, wait_until, log, timeout
        self.pacer = pacer or Pacer()
        self.doc = None                                  # (url, body, content type) the local page serves in http mode
        self.forms = {}                                  # script -> True when it is an expression, False for a body

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self.pw = sync_playwright().start()
        self.browser = launch(self.pw)
        ctx = self.browser.new_context(service_workers="block")
        self.page = ctx.new_page()
        if self.mode == "http":
            from scrapling.fetchers import FetcherSession
            logging.getLogger("scrapling").setLevel(logging.WARNING)
            self.session = FetcherSession(impersonate="chrome", stealthy_headers=False, retries=1,
                                          timeout=self.timeout).__enter__()
            self.page.route("**/*", self._serve)
        else:
            self.page.route("**/*", self._light)
        return self

    def __exit__(self, *exc):
        if self.mode == "http":
            self.session.__exit__(*exc)
        self.browser.close()
        self.pw.stop()

    def _serve(self, route):
        """http mode: the fetched HTML is the only thing the local page may load; scripts of the site are blocked."""
        r = route.request
        if self.doc and r.is_navigation_request() and r.url.split("#")[0] == self.doc[0].split("#")[0]:
            route.fulfill(status=200, body=self.doc[1], headers={
                "content-type": self.doc[2], "content-security-policy": "script-src 'none'; object-src 'none'; frame-src 'none'"})
        else:
            route.abort()

    @staticmethod
    def _light(route):
        # pictures, video and fonts are not needed to read a page; skipping them spares the site
        if route.request.resource_type in ("image", "media", "font"):
            route.abort()
        else:
            route.continue_()

    def _fetch(self, url):
        """One request: (status, final url, headers, body, encoding)."""
        if self.mode == "http":
            p = self.session.get(url, timeout=self.timeout)
            return p.status, str(p.url or url), p.headers or {}, p.body or b"", p.encoding or "utf-8"
        resp = self.page.goto(url, wait_until=self.wait_until, timeout=self.timeout * 1000)
        return (resp.status if resp else 200), self.page.url, (resp.headers if resp else {}), self.page.content(), ""

    def read(self, url):
        """Load `url` into the page; Page.ok False (with the reason) when it could not be read."""
        for attempt in range(len(WAITS) + 1):
            self.pacer.wait(url)
            try:
                status, final, headers, body, enc = self._fetch(url)
                err = ""
            except Exception as e:
                status, err = 0, short(e)
            finally:
                self.pacer.done(url)
            if err:
                if attempt == 0:
                    self.log(f"{url}: {err}; trying again in {WAITS[0]} s")
                    self.pacer.sleep(WAITS[0])
                    continue
                return Page(False, url, 0, err)
            if status in (429, 503):
                wait = retry_after(headers)
                if attempt == len(WAITS) or (wait or 0) > MAX_RETRY_AFTER:
                    return Page(False, url, status, f"HTTP {status}" + (f", asks to wait {wait} s" if wait else ", still refused after 3 waits"))
                wait = wait or WAITS[attempt]
                self.log(f"{url}: HTTP {status}, waiting {wait} s")
                self.pacer.sleep(wait)
                continue
            if status >= 400:
                return Page(False, url, status, f"HTTP {status}")
            text = body.decode(enc or "utf-8", "replace") if isinstance(body, bytes) else body
            if CHALLENGE.search(text[:200_000]):
                return Page(False, url, status, "a challenge / block page (not solved)")
            at = iso(now_utc())
            if self.mode == "http":
                try:
                    self._show(final, body, headers.get("content-type") or "text/html", enc)
                except Exception as e:
                    return Page(False, url, status, f"could not show the page to Chromium: {short(e)}")
            return Page(True, final, status, "", at)

    def _show(self, url, body, ctype, enc):
        if "charset" not in ctype.lower() and ctype.lower().startswith("text/"):
            ctype += f"; charset={enc or 'utf-8'}"
        self.doc = (url, body if isinstance(body, bytes) else body.encode("utf-8"), ctype)
        self.page.goto(url, wait_until="load", timeout=self.timeout * 1000)

    def run(self, script):
        """Run a script in the page once: (value, error). The script is an expression or a function (`[...]`,
        `() => ...`, `function pageFunction(context) {...}`, which is called), or else a function body ending in
        `return ...`."""
        try:
            if script not in self.forms:
                self.forms[script] = self._parses(wrap(script, expression=True))
            return self.page.evaluate(wrap(script, self.forms[script]), SCRIPT_TIMEOUT), ""
        except Exception as e:
            return None, short(e)

    def _parses(self, fn):
        """Whether `fn` compiles; it is only defined, never called, so nothing of the script runs."""
        try:
            return self.page.evaluate(f"() => {{ const __unused = {fn}; return true; }}") is True
        except Exception:
            return False

    def links(self, selector):
        """Absolute http(s) hrefs of the elements matched by `selector`, in page order, without duplicates."""
        hrefs = self.page.evaluate("""(sel) => [...document.querySelectorAll(sel)].map((a) => {
            const h = a.href || a.getAttribute('href') || '';
            try { return h ? new URL(h, location.href).href : ''; } catch (e) { return ''; } })""", selector)
        out = []
        for h in hrefs:
            h = h.split("#")[0]
            if urlsplit(h).scheme in ("http", "https") and h not in out:
                out.append(h)
        return out


def wrap(script, expression=False):
    body = (f"const __v = (\n{script.rstrip().rstrip(';')}\n);\nreturn typeof __v === 'function' ? await __v(__ctx) : __v;"
            if expression else script)
    return ("async (t) => {\nconst __ctx = { url: location.href, request: { url: location.href } };\n"
            f"const __run = async () => {{\n{body}\n}};\n"
            "return await Promise.race([__run(), new Promise((_, no) => setTimeout(() => "
            "no(new Error(`the script did not finish in ${t} s`)), t * 1000))]);\n}")


# ------------------------------------------------------------ a run
def as_items(v):
    """list_script's value -> (objects, note)."""
    if v is None:
        return [], "returned nothing"
    if isinstance(v, dict):
        v = [v]
    if not isinstance(v, list):
        return [], f"returned a {type(v).__name__}, not an array of objects"
    items = [x for x in v if isinstance(x, dict)]
    return items, (f"{len(v) - len(items)} entries that are not objects were skipped" if len(items) < len(v) else "")


def detail_url(item, base):
    u = item.get("url")
    if not isinstance(u, str) or not u.strip():
        return ""
    u = urljoin(base, u.strip())
    return u if urlsplit(u).scheme in ("http", "https") else ""


def scrape(doc, reader, log):
    """Listing pages, then detail pages -> (rows, page counts)."""
    limit, lst, det, sel = doc["target_items"], doc["list_script"], doc["details_script"], doc["link_selector"]
    full = lambda: limit and len(found) >= limit
    pages = new_pages()
    found = []                                            # [item, source url, read at, detail url]
    seen = {}                                             # detail url -> details() result, each page read once
    for url in doc["target_urls"]:
        if full():
            break
        page = reader.read(url)
        if not page.ok:
            pages["list_not_read"] += 1
            log(f"NOT READ listing {url}: {page.reason}")
            continue
        got = []
        if lst:
            v, err = reader.run(lst)
            if err:
                pages["list_read"] += 1
                pages["list_script_errors"] += 1
                log(f"SCRIPT ERROR list_script on {page.url}: {err}")
                continue
            got, note = as_items(v)
            for it in got:
                found.append([it, page.url, page.at, detail_url(it, page.url) if det else ""])
            log(f"listing {page.url}: {len(got)} items" + (f" ({note})" if note else ""))
        if sel and not any(detail_url(it, page.url) for it in got):
            try:
                hrefs = reader.links(sel)
            except Exception as e:
                pages["list_read"] += 1
                pages["list_script_errors"] += 1
                log(f"SCRIPT ERROR link_selector {sel!r} on {page.url}: {short(e)}")
                continue
            found += [[{"url": h}, page.url, page.at, h if det else ""] for h in hrefs]
            log(f"listing {page.url}: {len(hrefs)} links matched by {sel!r}")
        if not lst and not sel:                           # only a details script: the target page is the item
            found.append([{}, page.url, page.at, page.url])
            seen[page.url] = details(reader, det, None, log, pages, page.url, page.at)
        pages["list_read"] += 1
    if limit:
        del found[limit:]
    rows = []
    for it, src, at, du in found:
        row = dict(it)
        if du and du not in seen:
            seen[du] = details(reader, det, du, log, pages)
        if du:
            ok, data, dsrc, dat, reason = seen[du]
            if ok:
                row.update(data)
                src, at = dsrc, dat
            else:
                row["detail_error"] = reason
        row["source_url"], row["scraped_at"] = src, at
        rows.append(row)
    return rows, pages


def details(reader, script, url, log, pages, here="", at=""):
    """Read one detail page (or use the page already loaded) and run details_script: (ok, object, url, at, reason)."""
    if url:
        page = reader.read(url)
        if not page.ok:
            pages["detail_not_read"] += 1
            log(f"NOT READ detail {url}: {page.reason}")
            return False, {}, url, "", f"not read: {page.reason}"
        here, at = page.url, page.at
    v, err = reader.run(script)
    if not err and isinstance(v, list) and len(v) == 1 and isinstance(v[0], dict):
        v = v[0]
    if not err and v is not None and not isinstance(v, dict):
        err = f"returned a {type(v).__name__}, not an object"
    if url:
        pages["detail_read"] += 1
    if err:
        pages["detail_script_errors"] += 1
        log(f"SCRIPT ERROR details_script on {here}: {err}")
        return False, {}, here, at, f"script error: {err}"
    if v is None:
        log(f"detail {here}: details_script returned nothing")
    return True, v or {}, here, at, ""


def new_pages():
    """Pages fetched (read), pages that could not be fetched (not read) and script errors on pages that were read."""
    return dict(list_read=0, list_not_read=0, list_script_errors=0, detail_read=0, detail_not_read=0, detail_script_errors=0)


def status_of(pages):
    """'error' when a listing page was not read or its script failed, or more than 5% of the detail pages were not
    read or their script failed (either way those items lack their detail values); else 'done'."""
    if pages["list_not_read"] or pages["list_script_errors"] or not pages["list_read"]:
        return "error"
    tried = pages["detail_read"] + pages["detail_not_read"]
    bad = pages["detail_not_read"] > DETAIL_FAIL_SHARE * tried
    broken = pages["detail_script_errors"] > DETAIL_FAIL_SHARE * pages["detail_read"]
    return "error" if bad or broken else "done"


def summary(pages):
    return (f"pages read {pages['list_read'] + pages['detail_read']}, not read "
            f"{pages['list_not_read'] + pages['detail_not_read']}, script errors "
            f"{pages['list_script_errors'] + pages['detail_script_errors']}")


def chunks_of(rows):
    out, cur, size = [], [], 0
    for r in rows:
        s = len(json.dumps(r, ensure_ascii=False, default=str))
        if size + s > CHUNK and cur:
            out.append(cur)
            cur, size = [], 0
        cur.append(r)
        size += s
    out.append(cur)
    return out


class Log:
    def __init__(self, path):
        self.lines, self.f = [], open(path, "w", encoding="utf-8")

    def __call__(self, msg):
        line = f"{now_utc().strftime('%H:%M:%S')} {msg}"
        self.lines.append(line)
        self.f.write(line + "\n")
        self.f.flush()
        print(line, file=sys.stderr)


def run(doc, out, pacer=None, started=None):
    """Run one scraper document into `out`; returns run.json's content (plus run_id)."""
    out = Path(out)
    (out / "rows").mkdir(parents=True, exist_ok=True)
    for f in (out / "rows").glob("c*.json"):
        f.unlink()
    started = started or now_utc()
    run_id = started.astimezone(timezone.utc).strftime("%Y%m%dT%H%M") + "-auto"
    log = Log(out / "log.txt")
    doc, problems = check(unwrap(doc))
    log(f"scraper {doc.get('map_name') or doc.get('name') or '?'}: {len(doc['target_urls'])} target URLs, "
        f"{doc['browser_type']}" + (f" (wait until {doc['wait_until']})" if doc["browser_type"] == "chromium" else "")
        + f", target items {doc.get('target_items') or 'no limit'}")
    pages = new_pages()
    rows = []
    if problems:
        for p in problems:
            log(f"PROBLEM {p}")
    else:
        try:
            with Reader(doc["browser_type"], doc["wait_until"], pacer, log) as reader:
                rows, pages = scrape(doc, reader, log)
        except Exception as e:                            # the browser itself failed: keep what the log says
            log(f"ERROR {short(e)}")
            pages["list_not_read"] += 1
    status = "error" if problems else status_of(pages)
    log(f"{len(rows)} items; {summary(pages)}; status {status}")
    if not rows and status == "done":
        log("WARNING every page was read but the scripts found no items")
    chunks = chunks_of(rows)
    for i, c in enumerate(chunks):
        (out / "rows" / f"c{i:03d}.json").write_text(json.dumps({"rows": c, "i": i}, ensure_ascii=False, default=str), encoding="utf-8")
    finished = iso(now_utc())
    doc_run = dict(startedAt=iso(started), finishedAt=finished, status=status, count=len(rows), chunks=len(chunks),
                   log=log.lines[-LOG_KEEP:], engine="scrapling", pages=pages)
    (out / "run.json").write_text(json.dumps(doc_run, ensure_ascii=False), encoding="utf-8")
    (out / "last.json").write_text(json.dumps(dict(
        last_run=dict(at=iso(started), status=status, items=len(rows), run_id=run_id), last_scraped=len(rows),
        run_request=None), ensure_ascii=False), encoding="utf-8")
    log.f.close()
    return dict(doc_run, run_id=run_id)


# ------------------------------------------------------------ which scrapers are due
def zone(tz):
    """'Asia/Dubai' or the form's label '(GMT+04:00) Asia/Dubai'."""
    m = re.search(r"[A-Za-z_]+/[A-Za-z_+\-/]+|UTC", tz or "")
    try:
        return ZoneInfo(m.group(0)) if m else ZoneInfo("Asia/Dubai")
    except Exception:
        return ZoneInfo("Asia/Dubai")


def due_reason(doc, now):
    """Why this scraper should run now, or '' (see the README of the routine: docs/routines/custom_scrapers.md)."""
    if doc.get("active", True) is False or doc.get("engine") != "scrapling":
        return ""
    last = doc.get("last_run") or {}
    last_at = parse_time(last.get("at"))
    if last.get("status") == "running" and last_at:
        if now - last_at < timedelta(hours=3):
            return ""                                     # another session is on it
        last_at = None                                    # that session died: the run never happened
    req = doc.get("run_request")
    if req:
        req_at = parse_time(req.get("at")) if isinstance(req, dict) else None
        if not last_at or not req_at or req_at > last_at:
            return "run now"
    auto = doc.get("auto") or {}
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", str(auto.get("run_at") or "").strip())
    if not auto.get("enabled") or not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        return ""
    local = now.astimezone(zone(auto.get("tz")))
    slot = local.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
    if local >= slot:
        return f"auto {auto['run_at']}" if not last_at or last_at < slot else ""
    # a slot just before midnight, missed by the last hourly check of the day
    slot -= timedelta(days=1)
    created = parse_time(doc.get("created_at"))
    if local - slot <= timedelta(hours=2) and (not last_at or last_at < slot) and (not created or created <= slot):
        return f"auto {auto['run_at']} (yesterday)"
    return ""


def due(folder, now):
    out = []
    for f in sorted(Path(folder).glob("*.json")):
        raw = json.loads(f.read_text(encoding="utf-8"))
        doc = unwrap(raw)
        why = due_reason(doc, now)
        if why:
            out.append((raw.get("id") or doc.get("map_name") or f.stem, why))
    return out


def main(argv):
    if len(argv) in (3, 4) and argv[0] == "run":
        doc = unwrap(json.loads(Path(argv[1]).read_text(encoding="utf-8")))
        if doc.get("engine", "scrapling") != "scrapling":
            sys.exit(f"{argv[1]}: engine {doc.get('engine')!r}; this script runs Scrapling scrapers only")
        if doc.get("active", True) is False:
            sys.exit(f"{argv[1]}: the scraper is not active")
        started = parse_time(argv[3]) if len(argv) == 4 else None
        if len(argv) == 4 and not started:
            sys.exit(f"not an ISO time: {argv[3]}")
        r = run(doc, argv[2], started=started)
        print("RUN_ID", r["run_id"], "status", r["status"], "items", r["count"], "chunks", r["chunks"], summary(r["pages"]))
        return
    if len(argv) == 3 and argv[0] == "due":
        now = parse_time(argv[2])
        if not now:
            sys.exit(f"not an ISO time: {argv[2]}")
        for i, why in due(argv[1], now):
            print(i)
            print(f"{i}: {why}", file=sys.stderr)
        return
    sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
