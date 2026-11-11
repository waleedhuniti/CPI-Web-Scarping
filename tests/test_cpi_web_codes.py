"""scripts/cpi_web_codes.py: CPI-structured codes for scraped products."""
import csv, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "cpi_web_codes.py")
COLS = ["date", "store", "chain", "product_id", "title", "brand", "size", "group", "category", "basket_item_codes"]


def write_unified(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})


def setup(tmp_path, rows, rules):
    (tmp_path / "rules").mkdir(exist_ok=True)
    (tmp_path / "rules" / "b1.json").write_text(json.dumps(rules), encoding="utf-8")
    (tmp_path / "rules" / "new_types_canonical.json").write_text(json.dumps({"types": [
        {"class_value": "N:03121:Jackets and coats", "name_en": "Jackets and coats", "name_ar": "جاكيتات ومعاطف", "subclass5": "03121"}]}), encoding="utf-8")
    basket = [{"class_code": "0111101", "class_name": "0111101 - أرز بسمتي هندي"}, {"class_code": "0111104", "class_name": "0111104 - أرز مصري"},
              {"class_code": "0312101", "class_name": "0312101 - قميص رجالي"}]
    (tmp_path / "basket.json").write_text(json.dumps(basket), encoding="utf-8")
    (tmp_path / "coicop.tsv").write_text("code5\tcoicop\ttitle\tincludes\texcludes\n01111\t01.1.1.1\tCereals (ND)\t\t\n03121\t03.1.2.1\tGarments for men (SD)\t\t\n", encoding="utf-8")
    write_unified(tmp_path / "u.csv", rows)


def run(tmp_path, out, prev=None):
    a = [sys.executable, "-I", SCRIPT, str(tmp_path / "u.csv"), str(out), "--rules", str(tmp_path / "rules"),
         "--basket", str(tmp_path / "basket.json"), "--coicop", str(tmp_path / "coicop.tsv"), "--names", str(tmp_path / "names")]
    if prev:
        a += ["--prev", str(prev)]
    subprocess.run(a, check=True, capture_output=True, text=True)
    return json.loads(out.read_text(encoding="utf-8"))


RULES = {"categories": {
    "rice": {"default": "0111101", "rules": [{"re": r"\begypt", "class": "0111104"}]},
    "men_jackets": {"default": "N:03121:Jackets and coats", "rules": [{"re": r"gift card", "class": "X:gift card"}]}}}

ROWS = [
    {"date": "2026-11-01", "store": "Lulu", "chain": "lulu", "product_id": "1", "title": "Tilda Basmati 1 kg", "category": "rice"},
    {"date": "2026-11-01", "store": "Lulu", "chain": "lulu", "product_id": "2", "title": "Egyptian Rice 2 kg", "category": "rice"},
    {"date": "2026-11-01", "store": "Lulu", "chain": "lulu", "product_id": "3", "title": "Sinnara Basmati 5 kg", "category": "rice", "basket_item_codes": "011110401"},
    {"date": "2026-11-01", "store": "Max", "chain": "max", "product_id": "J1", "title": "Puffer Jacket", "category": "men jackets"},
    {"date": "2026-11-01", "store": "Max", "chain": "max", "product_id": "G1", "title": "Max Gift Card", "category": "men jackets"},
    {"date": "2026-11-01", "store": "Zara", "chain": "zara", "product_id": "Z9", "title": "Scarf", "category": "scarves"},
]


def test_codes_follow_the_cpi_structure(tmp_path):
    setup(tmp_path, ROWS, RULES)
    reg = run(tmp_path, tmp_path / "reg.json")
    p = reg["p"]
    assert all(len(c) == 12 and c.isdigit() for c in p.values())
    assert p["lulu|1"][:7] == "0111101" and p["lulu|2"][:7] == "0111104"
    assert p["lulu|3"][:7] == "0111104"                      # the basket match wins over the rule (Sinnara basmati coded as basket says)
    assert p["max|J1"][:7] == "0312151"                      # a web type: subclass 03121, first free type from 51
    assert reg["classes"]["0312151"]["web"] is True and reg["classes"]["0312151"]["ar"] == "جاكيتات ومعاطف"
    assert reg["x"] == {"max|G1": "gift card"}               # excluded: no code
    assert reg["uncoded"] == ["zara|Z9"]                     # no rules for its category yet
    assert len(set(p.values())) == len(p)                    # one listing, one code
    assert reg["b"]["lulu|3"] == "011110401"


def test_codes_are_stable_and_new_products_append(tmp_path):
    setup(tmp_path, ROWS, RULES)
    first = run(tmp_path, tmp_path / "r1.json")
    more = ROWS + [{"date": "2026-11-02", "store": "Lulu", "chain": "lulu", "product_id": "0", "title": "Abu Kass Basmati 10 kg", "category": "rice"}]
    write_unified(tmp_path / "u.csv", more)
    second = run(tmp_path, tmp_path / "r2.json", prev=tmp_path / "r1.json")
    for k, c in first["p"].items():
        assert second["p"][k] == c                            # nobody's code changes
    assert second["p"]["lulu|0"][:7] == "0111101"
    assert int(second["p"]["lulu|0"][7:]) == max(int(c[7:]) for k, c in first["p"].items() if c[:7] == "0111101") + 1
    assert second["web_types"] == first["web_types"]


def test_a_reclassified_product_gets_a_new_code_and_the_old_one_is_kept(tmp_path):
    setup(tmp_path, ROWS, RULES)
    first = run(tmp_path, tmp_path / "r1.json")
    rules = json.loads(json.dumps(RULES))
    rules["overrides"] = {"lulu|1": "0111104"}
    (tmp_path / "rules" / "b1.json").write_text(json.dumps(rules), encoding="utf-8")
    second = run(tmp_path, tmp_path / "r2.json", prev=tmp_path / "r1.json")
    old = first["p"]["lulu|1"]
    assert second["p"]["lulu|1"][:7] == "0111104"
    assert second["moved"][old] == second["p"]["lulu|1"]
