"""scripts/custom_scrape.py without the network: pages come from a local http.server on 127.0.0.1."""
import json
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import custom_scrape as cs  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore:The 'strip_cdata' option:DeprecationWarning")   # inside Scrapling

LIST = """<html><head><title>Shop</title>
<script>document.addEventListener('DOMContentLoaded', () => {
  const li = document.createElement('li'); li.className = 'p';
  li.innerHTML = '<a href="/item/js">Made by the site script</a><span class="price">9.00</span>';
  document.querySelector('ul').appendChild(li); });</script>
<script src="/app.js"></script></head>
<body><img src="/pic.png"><ul>
<li class="p"><a href="/item/1">Tea</a><span class="price">3.50</span></li>
<li class="p"><a href="/item/2">Rice</a><span class="price">12.00</span></li>
<li class="p"><a href="item/3">Milk</a><span class="price">6.25</span></li>
</ul></body></html>"""
ITEM = "<html><body><h1>{n}</h1><table><tr><th>UPC</th><td>upc-{n}</td></tr></table></body></html>"
LIST_SCRIPT = """return [...document.querySelectorAll('li.p')].map((li) => ({
  title: li.querySelector('a').textContent, price: li.querySelector('.price').textContent,
  url: li.querySelector('a').getAttribute('href') }));"""
DETAILS_SCRIPT = "return { upc: document.querySelector('td').textContent };"


class Site(BaseHTTPRequestHandler):
    hits = []
    busy = {}                                   # path -> how many more 429s to send

    def do_GET(self):
        Site.hits.append(self.path)
        path = self.path.split("?")[0]
        if Site.busy.get(path):
            Site.busy[path] -= 1
            return self.reply(429, "busy", {"Retry-After": "1"})
        if path == "/list":
            return self.reply(200, LIST)
        if path == "/list-busy":
            return self.reply(503, "down")
        if path == "/challenge":
            return self.reply(200, "<html><head><title>Just a moment...</title></head><body></body></html>")
        if path.startswith("/item/"):
            if "forbid" in self.path:
                return self.reply(403, "no")
            return self.reply(200, ITEM.format(n=path.rsplit("/", 1)[1]))
        return self.reply(404, "not here")

    def reply(self, status, body, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def site():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Site)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture(scope="module")
def chromium():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            cs.launch(pw).close()
    except Exception as e:                      # no browser in this environment
        pytest.skip(f"Chromium is not available: {e}")


class FakeSleep:
    def __init__(self):
        self.waits = []

    def __call__(self, s):
        self.waits.append(s)


def quick():
    sleep = FakeSleep()
    return cs.Pacer(gap=0, jitter=0, sleep=sleep), sleep


def scraper(site, **kw):
    d = dict(name="Test", engine="scrapling", map_name="test", browser_type="http", wait_until="load",
             link_selector="", target_urls=[site + "/list"], list_script=LIST_SCRIPT, details_script=DETAILS_SCRIPT,
             target_items=0, active=True)
    d.update(kw)
    return d


def rows_of(out):
    return [r for f in sorted((Path(out) / "rows").glob("c*.json")) for r in json.loads(f.read_text())["rows"]]


# ---- the document ------------------------------------------------------------------------------------------
def test_check_fills_defaults_and_lists_problems():
    d, problems = cs.check(dict(target_urls="https://a.test/x\n\n  https://b.test/y ", list_script="return []"))
    assert problems == [] and d["target_urls"] == ["https://a.test/x", "https://b.test/y"]
    assert (d["browser_type"], d["wait_until"], d["target_items"]) == ("http", "load", 0)
    _, problems = cs.check(dict(target_urls=["ftp://a.test/x"], browser_type="firefox", wait_until="idle",
                                target_items="-3"))
    assert len(problems) == 5          # url, browser, wait_until, target_items, nothing to collect


# ---- politeness --------------------------------------------------------------------------------------------
def test_pacer_keeps_two_seconds_per_host():
    t = [100.0]
    sleep = lambda s: t.__setitem__(0, t[0] + s)
    p = cs.Pacer(gap=2, jitter=1, sleep=sleep, clock=lambda: t[0])
    p.wait("https://a.test/1"), p.done("https://a.test/1")
    start = t[0]
    p.wait("https://a.test/2")
    assert 2 <= t[0] - start <= 3
    before = t[0]
    p.wait("https://b.test/1")         # another host does not wait
    assert t[0] == before


def test_retry_after_seconds_and_date():
    assert cs.retry_after({"retry-after": "7"}) == 7
    later = datetime.now(timezone.utc).timestamp() + 120
    from email.utils import formatdate
    assert 100 <= cs.retry_after({"retry-after": formatdate(later, usegmt=True)}) <= 121
    assert cs.retry_after({}) is None and cs.retry_after({"retry-after": "soon"}) is None


def test_chunks_stay_near_40_kb():
    rows = [{"title": "x" * 1000, "i": i} for i in range(100)]
    chunks = cs.chunks_of(rows)
    assert sum(len(c) for c in chunks) == 100 and len(chunks) == 3
    assert all(len(json.dumps(c)) <= 41_000 for c in chunks)
    assert cs.chunks_of([]) == [[]]


# ---- due ---------------------------------------------------------------------------------------------------
NOW = datetime(2026, 11, 3, 4, 10, tzinfo=timezone.utc)          # 08:10 in Dubai


def doc(**kw):
    d = dict(engine="scrapling", active=True, auto=dict(enabled=False, run_at="06:30", tz="Asia/Dubai"),
             run_request=None, last_run=None)
    d.update(kw)
    return d


def test_due_run_request_newer_than_last_run():
    assert cs.due_reason(doc(run_request={"at": "2026-11-03T04:00:00Z"}), NOW) == "run now"
    last = {"at": "2026-11-03T04:05:00Z", "status": "done"}
    assert cs.due_reason(doc(run_request={"at": "2026-11-03T04:00:00Z"}, last_run=last), NOW) == ""
    assert cs.due_reason(doc(run_request={"at": "2026-11-03T04:06:00Z"}, last_run=last), NOW) == "run now"


def test_due_skips_inactive_apify_and_running():
    req = {"at": "2026-11-03T04:00:00Z"}
    assert cs.due_reason(doc(run_request=req, active=False), NOW) == ""
    assert cs.due_reason(doc(run_request=req, engine="apify"), NOW) == ""
    running = {"at": "2026-11-03T03:00:00Z", "status": "running"}
    assert cs.due_reason(doc(run_request={"at": "2026-11-03T03:30:00Z"}, last_run=running), NOW) == ""
    stale = {"at": "2026-11-02T20:00:00Z", "status": "running"}            # a session that died 8 h ago
    assert cs.due_reason(doc(run_request={"at": "2026-11-02T19:00:00Z"}, last_run=stale), NOW) == "run now"


def test_due_auto_trigger_in_its_time_zone():
    auto = dict(enabled=True, run_at="06:30", tz="(GMT+04:00) Asia/Dubai")
    assert cs.due_reason(doc(auto=auto), NOW) == "auto 06:30"
    ran = {"at": "2026-11-03T02:31:00Z", "status": "done"}                # 06:31 Dubai today
    assert cs.due_reason(doc(auto=auto, last_run=ran), NOW) == ""
    before = {"at": "2026-11-03T01:00:00Z", "status": "done"}             # a manual run at 05:00, before the slot
    assert cs.due_reason(doc(auto=auto, last_run=before), NOW) == "auto 06:30"
    assert cs.due_reason(doc(auto=dict(auto, run_at="09:00")), NOW) == ""   # not yet today
    assert cs.due_reason(doc(auto=dict(auto, enabled=False)), NOW) == ""


def test_due_slot_just_before_midnight():
    auto = dict(enabled=True, run_at="23:50", tz="Asia/Dubai")
    after_midnight = datetime(2026, 11, 3, 20, 20, tzinfo=timezone.utc)   # 00:20 Dubai on 4 Nov
    assert cs.due_reason(doc(auto=auto, created_at="2026-10-01T00:00:00Z"), after_midnight) == "auto 23:50 (yesterday)"
    assert cs.due_reason(doc(auto=auto, created_at="2026-11-03T20:00:00Z"), after_midnight) == ""


def test_due_folder_lists_ids(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps({"id": "a", "data": doc(run_request={"at": "2026-11-03T04:00:00Z"})}))
    (tmp_path / "b.json").write_text(json.dumps(doc()))
    assert cs.due(tmp_path, NOW) == [("a", "run now")]


# ---- runs against the local site ---------------------------------------------------------------------------
def test_http_run_lists_details_and_writes_the_panel_format(site, chromium, tmp_path):
    pacer, _ = quick()
    r = cs.run(scraper(site), tmp_path, pacer)
    rows = rows_of(tmp_path)
    assert r["status"] == "done" and r["count"] == 3 == len(rows)
    assert [x["title"] for x in rows] == ["Tea", "Rice", "Milk"]          # the site's own script did not run
    assert rows[2]["upc"] == "upc-3" and rows[2]["source_url"] == site + "/item/3"   # relative link resolved
    assert rows[0]["price"] == "3.50" and rows[0]["scraped_at"].endswith("+00:00")
    run = json.loads((tmp_path / "run.json").read_text())
    assert {"startedAt", "finishedAt", "status", "count", "chunks", "log", "engine"} <= set(run)
    assert run["engine"] == "scrapling" and run["chunks"] == 1 and run["pages"]["detail_read"] == 3
    assert json.loads((tmp_path / "rows/c000.json").read_text())["i"] == 0
    last = json.loads((tmp_path / "last.json").read_text())
    assert last["last_run"]["items"] == 3 and last["last_scraped"] == 3 and last["run_request"] is None
    assert "3 items" in (tmp_path / "log.txt").read_text()


def test_http_mode_loads_nothing_but_the_page(site, chromium, tmp_path):
    Site.hits.clear()
    cs.run(scraper(site, details_script=""), tmp_path, quick()[0])
    assert Site.hits == ["/list"]                                          # no script, picture or detail request


def test_a_script_that_never_ends_is_stopped(site, chromium, tmp_path, monkeypatch):
    monkeypatch.setattr(cs, "SCRIPT_TIMEOUT", 1)
    r = cs.run(scraper(site, list_script="await new Promise(() => {}); return []"), tmp_path, quick()[0])
    assert r["status"] == "error" and "did not finish in 1 s" in (tmp_path / "log.txt").read_text()


def test_target_items_stops_the_run(site, chromium, tmp_path):
    Site.hits.clear()
    r = cs.run(scraper(site, target_items=2), tmp_path, quick()[0])
    assert r["count"] == 2 and not any(h.startswith("/item/3") for h in Site.hits)


def test_chromium_runs_the_site_and_waits(site, chromium, tmp_path):
    r = cs.run(scraper(site, browser_type="chromium", wait_until="domcontentloaded", details_script=""), tmp_path, quick()[0])
    titles = [x["title"] for x in rows_of(tmp_path)]
    assert r["status"] == "done" and "Made by the site script" in titles and len(titles) == 4


def test_429_waits_for_retry_after(site, chromium, tmp_path):
    Site.busy["/item/1"] = 1
    pacer, sleep = quick()
    r = cs.run(scraper(site), tmp_path, pacer)
    assert r["status"] == "done" and r["count"] == 3 and 1 in sleep.waits
    assert "HTTP 429, waiting 1 s" in (tmp_path / "log.txt").read_text()


def test_503_three_waits_then_not_read(site, chromium, tmp_path):
    pacer, sleep = quick()
    r = cs.run(scraper(site, target_urls=[site + "/list-busy", site + "/list"]), tmp_path, pacer)
    assert sleep.waits[:3] == [30, 90, 180]
    assert r["status"] == "error" and r["count"] == 3                      # the second listing was still read
    assert r["pages"]["list_not_read"] == 1
    assert "NOT READ listing" in (tmp_path / "log.txt").read_text()


def test_refused_and_challenge_pages_are_not_empty_results(site, chromium, tmp_path):
    r = cs.run(scraper(site, target_urls=[site + "/challenge"]), tmp_path, quick()[0])
    assert r["status"] == "error" and r["count"] == 0
    assert "challenge" in (tmp_path / "log.txt").read_text()
    script = "return [{title: 'a', url: '/item/1'}, {title: 'b', url: '/item/2?forbid=1'}]"
    r = cs.run(scraper(site, list_script=script), tmp_path, quick()[0])
    rows = rows_of(tmp_path)
    assert r["status"] == "error" and rows[1]["detail_error"] == "not read: HTTP 403" and "upc" not in rows[1]
    assert rows[1]["source_url"] == site + "/list" and rows[0]["upc"] == "upc-1"


def test_script_errors_are_caught_per_page(site, chromium, tmp_path):
    script = "if (location.pathname === '/list') throw new Error('boom'); return [{title: 'x'}]"
    r = cs.run(scraper(site, target_urls=[site + "/list", site + "/item/5"], list_script=script, details_script=""),
               tmp_path, quick()[0])
    assert r["count"] == 1 and r["status"] == "error" and r["pages"]["script_errors"] == 1
    assert "SCRIPT ERROR list_script" in (tmp_path / "log.txt").read_text() and "boom" in (tmp_path / "log.txt").read_text()


def test_link_selector_when_the_list_script_gives_no_urls(site, chromium, tmp_path):
    r = cs.run(scraper(site, list_script="return []", link_selector="li.p a"), tmp_path, quick()[0])
    rows = rows_of(tmp_path)
    assert r["count"] == 3 and [x["url"] for x in rows] == [site + "/item/1", site + "/item/2", site + "/item/3"]
    assert rows[1]["upc"] == "upc-2"


def test_expression_scripts_and_details_only(site, chromium, tmp_path):
    expr = "[...document.querySelectorAll('li.p a')].map((a) => ({ title: a.textContent }))"
    r = cs.run(scraper(site, list_script=expr, details_script=""), tmp_path, quick()[0])
    assert r["count"] == 3
    fn = "function pageFunction(context) { return { h1: document.querySelector('h1').textContent, at: context.request.url }; }"
    r = cs.run(scraper(site, target_urls=[site + "/item/7"], list_script="", details_script=fn), tmp_path, quick()[0])
    rows = rows_of(tmp_path)
    assert r["count"] == 1 and rows[0]["h1"] == "7" and rows[0]["source_url"] == site + "/item/7"


def test_bad_document_is_an_error_run(tmp_path):
    r = cs.run(dict(target_urls=["notaurl"], list_script="return []"), tmp_path)
    assert r["status"] == "error" and r["count"] == 0 and "PROBLEM" in (tmp_path / "log.txt").read_text()
