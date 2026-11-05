"""(a) Inventory: commodities, days, gaps, stale quotes, index membership."""
import pandas as pd

from common import OUT, load, trading_panel, fresh_mask, index_keys, jevons

d = load()
runs = sorted(d.run_date.unique())
cal = pd.date_range(runs[0], runs[-1])
missing_runs = [x.date().isoformat() for x in cal if x not in set(runs)]
print(f"rows={len(d)} commodities={d.key.nunique()} run_dates={len(runs)} "
      f"({pd.Timestamp(runs[0]).date()}..{pd.Timestamp(runs[-1]).date()}); missing calendar run_dates: {missing_runs}")
print("commodities per category:\n", d.drop_duplicates("key").groupby("category").size().to_string())
ik = index_keys(d)
print(f"in TrendX index (excl. Index + Electricity): {len(ik)}")

g = d.groupby(["category", "commodity"]).agg(
    run_days=("run_date", "nunique"), distinct_price_dates=("price_date", "nunique"),
    distinct_prices=("price", "nunique"), stale_runs=("lag_days", lambda s: int((s > 0).sum())),
    stale_gt3=("lag_days", lambda s: int((s > 3).sum())), max_lag_days=("lag_days", "max"),
    median_lag=("lag_days", "median"), first_price_date=("price_date", "min"), last_price_date=("price_date", "max"),
    unit=("unit", "first"), in_index=("in_index", "first")).reset_index()
g.to_csv(OUT / "inventory.csv", index=False)

print(f"\nrow-level staleness: price_date<run_date in {(d.lag_days>0).mean():.1%} of rows; "
      f">1 day {(d.lag_days>1).mean():.1%}; >3 days {(d.lag_days>3).mean():.1%}; >7 days {(d.lag_days>7).mean():.1%}")
print("(the scrape runs ~23:07 UTC the day BEFORE run_date, so lag=1 is the normal 'yesterday's close')")
wk = d[d.run_date.dt.dayofweek < 5]
print(f"weekday run_dates only: lag>1 in {(wk.lag_days>1).mean():.1%} of rows")

panel = trading_panel(d)
fm = fresh_mask(d).reindex(columns=panel.columns, fill_value=False)
print(f"\ntrading panel: {panel.shape[0]} business days {panel.index[0].date()}..{panel.index[-1].date()} x {panel.shape[1]}")
fresh_share = fm.mean()
print("commodities with a fresh quote on <60% of business days:")
low = fresh_share[fresh_share < 0.6].sort_values()
for k, v in low.items():
    print(f"   {k:45s} fresh {v:.0%}  distinct prices {panel[k].nunique()}")
flat = [k for k in panel.columns if panel[k].nunique() <= 3]
print(f"near-flat series (<=3 distinct closes over the month): {len(flat)} -> {flat}")
print("\nbusiness days with no fresh quote for >25% of index series:",
      [x.date().isoformat() for x, v in fm[ik].mean(axis=1).items() if v < 0.75])

idx = jevons(panel[ik])
idx.rename("trendx_90").to_csv(OUT / "index_business_days.csv")
print(f"\nTrendX(90) on business-day panel, 2 Oct=100: last {idx.iloc[-1]:.2f}; Oct mean {idx.mean():.2f}; "
      f"daily log-change sd {pd.Series(idx).pipe(lambda s: (s/s.shift()).apply(lambda r: __import__('math').log(r))).std()*100:.2f}%")
