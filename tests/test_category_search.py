"""Carrefour category crawl through search pages (scripts/scrapling_category.py)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import scrapling_category as sc  # noqa: E402

# the product data Carrefour embeds in a search page (escaped JSON inside a script), two products
PAGE = ('<script>self.__next_f.push([1,"{\\"productId\\":\\"2250157\\",\\"productName\\":\\"Pakistan Veal Cubes Boneless\\",'
        '\\"isSoldByWeight\\":true,\\"productCategory\\":[\\"f1600000\\",\\"f1670000\\",\\"f1670800\\"]},'
        '{\\"productId\\":\\"264677\\",\\"productName\\":\\"Frozen Beef Burger\\",'
        '\\"productCategory\\":[\\"f6000000\\",\\"f6060000\\"]},'
        '{\\"productId\\":\\"999\\",\\"productName\\":\\"No section\\"},'
        '{\\"productId\\":\\"555\\",\\"productCategory\\":[\\"bakery\\",\\"bread\\"]}"])</script>')


def test_sections_are_read_per_product():
    s = sc.carrefour_sections(PAGE)
    assert s["2250157"] == {"f1600000", "f1670000", "f1670800"}
    assert s["264677"] == {"f6000000", "f6060000"}
    assert "999" not in s                      # a product without section data never borrows the next product's
    assert s["555"] == {"bakery", "bread"}


def test_sections_also_read_from_plain_json():
    s = sc.carrefour_sections('{"productId":"1","productCategory":["f1640000"]}')
    assert s == {"1": {"f1640000"}}


def test_category_code_from_url_or_code():
    assert sc.cf_code({"url": "https://www.carrefouruae.com/mafuae/en/c/F1670000?currentPage={page0}"}) == "f1670000"
    assert sc.cf_code({"url": "https://www.carrefouruae.com/mafuae/en/c/bakery?currentPage={page0}"}) == "bakery"
    assert sc.cf_code({"code": "F1640000", "url": ""}) == "f1640000"


def test_search_query_takes_first_alternatives():
    assert sc.search_query({"must_have": ["fresh/chilled", "mutton", "bone-in"]}) == "fresh mutton bone-in"
    assert sc.search_query({"must_have": ["kingfish/kanad fresh"]}) == "kingfish fresh"
    assert sc.search_query({"must_have": ["Tilda", "pure", "basmati", "rice", "extra"]}) == "tilda pure basmati rice"
    assert sc.search_query({"must_have": [], "query_alt": "Banana Philippines"}) == "banana philippines"


class Page:
    def __init__(self, status, body, headers=None):
        self.status, self.body, self.headers = status, body, headers or {}


class Session:
    def __init__(self, pages):
        self.pages, self.urls = list(pages), []

    def get(self, url):
        self.urls.append(url)
        return self.pages.pop(0)


GOOD = "<title>Carrefour UAE</title>" + "carrefouruae " * 3000


def test_refused_page_is_not_read(monkeypatch):
    monkeypatch.setattr(sc.time, "sleep", lambda s: None)
    s = Session([Page(403, "Access Denied"), Page(403, "Access Denied")])
    page, html, ok = sc.get_page(s, "https://www.carrefouruae.com/mafuae/en/search?keyword=x", 0, {})
    assert not ok and page.status == 403 and len(s.urls) == 2      # asked once more (first request of a session), then left unread


def test_first_request_refusal_then_read(monkeypatch):
    monkeypatch.setattr(sc.time, "sleep", lambda s: None)
    s = Session([Page(403, "Access Denied"), Page(200, GOOD)])
    _, _, ok = sc.get_page(s, "https://www.carrefouruae.com/mafuae/en/search?keyword=x", 0, {})
    assert ok


def test_later_refusal_is_not_retried(monkeypatch):
    monkeypatch.setattr(sc.time, "sleep", lambda s: None)
    s = Session([Page(403, "Access Denied")])
    _, _, ok = sc.get_page(s, "https://www.carrefouruae.com/mafuae/en/search?keyword=x", 0, {"warm": True})
    assert not ok and len(s.urls) == 1


def test_retry_after_is_honoured(monkeypatch):
    waits = []
    monkeypatch.setattr(sc.time, "sleep", waits.append)
    s = Session([Page(429, "", {"Retry-After": "7"}), Page(200, GOOD)])
    _, _, ok = sc.get_page(s, "https://www.carrefouruae.com/mafuae/en/search?keyword=x", 0, {"warm": True})
    assert ok and 7.0 in waits


def test_pacing_is_at_least_min_delay(monkeypatch):
    monkeypatch.setattr(sc.time, "sleep", lambda s: None)
    state = {"warm": True}
    before = sc.time.time()
    sc.get_page(Session([Page(200, GOOD)]), "https://www.carrefouruae.com/x", 0.1, state)
    assert state["next"] - before >= sc.MIN_DELAY


def test_blocked_shop_stops_after_five_refusals_and_is_reported(monkeypatch, tmp_path):
    import json
    import types
    monkeypatch.setattr(sc.time, "sleep", lambda s: None)
    calls = []

    class Fake:
        def __init__(self, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            calls.append(url)
            return Page(403, "Access Denied")

    fetchers = types.ModuleType("scrapling.fetchers")
    fetchers.FetcherSession = Fake
    monkeypatch.setitem(sys.modules, "scrapling.fetchers", fetchers)
    monkeypatch.setattr(sc, "carrefour_queries", lambda cats: [f"q{i}" for i in range(20)])
    sc.crawl(tmp_path, 0, {"Meat & Poultry"})
    status = json.loads((tmp_path / "crawl_status.json").read_text())
    log = (tmp_path / "crawl_log.txt").read_text()
    assert len(calls) == 6                                 # 5 refused queries (+1 first-request retry), then no more asking
    assert status["carrefour"]["state"] == "blocked" and status["carrefour"]["read"] == 0
    assert "stopped after 5 refused pages" in log and "15 queries not asked" in log
    assert "0 products from" in log                        # section line still written (portal parser) ...
    assert "carrefour category: 0 pages read, 5 refused" in log   # ... next to the refused count that explains it


def test_lines_of_a_refused_shop_are_not_observed_not_not_found(tmp_path, monkeypatch):
    import csv
    import json
    import panel_run
    cols = ["item_code", "group", "name_ar", "basket_qty", "basket_origin", "spec_en", "retailer", "status", "accepted",
            "title", "price", "regular_price", "unit_price", "price_basis", "origin_seen", "n_candidates",
            "other_candidates", "url", "pin_state"]
    rows = [dict.fromkeys(cols, "") | dict(item_code="011210101", group="0112", name_ar="لحم", retailer=r, status="no_match",
                                            accepted="no", price_basis="kg") for r in ("carrefour", "lulu")]
    with open(tmp_path / "category_matches.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    (tmp_path / "crawl_status.json").write_text(json.dumps({"carrefour": {"read": 0, "refused": 5, "state": "blocked"},
                                                            "lulu": {"read": 300, "refused": 0, "state": "ok"}}))
    monkeypatch.delenv("CPI_CATALOGUE_JSON", raising=False)
    panel_run.main(tmp_path, "2026-11-07T02:49:01+00:00")
    out = json.loads((tmp_path / "panel" / "c000.json").read_text())["rows"]
    st = {r["retailer"]: r["status"] for r in out}
    assert st == {"carrefour": "not_observed", "lulu": "not_found"}


def test_barcode_search_stops_after_refusals_and_reports_blocked(monkeypatch, tmp_path):
    import json
    import types
    import scrapling_search as ssearch
    monkeypatch.setattr(ssearch.time, "sleep", lambda s: None)
    calls = []

    class Fake:
        def __init__(self, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            calls.append(url)
            return Page(403, "Access Denied")

    fetchers = types.ModuleType("scrapling.fetchers")
    fetchers.FetcherSession = Fake
    monkeypatch.setitem(sys.modules, "scrapling.fetchers", fetchers)
    codes = tmp_path / "codes.json"
    codes.write_text(json.dumps([f"890114431{i:04d}" for i in range(30)]))
    monkeypatch.setattr(sys, "argv", ["x", "carrefour", str(tmp_path / "run"), "--codes", str(codes), "--stop-after", "5", "--no-names"])
    ssearch.main()
    assert len(calls) == 5                                  # five refusals, then the shop is not asked again, no retry rounds
    st = json.loads((tmp_path / "run" / "carrefour_status.json").read_text())
    assert st["state"] == "blocked" and st["read"] == 0 and st["failed"] == 30 and st["not_asked"] == 25
    assert len(json.loads((tmp_path / "run" / "carrefour_failed.json").read_text())) == 30   # unread, never "not found"


def test_rebuild_code_writes_files_basket_and_pins(tmp_path):
    import json
    sys.path.insert(0, str(ROOT / "scripts" / "pc"))
    import rebuild_code
    w = tmp_path / "w"
    (w / "system_bundle").mkdir(parents=True)
    (w / "projects/cpi/basket").mkdir(parents=True)
    (w / "projects/cpi/pins").mkdir(parents=True)
    (w / "system_bundle/b0.json").write_text(json.dumps({"data": {"files": {
        "scripts/a.py": "print(1)\n", "cpi/b/c.py": "x = 'é'\n",
        "scripts/catalogue_crawl.py": "def main(out_dir, delay=1.0, only=None):\n    pass\n",
        "scripts/name_live.py": "def run(run_dir, delay=1.2):\n    pass\n"}}}))
    (w / "projects/cpi/basket/b1.json").write_text(json.dumps({"data": {"items": [{"item_code": "1"}]}}))
    (w / "projects/cpi/basket/b2.json").write_text(json.dumps({"items": [{"item_code": "2"}]}))
    (w / "projects/cpi/pins/current.json").write_text(json.dumps({"data": {"pins": {"k": {"url": "u"}}}}))
    rebuild_code.rebuild(str(tmp_path))
    assert (tmp_path / "repo/cpi/b/c.py").read_text(encoding="utf-8") == "x = 'é'\n"
    assert [i["item_code"] for i in json.loads((tmp_path / "repo/data/basket/basket.json").read_text())] == ["1", "2"]
    assert json.loads((tmp_path / "pins.json").read_text()) == {"k": {"url": "u"}}
    assert "delay=2.5" in (tmp_path / "repo/scripts/catalogue_crawl.py").read_text()      # paced at 2.5 s per shop
    assert "delay=2.5" in (tmp_path / "repo/scripts/name_live.py").read_text()


def test_rebuild_code_stops_if_a_pacing_default_moved(tmp_path):
    import json
    sys.path.insert(0, str(ROOT / "scripts" / "pc"))
    import rebuild_code
    (tmp_path / "w/system_bundle").mkdir(parents=True)
    (tmp_path / "w/system_bundle/b0.json").write_text(json.dumps({"files": {
        "scripts/catalogue_crawl.py": "def main(out_dir, delay=0.5):\n    pass\n", "scripts/name_live.py": "def run(run_dir, delay=1.2):\n    pass\n"}}))
    try:
        rebuild_code.rebuild(str(tmp_path), basket=False)
    except SystemExit as e:
        assert "pacing default not found" in str(e)
    else:
        raise AssertionError("must stop")
