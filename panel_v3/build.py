"""Build panel_v3/portal.html from portal.src.html: inlines the TrendX ISIC item codes (data/trendx/isic_map.csv)."""
import csv, json
from pathlib import Path
here = Path(__file__).parent; repo = here.parent
m = {r["commodity"]: [r["item_code"], r["isic_class"], r["class_en"], r["class_ar"]] for r in csv.DictReader(open(repo / "data/trendx/isic_map.csv", encoding="utf-8"))}
src = (here / "portal.src.html").read_text(encoding="utf-8")
out = src.replace("/*ISIC_MAP*/{}", json.dumps(m, ensure_ascii=False, separators=(",", ":")))
(here / "portal.html").write_text(out, encoding="utf-8")
print("portal.html", len(out), "bytes,", len(m), "ISIC codes")
