"""(f) Rebasing to 2024 average = 100: what our own columns can and cannot give.

* ytd  -> price at the last close of 2025 (one fixed point per commodity; must be identical every day - checked in 02)
* yoy  -> price one year before each price_date (a daily strip Sep/Oct/Nov 2025)
* a 2024 AVERAGE needs >= the 2024 daily/monthly prices -> external history; none of our columns reach 2024
  (the oldest reference we can derive is ~19 Sep 2025 from the yoy column).
Under the manager's rule (first collected price held constant back to Jan 2024, flagged) every one of the 107 series
would be backfilled, and the 2024 base would then equal the first collected price -> the rebased series is numerically
identical to today's "first day = 100". This script quantifies how far that flat backfill is from the truth at the two
anchors we CAN reconstruct, and writes the backfill register the manager asked for.
"""
import numpy as np
import pandas as pd

from common import OUT, load, trading_panel, index_keys

d = load()
x = d.sort_values(["key", "price_date", "run_date"]).drop_duplicates(["key", "price_date"], keep="last").copy()
x["ref_ytd"] = x.price / (1 + x.ytd / 100)
x["ref_yoy"] = x.price / (1 + x.yoy / 100)
x["yoy_date"] = x.price_date - pd.DateOffset(years=1)

first = x.groupby("key").first()            # first collected quote per commodity (earliest price_date)
anchor_ytd = x.groupby("key").ref_ytd.median()
oldest_ref = x.yoy_date.min()
print(f"oldest date any of our columns reaches: {oldest_ref.date()} (yoy of the earliest quote) -> 2024 not reachable")
print(f"commodities with a 2024 price from our data: 0 of {d.key.nunique()}")

reg = pd.DataFrame({
    "category": first.category, "commodity": first.commodity, "unit": first.unit, "in_trendx_index": first.in_index,
    "first_actual_price_date": first.price_date.dt.date, "first_run_date": first.run_date.dt.date,
    "first_price": first.price, "source": "Trading Economics commodities table (tradingeconomics.com/commodities)",
    "backfill_rule": "held constant to 2024-01-01; flag=backfilled; excluded from correlation/modelling",
    "implied_close_2025_12_31": anchor_ytd.round(6),
    "first_vs_2025_12_31_pct": ((first.price / anchor_ytd - 1) * 100).round(2),
    "implied_price_1y_before_first": first.ref_yoy.round(6), "date_1y_before_first": first.yoy_date.dt.date,
    "first_vs_1y_before_pct": first.yoy.round(2),
}).reset_index(drop=True)
reg.to_csv(OUT / "backfill_register_2024_base.csv", index=False)
n_all, n_idx = len(reg), int(reg.in_trendx_index.sum())
print(f"backfill needed with no external history: {n_all} of {n_all} series ({n_idx} of the 90 index series, "
      f"{n_all-n_idx} excluded series: Index 12 + Electricity 5)")
print("first actual price_date distribution:", reg.first_actual_price_date.value_counts().sort_index().to_dict())

ix = reg[reg.in_trendx_index]
a = ix.first_vs_2025_12_31_pct.abs()
b = ix.first_vs_1y_before_pct.abs()
print(f"\nhow wrong a flat backfill is at points we CAN check (90 index series):")
print(f"  vs 31-Dec-2025 close: median |gap| {a.median():.1f}%, >10% for {(a>10).sum()}, >25% for {(a>25).sum()}, "
      f">50% for {(a>50).sum()}; max {a.max():.0f}% ({ix.loc[a.idxmax(),'commodity']})")
print(f"  vs one year earlier : median |gap| {b.median():.1f}%, >10% for {(b>10).sum()}, >25% for {(b>25).sum()}, "
      f">50% for {(b>50).sum()}")
# index-level: Jevons of the 90 at the reconstructed anchors, on the first-collected-price base (= what the
# backfilled "2024=100" index would be if it were done honestly at those dates instead of flat)
lg = np.log(ix.implied_close_2025_12_31.values / ix.first_price.values)
lg2 = np.log(ix.implied_price_1y_before_first.values / ix.first_price.values)
print(f"  TrendX(90) on first-collected base (=100): end-2025 level {100*np.exp(lg.mean()):.1f}, "
      f"one year before first quote {100*np.exp(lg2.mean()):.1f}  -> flat backfill would show 100 for both")
top = ix.reindex(a.sort_values(ascending=False).index).head(8)[["commodity", "unit", "first_vs_2025_12_31_pct",
                                                                  "first_vs_1y_before_pct"]]
print("  largest gaps:\n" + top.to_string(index=False))

# what the rule does to the index arithmetic: with all series backfilled, base(2024 avg) = first price, so the
# rebased index equals today's chained Jevons on first day = 100 (up to the chain-vs-direct difference).
panel = trading_panel(d)
ik = index_keys(d)
rebased = 100 * np.exp(np.log(panel[ik] / reg.set_index(reg.category + " | " + reg.commodity).loc[ik, "first_price"]
                              ).mean(axis=1))
print(f"\nrebased '2024=100' index under the rule, 30 Oct 2026: {rebased.iloc[-1]:.2f} "
      f"(first-collected base) - i.e. the label changes, the numbers do not")
# the 'correlation/modelling' exclusion: share of a Jan-2024..Oct-2026 monthly series that would be flagged
months_flagged = len(pd.period_range("2024-01", "2026-09", freq="M"))
print(f"monthly Jan-2024..Oct-2026 series: {months_flagged} of {months_flagged+1} months flagged for every commodity "
      f"-> correlation/modelling over 2024-2026 has nothing left until external history is merged")
