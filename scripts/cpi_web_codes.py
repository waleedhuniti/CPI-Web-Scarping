"""Give every scraped CPI product a code in our CPI structure (COICOP 2018).

Usage:
  python3 -I scripts/cpi_web_codes.py <unified.csv> <out registry.json> [--prev registry.json] [--xlsx codes.xlsx]
      [--rules data/cpi/web_coding/rules] [--basket data/basket/basket.json]
      [--coicop data/cpi/web_coding/coicop2018_subclasses.tsv]

<unified.csv> is the output of scripts/cpi_unified.py (one row per date, shop and product).

The code follows the official basket's item code:
  official item code  SSSSS TT VV       (9 digits)  subclass + item type + variety
  web product code    SSSSS TT NNNNN    (12 digits) subclass + item type + product serial
  SSSSS = COICOP 2018 subclass (01111 = 01.1.1.1 Cereals), TT = item type inside the subclass. The first 7 digits are
  the CPI class, so every web product rolls up to the same class, subclass, group and division as the official basket.
  Item types 01-50 are the basket's own; types our basket does not have get 51-99 in their subclass ("web" types).
  NNNNN numbers the products of a class (shop + product id), so one product listing = one code.

Classification, per product (rules files in data/cpi/web_coding/rules, one per batch of shop categories):
  overrides > the product's basket item codes (when they share one class: the basket match is authoritative)
  > the first regex rule of its shop category that matches "title | brand | size" > the category default.
  Classes are values like 0111101 (existing class), N:<subclass5>:<type name> (web type) or X:<reason> (not a
  household consumption good: no code). A product in a category with no rules stays uncoded and is listed.

Codes are stable: with --prev, every product keeps the code it had; new products get the next serial of their class;
a product whose class changed gets a new code and the old one is recorded in "moved". Web type numbers are kept too.
"""
import csv, json, os, re, sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_TYPE_FIRST = 51


def slug_of(category, group, catalogue_categories):
    ck = category if category in catalogue_categories else "basket " + (group or "none")
    return re.sub(r"[^a-z0-9]+", "_", ck.lower()).strip("_")


def load_rules(rules_dir):
    cats, overrides, canon, extra = {}, {}, {}, []
    for f in sorted(os.listdir(rules_dir)):
        p = os.path.join(rules_dir, f)
        if f == "new_types_canonical.json":
            j = json.load(open(p, encoding="utf-8"))
            for t in j.get("types", []):
                canon[t["class_value"]] = t
        elif f.endswith(".newtypes.json"):
            extra += json.load(open(p, encoding="utf-8"))
        elif f.endswith(".json"):
            j = json.load(open(p, encoding="utf-8"))
            for slug, c in j.get("categories", {}).items():
                cats[slug] = {"default": c.get("default", ""), "rules": [(re.compile(r["re"], re.I), r["class"]) for r in c.get("rules", [])]}
            overrides.update(j.get("overrides", {}))
    for t in extra:
        canon.setdefault(t["class_value"], {"class_value": t["class_value"], "name_ar": t.get("name_ar", ""),
                                            "name_en": t["class_value"].split(":", 2)[2], "subclass5": t["class_value"].split(":")[1]})
    return cats, overrides, canon


def classify(p, cats, overrides):
    key = f"{p['chain']}|{p['product_id']}"
    if key in overrides:
        return overrides[key], "override"
    codes = p["basket"]
    if codes and len({c[:7] for c in codes}) == 1:
        return next(iter(codes))[:7], "basket"
    cat = cats.get(p["slug"])
    if not cat:
        return "", "no rules"
    text = f"{p['title']} | {p['brand']} | {p['size']}"
    for rx, c in cat["rules"]:
        if rx.search(text):
            return c, "rule"
    return cat["default"], "default" if cat["default"] else "no rules"


def main(a):
    unified, out = a[0], a[1]
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    rules_dir = opt("--rules", os.path.join(ROOT, "data/cpi/web_coding/rules"))
    basket = json.load(open(opt("--basket", os.path.join(ROOT, "data/basket/basket.json")), encoding="utf-8"))
    coicop = {r["code5"]: r for r in csv.DictReader(open(opt("--coicop", os.path.join(ROOT, "data/cpi/web_coding/coicop2018_subclasses.tsv")), encoding="utf-8"), delimiter="\t")}
    prev = json.load(open(opt("--prev"), encoding="utf-8")) if opt("--prev") else None

    classes = {}
    for x in basket:
        classes.setdefault(x["class_code"], {"ar": x["class_name"].split(" - ", 1)[-1], "en": "", "sub": x["class_code"][:5], "web": False})
    cats, overrides, canon = load_rules(rules_dir)

    # products from the unified dataset
    prods = {}
    with open(unified, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            k = (r["chain"], r["product_id"])
            p = prods.setdefault(k, {"chain": r["chain"], "product_id": r["product_id"], "store": r["store"], "title": r["title"], "brand": r["brand"],
                                     "size": r["size"], "category": r["category"], "group": r["group"], "basket": set()})
            if r["basket_item_codes"]:
                p["basket"].update(r["basket_item_codes"].split(" | "))
            for fld in ("title", "brand", "size", "category"):
                if not p[fld] and r[fld]:
                    p[fld] = r[fld]
    catalogue_cats = {p["category"] for p in prods.values() if p["category"]}
    for p in prods.values():
        p["slug"] = slug_of(p["category"], p["group"], catalogue_cats)

    # web types: keep previous numbers, number new ones from 51 in their subclass
    web_num = dict(prev.get("web_types", {})) if prev else {}       # "N:sub:name" -> class7
    for c7, c in (prev or {}).get("classes", {}).items():
        if c.get("web"):
            classes[c7] = c
    used = defaultdict(set)
    for c7 in classes:
        used[c7[:5]].add(int(c7[5:7]))

    def web_class(val):
        if val in web_num:
            return web_num[val]
        sub = val.split(":")[1]
        t = canon.get(val, {})
        n = WEB_TYPE_FIRST
        while n in used[sub]:
            n += 1
        if n > 99:
            raise SystemExit(f"subclass {sub} has no free web type number for {val}")
        used[sub].add(n)
        c7 = f"{sub}{n:02d}"
        web_num[val] = c7
        classes[c7] = {"ar": t.get("name_ar", ""), "en": t.get("name_en", val.split(":", 2)[2]), "sub": sub, "web": True}
        return c7

    assigned, how_n, uncoded, excluded = {}, Counter(), [], {}
    for k in sorted(prods, key=lambda k: (prods[k]["slug"], prods[k]["store"], prods[k]["title"], k)):
        p = prods[k]
        val, how = classify(p, cats, overrides)
        how_n[how] += 1
        if not val:
            uncoded.append(k)
            continue
        if val.startswith("X:"):
            excluded[f"{k[0]}|{k[1]}"] = val[2:]
            continue
        if val.startswith("N:"):
            val = web_class(val)
        if val not in classes:
            raise SystemExit(f"unknown class {val} for {k}")
        assigned[k] = val
    for val in sorted(canon):           # number canonical web types even if no product uses them today
        if val.startswith("N:"):
            web_class(val)

    # serials
    codes = dict(prev.get("p", {})) if prev else {}
    moved = dict(prev.get("moved", {})) if prev else {}
    top = defaultdict(int)
    for c in codes.values():
        top[c[:7]] = max(top[c[:7]], int(c[7:]))
    for k in sorted(assigned, key=lambda k: (assigned[k], prods[k]["store"], prods[k]["title"], k)):
        key, c7 = f"{k[0]}|{k[1]}", assigned[k]
        old = codes.get(key)
        if old and old[:7] == c7:
            continue
        top[c7] += 1
        if top[c7] > 99999:
            raise SystemExit(f"class {c7} ran out of serials")
        if old:
            moved[old] = f"{c7}{top[c7]:05d}"
        codes[key] = f"{c7}{top[c7]:05d}"
    for key in list(codes):
        ch, pid = key.split("|", 1)
        if (ch, pid) in prods and (ch, pid) not in assigned:
            moved[codes.pop(key)] = "excluded or uncoded"

    used_classes = {c[:7] for c in codes.values()}
    reg = {"v": 1, "scheme": "SSSSS TT NNNNN: COICOP 2018 subclass + item type (01-50 basket, 51-99 web) + product serial",
           "classes": {c7: classes[c7] for c7 in sorted(classes) if c7 in used_classes or classes[c7].get("web")},
           "subclasses": {s: coicop[s]["title"] for s in sorted({c[:5] for c in used_classes}) if s in coicop},
           "web_types": web_num, "p": dict(sorted(codes.items())),
           "b": {f"{a}|{b}": " ".join(sorted(prods[(a, b)]["basket"])) for a, b in sorted(prods) if prods[(a, b)]["basket"]}, "x": dict(sorted(excluded.items())), "moved": moved,
           "uncoded": [f"{a}|{b}" for a, b in uncoded]}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, separators=(",", ":"))
    print(f"products {len(prods):,} · coded {len(codes):,} · excluded {len(excluded):,} · uncoded {len(uncoded):,}")
    print("how:", dict(how_n))
    print(f"classes used {len(used_classes)} ({sum(1 for c in used_classes if classes[c].get('web'))} web types) · subclasses {len(reg['subclasses'])}")
    if opt("--xlsx"):
        write_xlsx(opt("--xlsx"), reg, prods, coicop)


def write_xlsx(path, reg, prods, coicop):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    hd = lambda ws: [setattr(c, "font", Font(bold=True, color="FFFFFF")) or setattr(c, "fill", PatternFill("solid", fgColor="1B2A52")) for c in ws[1]]
    ws = wb.active
    ws.title = "Product codes"
    ws.append(["web_code", "cpi_class", "class_name_ar", "class_name_en", "web_type", "coicop_subclass", "coicop_title", "store", "chain",
               "product_id", "title", "brand", "size", "shop_category", "basket_item_codes"])
    for key, code in sorted(reg["p"].items(), key=lambda t: t[1]):
        ch, pid = key.split("|", 1)
        p, c = prods.get((ch, pid), {}), reg["classes"][code[:7]]
        s = code[:5]
        ws.append([code, code[:7], c["ar"], c["en"], "yes" if c.get("web") else "", f"{s[:2]}.{s[2]}.{s[3]}.{s[4]}", reg["subclasses"].get(s, ""),
                   p.get("store", ""), ch, pid, p.get("title", ""), p.get("brand", ""), p.get("size", ""), p.get("category", ""), " ".join(sorted(p.get("basket", ())))])
    hd(ws)
    ws.freeze_panes = "A2"
    for col, w in zip("ABCDEFGHIJKLMNO", [14, 10, 28, 26, 8, 10, 30, 20, 11, 16, 50, 16, 10, 20, 20]):
        ws.column_dimensions[col].width = w
    c2 = wb.create_sheet("Classes")
    c2.append(["cpi_class", "coicop_subclass", "coicop_title", "type", "class_name_ar", "class_name_en", "web_type", "products"])
    n = Counter(c[:7] for c in reg["p"].values())
    for c7, c in sorted(reg["classes"].items()):
        s = c7[:5]
        c2.append([c7, f"{s[:2]}.{s[2]}.{s[3]}.{s[4]}", reg["subclasses"].get(s, coicop.get(s, {}).get("title", "")), c7[5:7], c["ar"], c["en"], "yes" if c.get("web") else "", n.get(c7, 0)])
    hd(c2)
    for col, w in zip("ABCDEFGH", [10, 12, 36, 6, 30, 30, 8, 10]):
        c2.column_dimensions[col].width = w
    x = wb.create_sheet("Not coded")
    x.append(["chain", "product_id", "store", "title", "reason"])
    for key, why in reg["x"].items():
        ch, pid = key.split("|", 1)
        p = prods.get((ch, pid), {})
        x.append([ch, pid, p.get("store", ""), p.get("title", ""), "excluded: " + why])
    for key in reg["uncoded"]:
        ch, pid = key.split("|", 1)
        p = prods.get((ch, pid), {})
        x.append([ch, pid, p.get("store", ""), p.get("title", ""), "no rules for its shop category yet"])
    hd(x)
    nt = wb.create_sheet("How the code works")
    nt.column_dimensions["A"].width = 110
    for line in [
        "Web product code = SSSSS TT NNNNN (12 digits), the same structure as the official basket item code SSSSS TT VV (9 digits).",
        "SSSSS: COICOP 2018 subclass (e.g. 01111 = 01.1.1.1 Cereals). TT: item type inside the subclass. First 7 digits = CPI class.",
        "Types 01-50 are the official basket's item types; 51-99 are types the basket does not have (web types, marked web_type = yes).",
        "NNNNN: serial of the product listing (shop + shop product id) inside its class. One listing = one code; codes never change.",
        "A product matched to a basket line takes that line's class. Others are classed by reviewed rules on the product title.",
        "Excluded: goods that are not household consumption (no code). Moved codes are kept in the registry when a class is corrected.",
    ]:
        nt.append([line])
    wb.save(path)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1:])
