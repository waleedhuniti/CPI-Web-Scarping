"""Shared loaders for the TrendX forecastability analysis (read-only on the repo data)."""
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("/home/user/CPI-Web-Scarping")
CSV = REPO / "data/portal/te/commodity_prices.csv"
OUT = Path(__file__).resolve().parents[3] / "data" / "trendx" / "research"
OUT.mkdir(exist_ok=True)

# TrendX index: every commodity except the published indices (category "Index") and Electricity -> 90 series.
# NB: scripts/build_pages_site.py::trendx() only drops category "Index" (95 series, electricity kept).
EXCLUDE_CATS = {"Index", "Electricity"}


def load():
    d = pd.read_csv(CSV, parse_dates=["run_date", "price_date"])
    d["key"] = d["category"] + " | " + d["commodity"]
    d["in_index"] = ~d["category"].isin(EXCLUDE_CATS)
    d["lag_days"] = (d["run_date"] - d["price_date"]).dt.days
    return d


def trading_panel(d, start="2026-10-02", end="2026-10-30"):
    """Business-day panel of closing prices keyed by the quote's own price_date.

    For each commodity keep the last scrape of each price_date (the scrape is at ~23:07 UTC so it is the close),
    then take the as-of value on every Mon-Fri from start to end (carry forward over a missing quote).
    Rows: business days; columns: commodity key.
    """
    x = d.sort_values(["key", "price_date", "run_date"]).drop_duplicates(["key", "price_date"], keep="last")
    wide = x.pivot(index="price_date", columns="key", values="price").sort_index()
    bdays = pd.bdate_range(start, end)
    allidx = wide.index.union(bdays)
    wide = wide.reindex(allidx).ffill().reindex(bdays)
    return wide


def fresh_mask(d, start="2026-10-02", end="2026-10-30"):
    """True where the commodity has a quote whose price_date is exactly that business day (not carried forward)."""
    x = d.drop_duplicates(["key", "price_date"])
    m = x.assign(v=True).pivot(index="price_date", columns="key", values="v")
    bdays = pd.bdate_range(start, end)
    return m.reindex(bdays).fillna(False).astype(bool)


def jevons(panel):
    """Chained Jevons (equal-weight geometric mean of day-on-day relatives over series present both days), first = 100."""
    lp = np.log(panel)
    rel = lp.diff()
    step = rel.mean(axis=1, skipna=True).fillna(0.0)
    return 100 * np.exp(step.cumsum())


def index_keys(d):
    return sorted(d.loc[d.in_index, "key"].unique())
