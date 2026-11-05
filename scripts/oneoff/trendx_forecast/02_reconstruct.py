"""(b) Extra history from the change columns, and how consistent it is.

TE's columns are percentages: pct = 1-day, weekly = 1-week, monthly = 1-month, ytd = since last close of 2025,
yoy = 1 year.  Reference price = price / (1 + x/100), anchored at the quote's price_date.
Checks:
  * pct    -> implied previous close vs our own previous distinct close
  * weekly -> implied close 7 days before price_date vs our own close on/as-of that date
  * monthly-> implied close 1 calendar month before; overlaps our data only for price_dates >= ~2 Nov (few) -> check
              against the weekly-implied values and against our first quotes (2 Oct) where they meet
  * ytd    -> implied 31-Dec-2025 close must be the SAME number on every day: dispersion across the 31 runs
  * yoy    -> gives the price ~1 year before each price_date (Oct-Nov 2025): a second, year-ago daily strip
"""
import numpy as np
import pandas as pd

from common import OUT, load

d = load()
x = d.sort_values(["key", "price_date", "run_date"]).drop_duplicates(["key", "price_date"], keep="last").copy()
for c in ["pct", "weekly", "monthly", "ytd", "yoy"]:
    x[f"ref_{c}"] = x["price"] / (1 + x[c] / 100)
x["ref_date_weekly"] = x.price_date - pd.Timedelta(days=7)
# Alignment sweep: which offset makes the implied reference match a close we observed ourselves / the weekly-implied one?
obs_ = x[["key", "price_date", "price"]].rename(columns={"price_date": "dt", "price": "o"})
for col, offs in [("weekly", [5, 6, 7, 8]), ("monthly", [28, 29, 30, 31])]:
    for k in offs:
        t = x[["key", "price_date"]].assign(v=x.price / (1 + x[col] / 100), dt=x.price_date - pd.Timedelta(days=k))
        mm_ = t.merge(obs_, on=["key", "dt"])
        e_ = (mm_.v / mm_.o - 1).abs() * 100
        print(f"   align {col:7s} price_date-{k}d vs our exact close: n={len(mm_):4d} within 0.1%: "
              f"{(e_ < .1).mean() if len(e_) else float('nan'):.0%}")
# empirically best: weekly = price_date - 7 days (exact); monthly = price_date - 29 days (calendar month fits worse)
MONTHLY_OFFSET = pd.Timedelta(days=29)
x["ref_date_monthly"] = x.price_date - MONTHLY_OFFSET
x["ref_date_yoy"] = x.price_date - pd.DateOffset(years=1)


def asof_price(key, date):
    s = x[(x.key == key) & (x.price_date <= date)]
    return s.price.iloc[-1] if len(s) else np.nan


def rel_err(a, b):
    return (a / b - 1) * 100


# 1-day: implied previous close vs our previous distinct close (only when the previous distinct quote is <=4 days back)
x["prev_close"] = x.groupby("key").price.shift()
x["prev_gap"] = (x.price_date - x.groupby("key").price_date.shift()).dt.days
m = x.prev_close.notna() & (x.prev_gap <= 4)
e1 = rel_err(x.loc[m, "ref_pct"], x.loc[m, "prev_close"]).abs()
print(f"1-day pct: n={m.sum()}  |implied prev close - our prev close| median {e1.median():.3f}%  "
      f"p90 {e1.quantile(.9):.3f}%  share within 0.1% {(e1 < .1).mean():.0%}")

# weekly: compare with our own as-of close 7 days earlier (only where that date is inside our window)
w = x[x.ref_date_weekly >= pd.Timestamp("2026-10-02")].copy()
w["our"] = [asof_price(k, dt) for k, dt in zip(w.key, w.ref_date_weekly)]
ew = rel_err(w.ref_weekly, w.our).abs().dropna()
print(f"weekly:    n={len(ew)}  |implied - ours| median {ew.median():.3f}%  p90 {ew.quantile(.9):.3f}%  "
      f"within 0.5% {(ew < .5).mean():.0%}")

# monthly: implied 1-month-ago close vs ours where the reference falls inside our window
mm = x[x.ref_date_monthly >= pd.Timestamp("2026-10-02")].copy()
mm["our"] = [asof_price(k, dt) for k, dt in zip(mm.key, mm.ref_date_monthly)]
em = rel_err(mm.ref_monthly, mm.our).abs().dropna()
print(f"monthly:   n={len(em)} (refs inside our window)  median {em.median():.3f}%  p90 {em.quantile(.9):.3f}%")
# monthly vs weekly-implied for the same reference date (both reconstructed, Sep 25-Oct 2 overlap)
wi = x[["key", "ref_date_weekly", "ref_weekly"]].rename(columns={"ref_date_weekly": "dt", "ref_weekly": "w"})
mi = x[["key", "ref_date_monthly", "ref_monthly"]].rename(columns={"ref_date_monthly": "dt", "ref_monthly": "m"})
j = wi.merge(mi, on=["key", "dt"])
ej = rel_err(j.m, j.w).abs()
print(f"monthly-implied vs weekly-implied same date: n={len(j)} median {ej.median():.3f}%  p90 {ej.quantile(.9):.3f}%")

# ytd: implied 31-Dec-2025 close should be constant per commodity (exclude quotes from the old year: none here)
yt = x.groupby("key").ref_ytd.agg(["median", "min", "max", "count"])
yt["spread_pct"] = (yt["max"] / yt["min"] - 1) * 100
print(f"ytd anchor (31 Dec 2025): commodities {len(yt)}; spread across days median {yt.spread_pct.median():.3f}%, "
      f"p90 {yt.spread_pct.quantile(.9):.3f}%, max {yt.spread_pct.max():.2f}% ({yt.spread_pct.idxmax()})")
print("   largest ytd-anchor spreads:", yt.spread_pct.sort_values().tail(5).round(2).to_dict())

# yoy strip
yo = x[["key", "category", "commodity", "unit", "in_index", "ref_date_yoy", "ref_yoy"]]
n_yoy = yo.groupby("key").ref_date_yoy.nunique()
print(f"yoy strip: {len(yo)} points, {n_yoy.median():.0f} distinct dates per commodity "
      f"({yo.ref_date_yoy.min().date()}..{yo.ref_date_yoy.max().date()})")

# assemble reconstructed history (long format) and the extended daily series Sep..Oct 2026
recs = []
for c, dc in [("weekly", "ref_date_weekly"), ("monthly", "ref_date_monthly"), ("yoy", "ref_date_yoy")]:
    t = x[["key", dc, f"ref_{c}"]].rename(columns={dc: "date", f"ref_{c}": "price"})
    t["source"] = f"implied_{c}"
    recs.append(t)
t = yt[["median"]].reset_index().rename(columns={"median": "price"})
t["date"] = pd.Timestamp("2025-12-31")
t["source"] = "implied_ytd"
recs.append(t)
obs = x[["key", "price_date", "price"]].rename(columns={"price_date": "date"}).assign(source="observed")
hist = pd.concat([obs] + recs, ignore_index=True)
hist.to_csv(OUT / "reconstructed_history_long.csv", index=False)
yt.to_csv(OUT / "ytd_anchor_2025-12-31.csv")

# extended business-day panel Sep 2 .. Oct 30: observed first, then weekly-implied, then monthly-implied
pri = {"observed": 0, "implied_weekly": 1, "implied_monthly": 2}
h = hist[hist.source.isin(pri)].copy()
h["p"] = h.source.map(pri)
h = h.sort_values(["key", "date", "p"]).drop_duplicates(["key", "date"])
wide = h.pivot(index="date", columns="key", values="price").sort_index()
bd = pd.bdate_range("2026-09-01", "2026-10-30")
wide = wide.reindex(wide.index.union(bd)).ffill().reindex(bd)
wide = wide.loc[wide.notna().mean(axis=1) > 0.9]
wide.to_csv(OUT / "extended_panel_sep_oct.csv")
print(f"extended business-day panel: {wide.index[0].date()}..{wide.index[-1].date()} = {len(wide)} days "
      f"(vs 21 observed)")
