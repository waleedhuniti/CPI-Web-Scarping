"""Build the normalised basket (CSV + JSON) and a data-quality report from the source workbook.

    python scripts/build_basket.py [data/basket/basket_source.xlsx]
"""
import collections
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cpi.basket import load_basket, write_csv, write_json  # noqa: E402


def report(items) -> str:
    n = len(items)
    kinds = collections.Counter(i.barcode_kind for i in items)
    out = [f"# Basket data-quality report\n\nItems: **{n}**\n",
           "## Barcodes\n", "| kind | items |\n|---|---|"]
    out += [f"| {k} | {v} |" for k, v in kinds.most_common()]
    out.append("\n`store_code` = PLU or in-store code (not a real EAN/UPC): "
               + ", ".join(f"{i.item_code} ({i.barcode_raw})" for i in items if i.barcode_kind == "store_code") + "\n")
    out += ["## By COICOP group\n", "| group | items | with GTIN | spec-matched |", "|---|---|---|---|"]
    groups = collections.OrderedDict()
    for i in items:
        g = groups.setdefault((i.group_code, i.group_name), [0, 0, 0])
        g[0] += 1
        g[1 if i.barcode_kind == "gtin" else 2] += 1
    out += [f"| {k[1]} | {v[0]} | {v[1]} | {v[2]} |" for k, v in groups.items()]
    bad_q = [i for i in items if i.qty_flag or not i.qty_unit]
    out.append(f"\n## Quantities that need a human look ({len(bad_q)})\n")
    out += [f"- {i.item_code} {i.name_ar}: `{i.qty_raw}`" for i in bad_q] or ["- none"]
    unk = [i for i in items if i.origin_iso == "UNKNOWN"]
    out.append(f"\n## Origins not in the mapping table ({len(unk)})\n")
    out += [f"- {i.item_code}: `{i.origin_raw}`" for i in unk] or ["- none"]
    africa = [i for i in items if i.origin_iso == "AFRICA"]
    out.append(f"\n## Origin recorded only as 'Africa' ({len(africa)})\n")
    out += [f"- {i.item_code} {i.name_ar}" for i in africa] or ["- none"]
    return "\n".join(out) + "\n"


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data/basket/basket_source.xlsx"
    items = load_basket(src)
    out = ROOT / "data/basket"
    write_csv(items, out / "basket.csv")
    write_json(items, out / "basket.json")
    (out / "quality_report.md").write_text(report(items), encoding="utf-8")
    print(f"{len(items)} items -> {out}")


if __name__ == "__main__":
    main()
