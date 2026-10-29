"""Offline tests for the SPPI parsers. Fixtures are cut from the pages fetched on 2026-10-29."""
import json
from pathlib import Path

import pytest

from sppi.fetch import Net, is_bot_wall
from sppi.parse import money_values, table_grid, to_number
from sppi.sources import megayachts, oracle, pinas, probe, rta, ups

FIX = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parent.parent


def read(name):
    return (FIX / name).read_text(encoding="utf-8")


def find(records, item, spec=None):
    hits = [r for r in records if r["item"] == item and (spec is None or r["spec"] == spec)]
    assert len(hits) == 1, (item, spec, len(hits))
    return hits[0]


# ---- helpers -------------------------------------------------------------------------------------------
@pytest.mark.parametrize("text,values", [
    ("AED 20 (Normal) / AED 25 (Van)", [20.0, 25.0]),
    ("8 AED", [8.0]),
    ("14,990 AED/hr", [14990.0]),
    ("Starting Fare", []),
])
def test_money_values(text, values):
    assert money_values(text) == values


def test_to_number_rejects_concessions():
    assert to_number("1,049") == 1049.0
    assert to_number("N/A") is None and to_number("Free") is None and to_number("50%") is None


def test_table_grid_expands_rowspan_and_colspan():
    from scrapling.parser import Selector
    t = Selector("<table><tr><th rowspan=2>P</th><th colspan=2>Silver</th></tr>"
                 "<tr><th>1 Zone</th><th>2 Zones</th></tr><tr><td>7 Days</td><td>50</td><td>80</td></tr></table>")
    assert table_grid(t.css("table")[0]) == [["P", "Silver", "Silver"], ["P", "1 Zone", "2 Zones"],
                                             ["7 Days", "50", "80"]]


def test_bot_wall_detection():
    assert is_bot_wall(403, b"<html><title>Just a moment...</title>")
    assert not is_bot_wall(200, b"<html><title>Just a moment...</title>")
    assert not is_bot_wall(403, b"<html>Forbidden</html>")


def test_robots_rules_are_obeyed(monkeypatch):
    net = Net(delay=0)
    monkeypatch.setattr(net, "_http", lambda url: (200, b"User-Agent: *\nDisallow: /\n", {}, url))
    assert net.robots_state("https://shop.example/plans")[0] == "disallowed"
    res = net.get("https://shop.example/plans")
    assert res.outcome == "robots_disallowed" and res.body == b""


def test_robots_4xx_means_no_rules_and_5xx_means_do_not_fetch(monkeypatch):
    net = Net(delay=0)
    monkeypatch.setattr(net, "_http", lambda url: (403, b"", {}, url))
    assert net.robots_state("https://a.example/x")[0] == "no_rules"
    net = Net(delay=0)
    monkeypatch.setattr(net, "_http", lambda url: (502, b"", {}, url))
    assert net.get("https://b.example/x").outcome == "robots_unreadable"


# ---- RTA -----------------------------------------------------------------------------------------------
def test_rta_nol_all_fares():
    recs = rta.parse_nol(read("sppi_rta_nol_tables.html"))
    assert len(recs) == 66          # 6 Red Ticket + 12 card x zone + 48 passes
    assert find(recs, "nol single journey - Silver Card - Within 1 Zone")["price"] == 3
    assert find(recs, "nol single journey - Gold Card - More than 2 Zones")["price"] == 15
    assert find(recs, "nol Red Ticket - Nol Red Ticket (Regular) - More than 2 Zones")["price"] == 8.5
    assert find(recs, "nol pass - Silver - All Zones - 30 Days")["price"] == 350
    assert find(recs, "nol pass - Gold - 2 Zones - 365 Days")["price"] == 3540
    assert all(r["currency"] == "AED" for r in recs)


def test_rta_taxi_starting_fares():
    recs = rta.parse_taxi(read("sppi_rta_taxi_fragment.html"))
    assert len(recs) == 21
    assert find(recs, "Taxi starting fare (Normal) - Dubai Airports - All day")["price"] == 20
    assert find(recs, "Taxi starting fare (Van) - Dubai Airports - All day")["price"] == 25
    assert find(recs, "Taxi starting fare - Port Rashid - All day")["price"] == 25
    road = [r for r in recs if r["spec"].startswith("Applies to Regular Taxi, Family Taxi and Hatta")]
    assert sorted(r["price"] for r in road) == [5, 5.5]


def test_rta_taxi_flags_the_overlapping_weekday_band_instead_of_fixing_it():
    recs = rta.parse_taxi(read("sppi_rta_taxi_fragment.html"))
    flagged = [r for r in recs if r["note"]]
    assert [r["item"] for r in flagged] == ["Taxi starting fare - All weekdays (Monday-Thursday) - 8 am-10 am"]


# ---- Mega Yachts ---------------------------------------------------------------------------------------
def test_megayachts_cards():
    recs = megayachts.parse(read("sppi_megayachts_cards.html"))
    assert [(r["item"], r["price"]) for r in recs] == [("Yacht charter - LOTUS 240", 14990),
                                                      ("Yacht charter - DESERT ROSE 155", 5990)]
    assert recs[0]["spec"] == "max guests 500; cabins 9; length 240 ft"
    assert recs[0]["price_text"] == "from 14,990 AED/hr"


# ---- UPS -----------------------------------------------------------------------------------------------
def test_ups_rate_pages():
    lines = read("sppi_ups_pages.txt").splitlines()
    recs, unparsed = ups.parse_rate_lines(lines, "2024-12-22")
    assert unparsed == []
    send = "sending (export, billed in UAE)"
    assert find(recs, "UPS Express Plus - UPS Express Envelopes - envelope", f"{send}; zone 1")["price"] == 614
    packages = "UPS Express Plus - Documents over 5 kg and Packages - 70 kg"
    assert find(recs, packages, f"{send}; zone 7")["price"] == 14159
    over70 = "UPS Express Plus - Documents over 5 kg and Packages - Over 70 kg"
    assert find(recs, over70, f"{send}; zone 3")["price"] == 125     # price per kg
    assert find(recs, "UPS Worldwide Express Freight Midday - all - minimum charge", f"{send}; zone 1")["price"] == 4899
    assert find(recs, "UPS Worldwide Express Freight - all - 1000 kg or more", f"{send}; zone 7")["price"] == 169


def test_ups_row_with_missing_zone_value_is_reported_not_guessed():
    lines = ["2025 UPS Tariff Guide, United Arab Emirates SENDING RATES", "UPS Express", "INTERNATIONAL DELIVERY",
             "Packages", "Zone 1 2 3", "1.0 kg 100 200"]
    recs, unparsed = ups.parse_rate_lines(lines)
    assert recs == [] and len(unparsed) == 1


def test_ups_effective_date():
    assert ups.effective_date("Effective from 22 December 2024, RATES IN AED") == "2024-12-22"


# ---- Oracle --------------------------------------------------------------------------------------------
def test_oracle_api_items_and_tiers():
    recs, updated = oracle.parse((FIX / "sppi_oracle_items.json").read_bytes())
    assert updated == "2026-10-08"
    assert len(recs) == 3
    assert all(r["currency"] == "AED" for r in recs)
    assert recs[0]["price"] == pytest.approx(0.3669327)
    assert "tier 950000-999999999999999" in recs[2]["spec"]


# ---- Pinas Cargo ---------------------------------------------------------------------------------------
def test_pinas_records_from_reading():
    reading = {"id": "air", "sha256": "0" * 64, "read_on": "2026-10-29", "currency": "AED",
               "currency_basis": "printed on the image", "title": "Air cargo UAE -> Philippines, temporary rates",
               "effective": "", "columns": ["Manila", "Luzon"],
               "rows": [{"label": "31 kg (flat rate)", "unit": "per box", "values": [465.0, 465.0]}],
               "extras": [{"label": "Airway bill fee", "unit": "per shipment", "price": 15.0}]}
    recs = pinas.records_from_reading(reading)
    assert [(r["item"], r["spec"], r["price"]) for r in recs] == [
        ("Air cargo UAE -> Philippines - 31 kg (flat rate)", "destination Manila", 465.0),
        ("Air cargo UAE -> Philippines - 31 kg (flat rate)", "destination Luzon", 465.0),
        ("Air cargo UAE -> Philippines - Airway bill fee", "", 15.0)]


def test_pinas_ocr_agreement_counts_each_value_once():
    reading = {"rows": [{"values": [450.0, 450.0]}]}
    assert pinas.ocr_agreement(reading, [450.0]) == "OCR cross-check: 1/2 read values also found by tesseract"
    assert "not run" in pinas.ocr_agreement(reading, None)


# ---- probe ---------------------------------------------------------------------------------------------
def test_probe_finds_text_and_alt_text_amounts():
    html = ('<html><body><p>3D glasses cost AED 3 each.</p>'
            '<img src="a.jpg" alt="31kg flat rate at AED 465"></body></html>')
    m = probe.mentions(html)
    assert {(x["currency"], x["amount"]) for x in m} == {("AED", 3.0), ("AED", 465.0)}
    assert any(x["where"].startswith("image alt") for x in m)


# ---- generic extractor ---------------------------------------------------------------------------------
from sppi import run as sppi_run  # noqa: E402
from sppi.sources import generic, tables  # noqa: E402


def test_generic_joins_amount_split_over_two_elements_and_reads_text_after():
    html = ('<html><body><h3>Business Pro 2 User Pack</h3><div class="card"><div><span>1,095</span> '
            '<span>AED/Month</span></div><p>5% VAT EXCLUDED</p></div></body></html>')
    recs = generic.extract(html)
    assert [(r["price"], r["currency"]) for r in recs] == [(1095.0, "AED")]
    assert recs[0]["context"].startswith("Business Pro 2 User Pack")
    assert recs[0]["after"] == "5% VAT EXCLUDED"


def test_generic_nested_list_labels_and_heading():
    html = ('<html><body><h2>Service Fees</h2><p>Mobile Application</p><ul><li>Friday<ul>'
            '<li>6:00 AM - 8:00 AM → AED 9</li><li>Per KM Rate: AED 2.45</li></ul></li></ul></body></html>')
    recs = generic.extract(html)
    assert [r["price"] for r in recs] == [9.0, 2.45]
    assert recs[0]["context"] == "Service Fees > Mobile Application > Friday"
    assert recs[1]["label"] == "Per KM Rate"


def test_generic_skips_header_nav_footer_unless_asked():
    html = '<html><body><nav><p>Lounge from AED 195</p></nav><main><p>Fee AED 10</p></main></body></html>'
    assert [r["price"] for r in generic.extract(html)] == [10.0]
    assert sorted(r["price"] for r in generic.extract(html, include_chrome=True)) == [10.0, 195.0]


def test_tables_matrix_skips_footnote_row_and_single_column_tables():
    html = ('<table><tr><th></th><th>Zone 1</th><th>Zone 2</th></tr>'
            '<tr><td>Zone 1 UAE</td><td>-</td><td>AED 50</td></tr>'
            '<tr><td colspan="3">* Asmara is AED 250.</td></tr></table>'
            '<table><tr><td>From Zone 1</td></tr><tr><td>AED 50</td></tr></table>')
    recs = tables.parse(html, "per kg")
    assert [(r["item"], r["price"], r["unit"]) for r in recs] == [("Zone 1 UAE -> Zone 2", 50.0, "per kg")]


def test_ups_fee_lines():
    lines = ["UPS Collect on Delivery (COD) UPS will attempt to collect ... For each UAE national / domestic COD "
             "shipment, AED 29 in addition to the",
             "Large Package Surcharge A package is considered ... 257 AED per package will be billed in addition",
             "Some other line AED 99"]
    recs = ups.parse_fee_lines(lines)
    assert [(r["item"], r["price"], r["unit"]) for r in recs] == [
        ("UPS fee - UPS Collect on Delivery (COD)", 29.0, ""),
        ("UPS fee - Large Package Surcharge", 257.0, "per package")]


# ---- linking to the sample products --------------------------------------------------------------------
PRODUCTS = {
    "x1-01": dict(product_id="x1-01", ser="x1", section="H", company="Taxi Co", isic_registered="4922", red="نعم",
                  type="خدمة", product="Taxi", isic_product="4922", isic_product_name="", source_url=""),
    "x1-02": dict(product_id="x1-02", ser="x1", section="H", company="Taxi Co", isic_registered="4922", red="نعم",
                  type="خدمة", product="Limousine", isic_product="4922", isic_product_name="", source_url=""),
    "y1-01": dict(product_id="y1-01", ser="y1", section="J", company="Telecom Co", isic_registered="6110", red="نعم",
                  type="منتج", product="Home plans", isic_product="6110", isic_product_name="", source_url=""),
}
COMPANIES = {"x1": dict(ser="x1", section="H", name_en="Taxi Co", isic="4922", red="نعم",
                        scraping_reason="sheet reason"),
             "y1": dict(ser="y1", section="J", name_en="Telecom Co", isic="6110", red="نعم", scraping_reason="")}


def _rec(item, price, text):
    return dict(item=item, spec="", price=price, currency="AED", unit="", price_type="", price_text=text, vat="",
                effective_date="", note="", status="parsed_page", source_url="https://x.ae/p", fetched_at="",
                http_status=200, snapshot="", sha256="", _context=item)


def test_map_records_rules_extras_and_dedupe():
    page = dict(id="p", ser="x1", map=[{"match": "Limo", "product": "x1-02"}, {"product": "x1-01"},
                                       {"match": "Rental", "product": "+Taxi rental"}])
    recs = [_rec("Limousine | Per KM Rate", 3.9, "Per KM Rate: AED 3.90"),
            _rec("Limousine | Per KM Rate", 3.9, "Per KM Rate: AED 3.90"),       # same text twice on the page
            _rec("Rental | 2 hours", 400.0, "2 hours - AED 400")]
    out = sppi_run.map_records(page, recs, PRODUCTS, COMPANIES, "2026-10-29")
    got = sorted((r["product_id"] or "+" + r["product"], r["price"]) for r in out)
    assert got == [("+Taxi rental", 400.0), ("x1-01", 3.9), ("x1-01", 400.0), ("x1-02", 3.9)]
    limo = next(r for r in out if r["product_id"] == "x1-02")
    assert (limo["section"], limo["isic_registered"], limo["isic_product"], limo["in_sample"]) == ("H", "4922", "4922",
                                                                                                    "نعم")
    assert "_context" not in limo
    extra = next(r for r in out if r["product"] == "Taxi rental")
    assert extra["section"] == "H" and extra["in_sample"].startswith("لا")


def test_availability_scraping_online_and_neither():
    prices = [dict(product_id="x1-01", currency="AED", price=5.0, source_url="https://x.ae/a"),
              dict(product_id="x1-01", currency="AED", price=2.45, source_url="https://x.ae/a")]
    status = {"companies": {"y1": {"status": "online", "verified": "yes", "reason": "robots.txt forbids"}},
              "products": {}}
    rows = {r["product_id"]: r for r in sppi_run.availability(PRODUCTS, COMPANIES, prices, status)}
    assert rows["x1-01"]["availability"] == sppi_run.SCRAPING and rows["x1-01"]["price_range"] == "2.45 - 5.00"
    assert rows["y1-01"]["availability"] == sppi_run.ONLINE and rows["y1-01"]["verified"] == "yes"
    assert rows["x1-02"]["availability"] == sppi_run.NEITHER and rows["x1-02"]["reason"] == "sheet reason"


def test_drop_repeated_removes_site_banner_only():
    banner = _rec("News | Revenue of over", 1.0, "Revenue of over AED 1 Billion")
    raw = {f"p{i}": [banner, _rec(f"Page {i} | Fee", float(i), f"Fee AED {i}")] for i in range(4)}
    out = sppi_run.drop_repeated(raw)
    assert all([r["price"] for r in recs] == [float(i)] for i, recs in enumerate(out.values()))


@pytest.mark.skipif(not (ROOT / "data/sppi/config/sppi_pages.json").exists()
                    or not (ROOT / "data/sppi/sample/products.csv").exists(),
                    reason="the sample config lives in data/sppi/ on the officer's machine (not in git)")
def test_pages_config_points_at_existing_products():
    products = sppi_run.load_products()
    pages, drop_labels = sppi_run.load_pages(products)       # raises on an unknown product_id
    assert drop_labels
    assert len({p["id"] for p in pages}) == len(pages)
    assert all(p["ser"] in {x["ser"] for x in products.values()} for p in pages)


# ---- airline 'from' fares -----------------------------------------------------------------------------
from sppi.sources import airfares  # noqa: E402


def test_emirates_featured_reads_card_code_and_keeps_only_the_departure_airport():
    card = ('<li data-departure="{dep}"><a href="/ae/english/book/featured-fares/?intc_name={code}"></a>'
            '<p>India</p><p>Mumbai (Bombay)</p><p>Book until 29 Oct 26</p><p>Economy Class Return</p>'
            '<p>from {cur} {price}*</p></li>')
    html = "<ul>" + card.format(dep="DXB", code="Y:DXB-BOM:AED%201,050*", cur="AED", price="1,050") + \
        card.format(dep="BOS", code="Y:BOS-BOM:USD%20874*", cur="USD", price="874") + "</ul>"
    recs, seen = airfares.emirates_featured(html, "DXB")
    assert seen == {"DXB", "BOS"}
    assert [(r["item"], r["price"], r["currency"], r["spec"]) for r in recs] == [
        ("Emirates fare DXB-BOM (Mumbai (Bombay)) - Economy Class Return", 1050.0, "AED", "Book until 29 Oct 26")]


def test_flydubai_route_links_and_route_fares():
    index = ('<a href="/en-ae/flights-from-dubai-to-baku/">Baku</a><a href="/en-ae/flights-from-baku-to-dubai/">x</a>'
             '<a href="/en-ae/flights-from-dubai-to-baku/">again</a>')
    assert airfares.flydubai_route_links(index) == ["/en-ae/flights-from-dubai-to-baku/"]
    page = ('<h2>Route information for Dubai to Baku Flights</h2><ul>'
            '<li><p>Lowest fare (One way)</p><p>AED 840</p></li><li><p>Lowest fare (Return)</p><p>AED 1,711</p></li>'
            '</ul><h2>Frequently asked questions</h2><p>a ticket costs a minimum of AED 788</p>')
    recs = airfares.flydubai_route(page)
    assert [(r["item"], r["price"]) for r in recs] == [
        ("flydubai fare Dubai to Baku - lowest fare (One way)", 840.0),
        ("flydubai fare Dubai to Baku - lowest fare (Return)", 1711.0)]


def test_unreadable_robots_is_read_again_on_the_next_page(monkeypatch):
    answers = iter([(502, b"", {}, ""), (200, b"User-Agent: *\nAllow: /\n", {}, "")])
    net = Net(delay=0)
    monkeypatch.setattr(net, "_http", lambda url: next(answers))
    monkeypatch.setattr("sppi.fetch.time.sleep", lambda s: None)
    assert net.robots_state("https://shop.example/a")[0] == "unreadable"
    assert net.robots_state("https://shop.example/b")[0] == "allowed"
