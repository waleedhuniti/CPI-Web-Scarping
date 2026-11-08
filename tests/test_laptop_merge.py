"""scripts/pc/merge_carrefour_barcode.py: the laptop's Carrefour barcode rows into the day's cloud run."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "pc"))

import merge_carrefour_barcode as m  # noqa: E402

DAY = "2026-11-09"


def row(item, retailer, source, status="found", day=DAY, price=10.0):
    return dict(run_date=day, source=source, retailer=retailer, item_code=item, status=status,
                accepted="yes" if status == "found" else "no", price=price if status == "found" else "")


def write(folder, rows, name="c"):
    Path(folder).mkdir(parents=True, exist_ok=True)
    for i, c in enumerate(m.chunk(rows, limit=300)):
        (Path(folder) / f"{name}{i:03d}.json").write_text(json.dumps({"rows": c, "i": i}))


def setup(tmp_path, cloud_read=0, laptop_read=363, laptop_day=DAY, lulu="363 pages read, 0 failed"):
    cloud_rows = ([row("A", "carrefour", "barcode", "not_found")] if cloud_read else []) + \
        [row("A", "carrefour", "catalogue"), row("B", "carrefour", "name_search"), row("C", "carrefour", "category", "not_observed"),
         row("A", "lulu", "barcode"), row("B", "lulu", "barcode"), row("A", "lulu", "category")] * 12
    write(tmp_path / "cloud" / "rows", cloud_rows)
    run = dict(startedAt=DAY + "T02:48:00+00:00", status="error", chunks=0, count=len(cloud_rows), accepted=0, thumbs_asset="t1",
               summary={"lulu_barcode": {"accepted": 2, "lines": 2}},
               log=["Carrefour UAE barcode: %d pages read, %d failed" % (cloud_read, 363 - cloud_read), "Lulu Hypermarket UAE barcode: " + lulu, "other line"])
    (tmp_path / "cloud" / "run.json").write_text(json.dumps(run))
    mine = [row("A", "carrefour", "barcode", day=laptop_day), row("D", "carrefour", "barcode", "not_found", day=laptop_day)]
    write(tmp_path / "laptop", mine)
    (tmp_path / "laptop" / "run.json").write_text(json.dumps(dict(
        log=["Carrefour UAE barcode: %d pages read, %d failed" % (laptop_read, 363 - laptop_read)],
        summary={"carrefour_barcode": {"accepted": 1, "label": "Carrefour UAE (barcode)", "lines": 2}})))
    return tmp_path / "cloud" / "run.json", tmp_path / "cloud" / "rows", tmp_path / "laptop", tmp_path / "out"


def test_merge_replaces_only_carrefour_barcode_rows(tmp_path):
    r = m.merge(*setup(tmp_path))
    assert r["action"] == "merged"
    new = [x for f in sorted((tmp_path / "out").glob("c*.json")) for x in json.loads(f.read_text())["rows"]]
    barcode = [x for x in new if x["retailer"] == "carrefour" and x["source"] == "barcode"]
    assert [x["item_code"] for x in barcode] == ["A", "D"]
    assert not [x for x in new if x["retailer"] == "carrefour" and x["source"] in ("catalogue", "name_search") and x["item_code"] == "A"]   # A now has a barcode price
    assert [x for x in new if x["source"] == "name_search"] == [x for x in new if x["item_code"] == "B" and x["source"] == "name_search"]
    assert sum(1 for x in new if x["retailer"] == "lulu") == 36 and sum(1 for x in new if x["source"] == "category" and x["retailer"] == "carrefour") == 12
    run = json.loads((tmp_path / "out" / "run.json").read_text())
    assert run["summary"]["carrefour_barcode"]["accepted"] == 1 and run["summary"]["lulu_barcode"]["lines"] == 2
    assert run["thumbs_asset"] == "t1" and run["count"] == len(new) and run["status"] == "done"
    assert run["log"][0] == "Carrefour UAE barcode: 363 pages read, 0 failed" and "replaced" in run["log"][-1]


def test_nothing_changes_when_the_laptop_read_nothing(tmp_path):
    r = m.merge(*setup(tmp_path, laptop_read=0))
    assert r["action"] == "skipped" and not list((tmp_path / "out").glob("c*.json")) and not (tmp_path / "out" / "run.json").exists()


def test_nothing_changes_when_the_cloud_run_read_as_much(tmp_path):
    assert m.merge(*setup(tmp_path, cloud_read=363, laptop_read=363))["action"] == "skipped"


def test_nothing_changes_for_another_day(tmp_path):
    r = m.merge(*setup(tmp_path, laptop_day="2026-11-08"))
    assert r["action"] == "skipped" and "another day" in r["reason"]


def test_run_stays_error_when_lulu_failed_pages_remain(tmp_path):
    m.merge(*setup(tmp_path, lulu="300 pages read, 63 failed"))
    assert json.loads((tmp_path / "out" / "run.json").read_text())["status"] == "error"


def test_old_chunks_beyond_the_new_ones_are_listed_for_deletion(tmp_path):
    paths = setup(tmp_path)
    for extra in ("c090", "c091"):
        (tmp_path / "cloud" / "rows" / f"{extra}.json").write_text(json.dumps({"rows": []}))
    r = m.merge(*paths)
    assert "c090" in r["delete"] and "c091" in r["delete"]
