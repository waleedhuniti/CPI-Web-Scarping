"""(b) Back out extra history from the % columns and check it is consistent.
pct     -> previous close         P/(1+pct/100)
weekly  -> close 1 week before    P/(1+weekly/100)
monthly -> close 1 month before   P/(1+monthly/100)
ytd     -> last close of 2025     P/(1+ytd/100)       (must be the SAME number on every run)
yoy     -> close 1 year before    P/(1+yoy/100)
"""
import numpy as np, pandas as pd
from common import load, trading_panel, jevons, OUT

d = load()
d = d[d.in_index].copy()
for c in ["pct", "weekly", "monthly", "ytd", "yoy"]:
    d["p_" + c] = d.price / (1 + d[c] / 100)
tp = trading_panel(d.assign(in_index=True))               # observed closes on business days (ffilled)

def rel_err(a, b):
    return (a / b - 1).abs()

# 1) ytd anchor: constant per commodity?
y = d.groupby("key").p_ytd.agg(lambda s: s.max() / s.min() - 1)
print("YTD anchor (31-Dec-2025 close) spread across 31 runs, max/min-1:")
print("  median %.4f%%  90th pct %.4f%%  max %.3f%% (%s)" % (y.median()*100, y.quantile(.9)*100, y.max()*100, y.idxmax()))
print("  commodities with spread > 0.5%:", int((y > .005).sum()), list(y[y > .005].sort_values().index[-8:]))

# 2) weekly / monthly / pct implied price vs what we actually observed
def check(col, offset, label):
    t = d.price_date - offset
    obs = []
    for k, dt in zip(d.key, t):
        s = tp.get(k)
        obs.append(np.nan if s is None or dt < tp.index[0] or dt > tp.index[-1] else s.asof(dt))
    e = rel_err(d["p_" + col], pd.Series(obs, index=d.index)).dropna()
    print(f"{label:<40} n={len(e):4d}  median abs err {e.median()*100:.3f}%  share<0.1% {(e<.001).mean():.0%}"
          f"  share<1% {(e<.01).mean():.0%}  p90 {e.quantile(.9)*100:.2f}%")
    return e
print("\nimplied past price vs our own observed close (quote-date basis):")
check("pct", pd.offsets.BDay(1), "pct -> previous business day")
check("weekly", pd.Timedelta(days=7), "weekly -> price_date - 7 days")
check("monthly", pd.DateOffset(months=1), "monthly -> price_date - 1 calendar month")
# same, but measured from run_date (to see which anchor TE uses)
d2 = d.copy(); d2["price_date"] = d2.run_date
tmp, d = d, d2
check("weekly", pd.Timedelta(days=7), "weekly -> run_date - 7 days")
d = tmp

# 3) reconstructed September 2026 (from monthly) and Oct-Nov 2025 (from yoy), deduplicated by target date
def recon(col, offset):
    r = d.assign(target=d.price_date - offset).sort_values("run_date")
    return r.groupby(["key", "target"])["p_" + col].last().unstack(0).sort_index()
sep = recon("monthly", pd.DateOffset(months=1))
ly = recon("yoy", pd.DateOffset(years=1))
sep = sep[(sep.index >= "2026-08-25") & (sep.index <= "2026-09-30")]
print(f"\nreconstructed Sep-2026 dates: {len(sep)} ({sep.index.min().date()}..{sep.index.max().date()}), "
      f"commodities with >=15 Sep points: {(sep.count() >= 15).sum()}")
print(f"reconstructed year-ago dates: {len(ly)} ({ly.index.min().date()}..{ly.index.max().date()})")
# monthly-implied consistency where the target falls inside our own window (Oct 1..Oct 30 obs)
ins = recon("monthly", pd.DateOffset(months=1))
ins = ins[ins.index >= "2026-10-01"]
if len(ins):
    common = ins.index.intersection(tp.index)
    e = rel_err(ins.loc[common].stack(), tp.loc[common].stack().reindex(ins.loc[common].stack().index)).dropna()
    print(f"monthly-implied vs observed inside window: n={len(e)} median {e.median()*100:.3f}% share<1% {(e<.01).mean():.0%}")

# extended panel: Sep (reconstructed) + Oct (observed), business days, ffilled
cal = pd.bdate_range("2026-09-01", tp.index[-1])
sep_b = sep.reindex(sep.index.union(pd.bdate_range("2026-09-01", "2026-09-30"))).ffill().loc["2026-09-01":"2026-09-30"]
ext = pd.concat([sep_b, tp]).reindex(cal)
ext = ext[[c for c in tp.columns]]
splice = rel_err(sep_b.iloc[-1], tp.iloc[0]).dropna()
print(f"splice check 30-Sep(recon) vs 1-Oct(observed): median jump {splice.median()*100:.2f}%  (normal daily move)")
iext = jevons(ext)
iext = 100 * iext / iext.loc["2026-10-02"]
print("extended index (2 Oct = 100): Sep mean %.2f, Oct mean (bdays) %.2f, 1 Sep %.2f, 30 Sep %.2f"
      % (iext.loc["2026-09"].mean(), iext.loc["2026-10"].mean(), iext.iloc[0], iext.loc["2026-09-30"]))
ext.to_csv(OUT / "panel_extended_sep_oct.csv"); ly.to_csv(OUT / "panel_year_ago.csv")
iext.to_frame("index_ext").to_csv(OUT / "index_extended.csv")
# year-on-year of the index (Jevons on yoy relatives, same commodities)
yo = d[d.run_date == d.run_date.max()]
print("index-level YoY on 2 Nov (geomean of yoy relatives, 90 items): %.2f%%" % ((np.exp(np.log(1 + yo.yoy / 100).mean()) - 1) * 100))
print("index-level YTD on 2 Nov (geomean of ytd relatives): %.2f%%" % ((np.exp(np.log(1 + yo.ytd / 100).mean()) - 1) * 100))

# 4) cross-check monthly-implied against weekly-implied for the same target day (overlap 24-30 Sep)
wk = recon("weekly", pd.Timedelta(days=7))
for lab, off in [("1 calendar month", pd.DateOffset(months=1)), ("30 days", pd.Timedelta(days=30)),
                 ("4 weeks", pd.Timedelta(days=28))]:
    mo = recon("monthly", off)
    ix = mo.index.intersection(wk.index)
    a, b = mo.loc[ix].stack(), wk.loc[ix].stack()
    a, b = a.align(b, join="inner")
    e = rel_err(a, b)
    print(f"monthly({lab}) vs weekly-implied, same target day: n={len(e)} median {e.median()*100:.3f}% share<0.5% {(e<.005).mean():.0%}")
# 5) plausibility: daily volatility of the reconstructed September vs observed October (per commodity, median)
vs = np.log(sep_b).diff().std().median(); vo = np.log(tp).diff().std().median()
print(f"median per-commodity daily log-sd: reconstructed Sep {vs*100:.2f}%  observed Oct {vo*100:.2f}%")
vy = np.log(ly).diff().std().median()
print(f"median per-commodity daily log-sd, reconstructed Oct-2025 window: {vy*100:.2f}%")

# 6) which look-back does TE's "monthly" use? scan offsets against a reference daily series
#    (weekly-implied closes for 23-30 Sep + observed closes from 1 Oct), as-of matching
ref = pd.concat([wk[wk.index < "2026-10-01"], tp]).sort_index()
ref = ref[~ref.index.duplicated(keep="last")]
best = []
for days in range(26, 35):
    t = d.price_date - pd.Timedelta(days=days)
    obs = [ref[k].asof(x) if (k in ref and x >= ref.index[0]) else np.nan for k, x in zip(d.key, t)]
    e = rel_err(d.p_monthly, pd.Series(obs, index=d.index)).dropna()
    best.append((days, len(e), e.median(), (e < .001).mean()))
for b in best:
    print(f"monthly look-back {b[0]} days: n={b[1]:4d} median err {b[2]*100:.3f}% share<0.1% {b[3]:.0%}")
for nb in range(19, 24):
    t = d.price_date - pd.offsets.BDay(nb)
    obs = [ref[k].asof(x) if (k in ref and x >= ref.index[0]) else np.nan for k, x in zip(d.key, t)]
    e = rel_err(d.p_monthly, pd.Series(obs, index=d.index)).dropna()
    print(f"monthly look-back {nb} business days: n={len(e):4d} median err {e.median()*100:.3f}% share<0.1% {(e<.001).mean():.0%}")
# by category, 29 days
t = d.price_date - pd.Timedelta(days=29)
obs = pd.Series([ref[k].asof(x) if (k in ref and x >= ref.index[0]) else np.nan for k, x in zip(d.key, t)], index=d.index)
e = rel_err(d.p_monthly, obs)
print("29-day look-back, share exact(<0.1%) by category:", e.lt(.001)[e.notna()].groupby(d.category).mean().round(2).to_dict())
