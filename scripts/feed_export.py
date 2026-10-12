"""One day's data as plain CSV files for Dataiku (committed to the repository under data/feed/ by the daily routine).

    python scripts/feed_export.py data/runs/<D>_daily [data/catalogue/<D>]

-> data/feed/basket/<date>.csv       the basket run (every line x retailer, found / not found), same columns as the
                                      panel's long table (no photos)
   data/feed/catalogue/<date>.csv    the all-divisions catalogue (if a catalogue folder is given)
   data/feed/latest_basket.csv, data/feed/latest_catalogue.csv   copies of today's files

The date is the run's date; files of other days are never touched, so the folders become the history. A Dataiku recipe
(dataiku/recipe_github_feed.py) lists the folders and loads the dates it has not loaded yet.
"""
import csv
import glob
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASKET_COLS = ["run_date", "source", "retailer", "item_code", "group_code", "name", "brand", "basket_qty", "barcode", "status",
               "detail", "accepted", "title", "price", "regular_price", "unit_price", "price_basis", "basket_origin",
               "origin_seen", "currency", "url", "photo", "size", "group_name", "section", "retailer_id", "note"]


def main(run_dir, cat_dir=None):
    run_dir = Path(run_dir)
    feed = ROOT / "data/feed"
    (feed / "basket").mkdir(parents=True, exist_ok=True)
    rows = [r for f in sorted(glob.glob(str(run_dir / "panel/c*.json"))) for r in json.load(open(f))["rows"]]
    if rows:
        date = rows[0]["run_date"]
        with open(feed / "basket" / f"{date}.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=BASKET_COLS, extrasaction="ignore", restval="")
            w.writeheader()
            w.writerows(rows)
        shutil.copy(feed / "basket" / f"{date}.csv", feed / "latest_basket.csv")
        print(f"basket: {len(rows)} rows -> {feed / 'basket' / (date + '.csv')}")
    if cat_dir and (Path(cat_dir) / "catalog.csv").exists():
        date = Path(cat_dir).name[:10]
        (feed / "catalogue").mkdir(parents=True, exist_ok=True)
        shutil.copy(Path(cat_dir) / "catalog.csv", feed / "catalogue" / f"{date}.csv")
        shutil.copy(feed / "catalogue" / f"{date}.csv", feed / "latest_catalogue.csv")
        print(f"catalogue -> {feed / 'catalogue' / (date + '.csv')}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
