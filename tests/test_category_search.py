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
