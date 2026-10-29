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
    assert net.robots_state("https://www.du.ae/ultimate")[0] == "disallowed"
    res = net.get("https://www.du.ae/ultimate")
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
def test_pinas_readings_are_consistent():
    readings = json.loads((ROOT / "config/sppi_image_transcriptions.json").read_text(encoding="utf-8"))["pinas_cargo"]
    for r in readings:
        assert len(r["sha256"]) == 64
        assert all(len(row["values"]) == len(r["columns"]) for row in r["rows"])
    recs = [x for r in readings for x in pinas.records_from_reading(r)]
    assert len(recs) == 52
    air = next(r for r in readings if r["id"] == "pinas_air_cargo")
    assert air["rows"][0]["values"][0] == 465.0     # also stated in the site's alt text ('AED 465')


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
