"""Portal: basket normalisation, actor input building, parsers, matching, and a full scrape with a fake Apify."""
import json
import time

import pytest

from portal import scraper

ITEM = scraper.load_basket()[0]          # Tilda basmati 1 kg, barcode 8901144311002


def test_normalize_recomputes_derived_fields():
    d = scraper.normalize_item(dict(ITEM, qty_raw="5 كغ", barcode_raw="8901144311002", gtin="x", qty_total=0))
    assert d["gtin"] == "08901144311002" and d["qty_total"] == 5000.0 and d["match_mode"] == "barcode"
    spec = scraper.normalize_item(dict(ITEM, barcode_raw=""))
    assert spec["barcode_kind"] == "none" and spec["match_mode"] == "spec"
    with pytest.raises(ValueError):
        scraper.normalize_item(dict(ITEM, item_code="abc"))


def test_save_basket_rejects_duplicates(tmp_path):
    with pytest.raises(ValueError):
        scraper.save_basket([ITEM, ITEM], tmp_path / "b.json", tmp_path / "b.csv")
    out = scraper.save_basket([ITEM], tmp_path / "b.json", tmp_path / "b.csv")
    assert json.loads((tmp_path / "b.json").read_text(encoding="utf-8")) == out


def test_build_runs_fills_placeholders():
    actors = scraper.load_actors()
    items = [dict(ITEM, barcode_raw=str(8901144311000 + k)) for k in range(25)]
    runs = scraper.build_runs(actors["carrefour"], items)
    assert len(runs) == 3 and json.loads(runs[0][1]["query"]) == runs[0][0] and len(runs[0][0]) == 10
    lulu = scraper.build_runs(actors["lulu"], items)
    assert lulu[0][1]["startUrls"][0] == {"url": scraper.lulu.search_url(items[0]["barcode_raw"]),
                                         "userData": {"ean": items[0]["barcode_raw"]}}
    assert lulu[0][1]["ignoreCanonicalUrl"] is True


def test_validate_actor():
    good = scraper.load_actors()["carrefour"]
    with pytest.raises(ValueError):
        scraper.validate_actor("carrefour", dict(good, actor="not an actor"))
    with pytest.raises(ValueError):
        scraper.validate_actor("x", dict(good, parser="nope"))
    with pytest.raises(ValueError):
        scraper.validate_actor("lulu", dict(good, mode="search_urls", url_template="https://x/"))


def test_match_rows_statuses():
    other = dict(ITEM, item_code="011110199", barcode_raw="6291100207497")
    third = dict(ITEM, item_code="011110198", barcode_raw="8908001361026")
    rows = [dict(searched_barcode="8901144311002", title="Tilda Pure Basmati Rice 1kg", price=17.5, regular_price=19.0,
                 in_stock=True, url="https://x/p/1")]
    res = scraper.match_rows("carrefour", [ITEM, other, third], rows, searched={"8901144311002", "6291100207497"})
    assert [r["accepted"] for r in res] == ["yes", "no", "no"]
    assert [r["status"] for r in res][1:] == ["not_found", "not_searched"]


def test_generic_parser_nested_fields():
    rows, searched = scraper.parse_generic([{"q": {"code": "8901144311002"}, "name": "T", "cost": 3}], ["8901144311002"],
                                           {"fields": {"searched_barcode": "q.code", "title": "name", "price": "cost"}})
    assert rows[0]["price"] == 3.0 and rows[0]["regular_price"] == 3.0 and searched == {"8901144311002"}


class FakeClient:
    def __init__(self, token):
        pass

    def run(self, actor, actor_input, stop=lambda: False):
        codes = json.loads(actor_input["query"])
        return "run1", [{"searchQuery": c, "title": "Tilda Pure Basmati Rice 1kg", "price": 17.5, "regularPrice": 19,
                         "url": f"https://www.carrefouruae.com/p/{c}", "in_stock": True} for c in codes[:1]]


def test_full_scrape_with_fake_apify(tmp_path, monkeypatch):
    from portal import app as portal
    monkeypatch.setattr(scraper, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(scraper, "get_token", lambda: "t")
    monkeypatch.setattr(portal, "CLIENT_FACTORY", FakeClient)
    c = portal.app.test_client()
    r = c.post("/api/scrape", json={"retailers": ["carrefour"], "item_codes": [ITEM["item_code"], "011110102"]})
    assert r.status_code == 200, r.json
    for _ in range(100):
        if c.get("/api/scrape/status").json["status"] != "running":
            break
        time.sleep(0.05)
    st = c.get("/api/scrape/status").json
    assert st["status"] == "done", st["log"]
    assert st["summary"]["carrefour"]["lines"] == 2 and st["summary"]["carrefour"]["accepted"] == 1
    runs = c.get("/api/runs").json
    rows = c.get(f"/api/runs/{runs[0]['name']}/results").json
    assert rows[0]["status"] == "barcode_search_match" or rows[0]["accepted"] == "yes"
    assert c.get("/api/runs/..%2F..%2Fetc/results").status_code == 404
