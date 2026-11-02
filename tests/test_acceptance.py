"""Regression tests for review export and repeated bulk-category filtering."""
import csv
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import scrapling_category as sc
from cpi.decision import barcode_found, category_found
from cpi.basket import load_basket_any


@pytest.mark.parametrize('status', ['review_multiple', 'review_origin', 'substitute_origin', 'no_match'])
def test_review_is_not_approval(status):
    assert not category_found(status, True)
    assert not category_found(status, False)


def test_unverified_quantity_stays_unapproved():
    assert not barcode_found('barcode_match_qty_unverified')
    assert barcode_found('barcode_match')
    assert category_found('match')


@pytest.fixture
def category_case(tmp_path, monkeypatch):
    item = replace(load_basket_any(sc.ROOT)[0], item_code='test', match_mode='spec',
                   name_ar='طماطم', group_code='0117', origin_iso='EG', qty_raw='1 kg',
                   qty_unit='g', qty_total=1000)
    import cpi.basket
    monkeypatch.setattr(cpi.basket, 'load_basket_any', lambda root: [item])
    specs = tmp_path / 'specs.json'
    specs.write_text(json.dumps([{'c': 'test', 'product_en': 'tomato', 'query_en': 'tomato', 'must_have': ['tomato']}]))
    monkeypatch.setattr(sc, 'SPECS', specs)
    monkeypatch.setattr(sc, 'enrich_origins', lambda *args: None)
    monkeypatch.setenv('CPI_PINS', str(tmp_path / 'pins.json'))
    run = tmp_path / '2026-11-02_test'
    run.mkdir()
    row = dict(retailer='carrefour', group='0117', category='Fresh vegetables', title='Tomato Egypt 1kg',
               price=5, regular_price=5, unit_price=5, price_basis='kg', origin_seen='EG', url='https://example/p/1')
    def execute(rows):
        return sc.match(run, catalog=rows, delay=0)[0]
    return row, execute


def test_valid_pin_is_rechecked_when_product_changes(category_case):
    row, run = category_case
    assert run([row])['accepted'] == 'yes'
    assert run([dict(row, title='Organic Tomato Egypt 1kg')])['accepted'] == 'no'


def test_valid_pin_is_rechecked_when_origin_changes(category_case):
    row, run = category_case
    assert run([row])['accepted'] == 'yes'
    assert run([dict(row, origin_seen='AE')])['accepted'] == 'no'


def test_ambiguous_candidates_never_become_pins(category_case):
    row, run = category_case
    rows = [row, dict(row, url='https://example/p/2', unit_price=15)]
    assert run(rows)['status'] == 'review_multiple'
    assert not sc.load_pins()
    assert run(rows)['accepted'] == 'no'


@pytest.mark.parametrize('origin', ['', 'AE'])
def test_origin_substitution_never_becomes_initial_base(category_case, origin):
    row, run = category_case
    assert run([dict(row, origin_seen=origin)])['accepted'] == 'no'
    assert not sc.load_pins()


def test_legacy_ambiguous_pin_is_not_grandfathered(category_case):
    row, run = category_case
    sc.save_pins({'test|carrefour': {'url': row['url'], 'unit': 5}})
    assert run([row, dict(row, url='https://example/p/2', unit_price=15)])['accepted'] == 'no'


def test_default_pin_path_persists(tmp_path, monkeypatch):
    monkeypatch.delenv('CPI_PINS', raising=False)
    monkeypatch.setattr(sc, 'ROOT', tmp_path)
    sc.save_pins({'test': {'url': 'example'}})
    assert sc.load_pins() == {'test': {'url': 'example'}}


def test_missing_spec_does_not_match_entire_category():
    _, ok = sc.make_filter(dict(name_ar='طماطم', group_code='0117', qty_raw='1kg', qty_unit='g'), {})
    assert not ok(dict(title='Potato 1kg', category='Fresh vegetables', price_basis='kg', unit_price=5))


def test_long_export_preserves_review_without_approval(tmp_path, monkeypatch):
    import export_for_dataiku as export
    run = tmp_path / 'data/runs/2026-11-02_daily'
    run.mkdir(parents=True)
    row = dict(retailer='carrefour', name_ar='tomato', item_code='test', status='review_multiple', group='0117',
               basket_qty='1kg', title='Tomato', price=5, regular_price=5, unit_price=5, price_basis='kg',
               basket_origin='EG', origin_seen='EG', url='https://example/p/1')
    write_csv(run / 'category_matches.csv', [row])
    monkeypatch.setattr(export, 'ROOT', tmp_path)
    result = list(export.category_rows())[0]
    assert result['accepted'] == 'no'
    assert result['detail'] == 'review_multiple'
    assert result['url'] == row['url']


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.parametrize('observed', ['yes', 'no'])
def test_panel_estimate_cannot_override_review(tmp_path, monkeypatch, observed):
    import panel_run
    monkeypatch.delenv('CPI_CATALOGUE_JSON', raising=False)
    monkeypatch.delenv('CPI_PENDING_ROWS', raising=False)
    write_csv(tmp_path / 'category_matches.csv', [dict(retailer='carrefour', name_ar='tomato', item_code='test',
        status='review_multiple', group='0117', basket_qty='1kg', price_basis='kg', basket_origin='EG')])
    write_csv(tmp_path / 'line_prices.csv', [dict(date='2026-11-02', item_code='test', retailer='carrefour',
        observed=observed, rep_title='Tomato', rep_url='https://example/p/1', rep_photo='', price=5,
        index=100, n_products=2, cheapest=4, dearest=6)])
    panel_run.main(tmp_path, '2026-11-02T08:00:00+04:00')
    row = json.loads((tmp_path / 'panel/c000.json').read_text())['rows'][0]
    assert row['accepted'] == 'no' and row['price'] == ''
    assert row['status'] == ('review' if observed == 'yes' else 'not_observed')
