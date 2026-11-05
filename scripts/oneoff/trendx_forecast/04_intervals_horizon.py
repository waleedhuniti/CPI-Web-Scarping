"""(d) Forecast-interval width and credible horizon.
Random-walk (naive) intervals: log level +- z * sigma * sqrt(h), sigma from training daily log-changes.
Checked empirically: coverage of 80% / 95% intervals in the rolling backtest (03_backtest outputs).
Monthly-mean intervals: for a random walk the average of the next N days has sd sigma*sqrt((N+1)(2N+1)/(6N))."""
import numpy as np, pandas as pd
from common import load, trading_panel, run_panel, jevons, OUT

d = load()
tp, rp = trading_panel(d), run_panel(d)
ext = pd.read_csv(OUT / "panel_extended_sep_oct.csv", index_col=0, parse_dates=True).ffill().bfill()
it, ir = jevons(tp), jevons(rp)
ie = jevons(ext); ie = 100 * ie / ie.loc["2026-10-02"]
Z = {"80%": 1.2816, "95%": 1.96}

print("daily sd of index log-changes:")
sig = {}
for lab, s in [("trading days Oct (22)", it), ("run dates Oct-2Nov (31, incl. weekends)", ir),
               ("trading days Sep(recon)+Oct (44)", ie)]:
    r = np.log(s).diff().dropna(); sig[lab] = r.std()
    ac1 = r.autocorr(1)
    print(f"  {lab:<42} sd {r.std()*100:.3f}%  mean {r.mean()*100:+.3f}%  lag-1 autocorr {ac1:+.2f}")
# variance ratio: is the 5-day variance 5x the 1-day variance (random walk) or less (mean reversion)?
for lab, s in [("Oct trading", it), ("Sep+Oct trading", ie)]:
    l = np.log(s.values); v1 = np.var(np.diff(l), ddof=1); v5 = np.var(l[5:] - l[:-5], ddof=1)
    print(f"  variance ratio VR(5) {lab}: {v5/(5*v1):.2f}  (1 = random walk, <1 mean reversion, >1 momentum)")

# empirical coverage of naive RW intervals in the rolling backtest
def coverage(path, label):
    df = pd.read_csv(path)
    df = df[(df.scheme == "rolling") & (df.method == "naive")]
    return df
for name, s in [("trading", it), ("extended", ie)]:
    df = pd.read_csv(OUT / f"bt_index_direct_{name}.csv")
    df = df[(df.scheme == "rolling") & (df.method == "naive")]
    l = np.log(s.values)
    cov = {k: [] for k in Z}
    for _, r in df.iterrows():
        sd = np.std(np.diff(l[: int(r.origin)]), ddof=1) * np.sqrt(r.step)
        e = abs(np.log(r.actual / r.forecast))
        for k, z in Z.items():
            cov[k].append(e <= z * sd)
    print(f"index naive-RW interval coverage ({name}, rolling, n={len(df)}): " +
          ", ".join(f"{k} nominal -> {np.mean(v):.0%}" for k, v in cov.items()))
cdf = pd.read_csv(OUT / "bt_commodities_trading.csv.gz")
cdf = cdf[(cdf.scheme == "rolling") & (cdf.method == "naive")]
lp = np.log(tp.ffill().bfill())
cv = {k: [] for k in Z}
for (key, o), g in cdf.groupby(["key", "origin"]):
    sd0 = lp[key].values[:o]; sd0 = np.std(np.diff(sd0), ddof=1)
    for _, r in g.iterrows():
        e = abs(np.log(r.actual / r.forecast)); sd = sd0 * np.sqrt(r.step)
        for k, z in Z.items():
            cv[k].append(e <= z * sd + 1e-12)
print("commodity naive-RW interval coverage (rolling, all 90): " + ", ".join(f"{k} -> {np.mean(v):.0%}" for k, v in cv.items()))

# interval half-widths for the index, by horizon (trading days), using the larger (more honest) sigma
s_hi = max(sig.values()); s_lo = min(sig.values())
print(f"\nindex 95% interval half-width (+-%, RW, sigma {s_lo*100:.3f}%..{s_hi*100:.3f}% per trading day):")
for h, lab in [(1, "1 day"), (5, "1 week"), (10, "2 weeks"), (21, "1 month"), (63, "3 months")]:
    print(f"  {lab:<9} +-{1.96*s_lo*np.sqrt(h)*100:.2f}% .. +-{1.96*s_hi*np.sqrt(h)*100:.2f}%")

# November monthly mean (what TrendX publishes): forecast from the last observed value
def mean_sd(sigma, N, lead=0):
    # average of RW at steps lead+1 .. lead+N
    steps = np.arange(lead + 1, lead + N + 1)
    cov = np.minimum.outer(steps, steps)
    return sigma * np.sqrt(cov.sum()) / N
last_run = ir.iloc[-1]; oct_mean = ir[(ir.index >= "2026-10-02") & (ir.index <= "2026-10-31")].mean()
N_nov = len(pd.bdate_range("2026-11-03", "2026-11-30"))       # remaining Nov trading days after the 2 Nov run
for lab, sgm in [("low sigma", s_lo), ("high sigma", s_hi)]:
    sd = mean_sd(sgm, N_nov)
    lo95, hi95 = last_run * np.exp(-1.96 * sd), last_run * np.exp(1.96 * sd)
    lo80, hi80 = last_run * np.exp(-1.2816 * sd), last_run * np.exp(1.2816 * sd)
    print(f"\nNovember mean, naive point {last_run:.2f} (Oct mean {oct_mean:.2f}; base 2 Oct=100) [{lab}]:"
          f" 80% {lo80:.2f}-{hi80:.2f}, 95% {lo95:.2f}-{hi95:.2f}  (sd {sd*100:.2f}%)")
    sdd = mean_sd(sgm, 22, lead=N_nov)
    print(f"December mean [{lab}]: 95% +-{1.96*sdd*100:.2f}%   | Q1-2027 mean: 95% +-"
          f"{1.96*mean_sd(sgm, 63, lead=N_nov+22)*100:.2f}%")
# which categories drive the risk
cats = d[d.in_index].drop_duplicates("key").set_index("key").category
lr = np.log(tp).diff().dropna(how="all")
print("\nmedian daily sd by category (trading days): " +
      ", ".join(f"{c} {lr[cats[cats == c].index].std().median()*100:.2f}%" for c in sorted(cats.unique())))
