# Dataiku Python recipe: pull the daily CPI data from the private GitHub repository into two Dataiku datasets.
# No scraping inside Dataiku and no file download/upload: the daily scraping run commits one CSV per day to
#   data/feed/basket/<date>.csv       (the 637-line basket x Carrefour / Lulu)
#   data/feed/catalogue/<date>.csv    (all CPI divisions: food, household, personal care, electronics, clothing ...)
# and this recipe loads the days it does not have yet (incremental), so history is kept.
#
# Setup (once):
#   - Project variable (or a DSS secret): github_token = a fine-grained read-only token for the repository
#     (Repository permissions -> Contents: Read-only). Never put it in the recipe code.
#   - Python code environment with: requests, pandas
#   - Output datasets: "cpi_basket_feed" and "cpi_catalogue_feed" (SQL or filesystem; the recipe appends)
#   - Scenario: time trigger daily 09:30 Asia/Dubai (the scraping run finishes before) -> build both datasets
#   - The Dataiku server needs outbound HTTPS to api.github.com
import io

import dataiku
import pandas as pd
import requests

OWNER, REPO = "waleedhuniti", "CPI-Web-Scarping"
BRANCH = "claude/sleepy-lamport-dwu4iw"        # the branch the daily run commits to
FEEDS = {"basket": "cpi_basket_feed", "catalogue": "cpi_catalogue_feed"}

token = dataiku.get_custom_variables().get("github_token")
H = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
RAW = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.raw+json"}


def dates_in_feed(folder):
    r = requests.get(f"https://api.github.com/repos/{OWNER}/{REPO}/contents/data/feed/{folder}", params={"ref": BRANCH}, headers=H, timeout=60)
    r.raise_for_status()
    return sorted(x["name"][:-4] for x in r.json() if x["name"].endswith(".csv"))


def read_day(folder, date):
    r = requests.get(f"https://api.github.com/repos/{OWNER}/{REPO}/contents/data/feed/{folder}/{date}.csv", params={"ref": BRANCH}, headers=RAW, timeout=180)
    r.raise_for_status()
    return pd.read_csv(io.BytesIO(r.content), dtype=str, encoding="utf-8-sig")


for folder, name in FEEDS.items():
    ds = dataiku.Dataset(name)
    try:
        have = set(ds.get_dataframe(columns=["feed_date"])["feed_date"].unique())     # days already loaded
        old = ds.get_dataframe()
    except Exception:
        have, old = set(), None
    new = []
    for d in dates_in_feed(folder):
        if d not in have:
            df = read_day(folder, d)
            df.insert(0, "feed_date", d)
            for c in ("price", "regular_price", "unit_price"):
                if c in df:
                    df[c] = pd.to_numeric(df[c], errors="coerce")
            new.append(df)
            print(name, d, len(df), "rows")
    if new:
        out = pd.concat(([old] if old is not None else []) + new, ignore_index=True)
        ds.write_with_schema(out)
    else:
        print(name, "is up to date")
