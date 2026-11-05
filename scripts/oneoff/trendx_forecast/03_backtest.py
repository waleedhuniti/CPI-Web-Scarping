"""(c)+(d) Honest backtest on the business-day panel, per commodity and for the TrendX(90) index.

Panels:  OBS = 21 observed business days (2 Oct - 30 Oct 2026)
         EXT = 42 business days, observed + Sep 2026 reconstructed from the weekly/monthly columns (02_reconstruct.py)
Holdouts: last H = 5 and H = 10 business days.
Schemes:  fixed origin  - fit once on the first N-H days, forecast h = 1..H
          rolling 1-step - for each of the H holdout days refit on everything before it, forecast 1 day ahead
Methods (all on log price): naive, drift, meanrev (AR(1) with const, OLS), ses, holt_damped, arima (AIC pick among
          (0,1,1),(1,1,0),(1,0,0)+c).
Index:   direct = method applied to the index series; bottom-up = method applied to each of the 90 commodities, then
          aggregated with the same Jevons formula.
Metrics: MAPE (%), MAE (index points for the index), share of commodities where the method's MAE < naive's,
          direction hit-rate (sign of forecast change vs sign of actual change from the forecast origin; flat actuals
          dropped; naive has no direction).
"""
import os
os.environ["PYTHONWARNINGS"] = "ignore"
import sys
import warnings

import numpy as np
import pandas as pd

from common import OUT, load, trading_panel, index_keys, jevons

warnings.filterwarnings("ignore")
from scipy.stats import binomtest  # noqa: E402
from statsmodels.tsa.arima.model import ARIMA  # noqa: E402
from statsmodels.tsa.holtwinters import ExponentialSmoothing, SimpleExpSmoothing  # noqa: E402

FAST = "--fast" in sys.argv  # skip ARIMA in the rolling scheme


def f_naive(y, h):
    return np.repeat(y[-1], h)


def f_drift(y, h):
    mu = np.mean(np.diff(y)) if len(y) > 1 else 0.0
    return y[-1] + mu * np.arange(1, h + 1)


def f_meanrev(y, h):
    a, b = y[:-1], y[1:]
    if np.std(a) < 1e-12:
        return f_naive(y, h)
    phi, c = np.polyfit(a, b, 1)
    phi = float(np.clip(phi, 0.0, 0.999))
    mu = np.mean(y) if phi >= 0.999 else c / (1 - phi)
    if not np.isfinite(mu):
        return f_naive(y, h)
    mu = float(np.clip(mu, y.min(), y.max()))   # keep the attractor inside the observed range
    out, last = [], y[-1]
    for _ in range(h):
        last = mu + phi * (last - mu)
        out.append(last)
    return np.array(out)


def f_ses(y, h):
    if np.std(y) < 1e-12:
        return f_naive(y, h)
    return np.asarray(SimpleExpSmoothing(y, initialization_method="estimated").fit().forecast(h))


def f_holt(y, h):
    if np.std(y) < 1e-12:
        return f_naive(y, h)
    m = ExponentialSmoothing(y, trend="add", damped_trend=True, initialization_method="estimated").fit()
    return np.asarray(m.forecast(h))


def f_arima(y, h):
    if np.std(y) < 1e-12:
        return f_naive(y, h)
    best = None
    for order, trend in [((0, 1, 1), "n"), ((1, 1, 0), "n"), ((1, 0, 0), "c")]:
        try:
            r = ARIMA(y, order=order, trend=trend).fit()
            if best is None or r.aic < best.aic:
                best = r
        except Exception:
            pass
    return f_naive(y, h) if best is None else np.asarray(best.forecast(h))


METHODS = {"naive": f_naive, "drift": f_drift, "meanrev": f_meanrev, "ses": f_ses, "holt_damped": f_holt,
           "arima": f_arima}


def sgn(a, ref, tol=1e-6):
    """direction of a vs ref, with float noise (|a/ref-1| < tol) counted as 'no change'."""
    r = np.asarray(a) / ref - 1
    return np.where(np.abs(r) < tol, 0, np.sign(r))


def fixed_origin(logp, H):
    """dict method -> array (H,) of forecasts, for one log series."""
    tr = logp[:-H]
    return {m: f(tr, H) for m, f in METHODS.items()}


def rolling_1step(logp, H, methods):
    n = len(logp)
    return {m: np.array([METHODS[m](logp[:n - H + i], 1)[0] for i in range(H)]) for m in methods}


def evaluate_commodities(panel, keys, H, tag):
    rows = []
    roll_methods = [m for m in METHODS if not (FAST and m == "arima")]
    fc_store = {m: {} for m in METHODS}
    for k in keys:
        y = np.log(panel[k].values)
        act = panel[k].values[-H:]
        origin = panel[k].values[-H - 1]
        fo = fixed_origin(y, H)
        ro = rolling_1step(y, H, roll_methods)
        prev = panel[k].values[-H - 1:-1]
        for m in METHODS:
            f = np.exp(fo[m])
            fc_store[m][k] = f
            ape = np.abs(f / act - 1) * 100
            ad = sgn(act, origin)
            fd = sgn(f, origin)
            ok = ad != 0
            r = dict(panel=tag, H=H, key=k, method=m, mape_fixed=ape.mean(), ape_end=ape[-1],
                     mae_fixed=np.mean(np.abs(f - act)),
                     dir_hits=int(((fd == ad) & ok & (fd != 0)).sum()), dir_n=int((ok & (fd != 0)).sum()))
            if m in ro:
                f1 = np.exp(ro[m])
                r["mape_roll1"] = np.mean(np.abs(f1 / act - 1) * 100)
                ad1, fd1 = sgn(act, prev), sgn(f1, prev)
                ok1 = (ad1 != 0) & (fd1 != 0)
                r["dir1_hits"], r["dir1_n"] = int(((fd1 == ad1) & ok1).sum()), int(ok1.sum())
            rows.append(r)
    return pd.DataFrame(rows), fc_store


def summarise(res):
    piv = res.pivot_table(index="key", columns="method", values="mae_fixed")
    out = []
    for m, g in res.groupby("method"):
        ok = piv["naive"] > 0
        rel = (piv.loc[ok, m] / piv.loc[ok, "naive"])
        beats = (piv[m] < piv["naive"] * 0.999).mean()
        wins = int((piv[m] < piv["naive"] * 0.999).sum())
        loss = int((piv[m] > piv["naive"] * 1.001).sum())
        p_sign = binomtest(wins, wins + loss, 0.5, alternative="greater").pvalue if wins + loss else np.nan
        out.append(dict(method=m, median_MAPE_fixed=g.mape_fixed.median(), mean_MAPE_fixed=g.mape_fixed.mean(),
                        median_APE_at_H=g.ape_end.median(),
                        median_MAPE_roll1=g.mape_roll1.median() if "mape_roll1" in g else np.nan,
                        share_beats_naive=beats,
                        median_rel_MAE_vs_naive=float(rel.median()), win_loss=f"{wins}/{loss}",
                        sign_test_p=p_sign,
                        dir_hit_fixed=g.dir_hits.sum() / max(g.dir_n.sum(), 1),
                        dir_hit_roll1=g.dir1_hits.sum() / max(g.dir1_n.sum(), 1) if "dir1_n" in g else np.nan))
    return pd.DataFrame(out).set_index("method").round(3)


def evaluate_index(panel, keys, H, fc_store):
    idx = jevons(panel[keys]).values
    act = idx[-H:]
    origin = idx[-H - 1]
    y = np.log(idx)
    fo = fixed_origin(y, H)
    ro = rolling_1step(y, H, list(METHODS) if not FAST else [m for m in METHODS if m != "arima"])
    base = panel[keys].iloc[0].values
    rows = []
    for m in METHODS:
        for kind in ["direct", "bottom_up"]:
            if kind == "direct":
                f = np.exp(fo[m])
            else:
                F = np.vstack([fc_store[m][k] for k in keys])           # (90, H)
                f = 100 * np.exp(np.mean(np.log(F / base[:, None]), axis=0))
            ad, fd = sgn(act, origin), sgn(f, origin)
            ok = (ad != 0) & (fd != 0)
            r = dict(method=m, kind=kind, MAE_pts=np.mean(np.abs(f - act)), MAPE=np.mean(np.abs(f / act - 1)) * 100,
                     err_at_H_pts=f[-1] - act[-1], dir_hit=f"{int(((fd == ad) & ok).sum())}/{int(ok.sum())}")
            if kind == "direct" and m in ro:
                f1 = np.exp(ro[m])
                r["MAE_roll1_pts"] = np.mean(np.abs(f1 - act))
            rows.append(r)
    return pd.DataFrame(rows), idx


def interval_check(panel, keys, H):
    """Random-walk (naive) prediction intervals: sigma from training daily log returns, +-z*sigma*sqrt(h).
    Coverage on the holdout, per commodity, pooled."""
    cov80 = cov95 = n = 0
    for k in keys:
        y = np.log(panel[k].values)
        tr, te = y[:-H], y[-H:]
        s = np.std(np.diff(tr), ddof=1)
        hs = np.sqrt(np.arange(1, H + 1))
        e = np.abs(te - tr[-1])
        if s == 0:
            continue
        cov80 += (e <= 1.2816 * s * hs).sum()
        cov95 += (e <= 1.96 * s * hs).sum()
        n += H
    return cov80 / n, cov95 / n


def main():
    d = load()
    keys = index_keys(d)
    obs = trading_panel(d)
    ext = pd.read_csv(OUT / "extended_panel_sep_oct.csv", index_col=0, parse_dates=True)
    allkeys = list(obs.columns)
    for tag, panel in [("OBS21", obs), ("EXT42", ext)]:
        ks = [k for k in allkeys if k in panel.columns and panel[k].notna().all()]
        ik = [k for k in keys if k in ks]
        print(f"\n================ panel {tag}: {len(panel)} business days, {len(ks)} commodities, "
              f"{len(ik)} index series ================")
        for H in (5, 10):
            res, fc = evaluate_commodities(panel, ks, H, tag)
            res.to_csv(OUT / f"backtest_commodities_{tag}_H{H}.csv", index=False)
            print(f"\n--- the {len(ik)} index commodities, hold-out H={H}, train={len(panel)-H} days ---")
            print(summarise(res[res.key.isin(ik)]).to_string(max_colwidth=12))
            ex = [k for k in ks if k not in ik]
            print(f"    (excluded {len(ex)} series - Index+Electricity - summary, naive vs best:)")
            sx = summarise(res[res.key.isin(ex)])
            print(sx[["median_MAPE_fixed", "share_beats_naive", "median_rel_MAE_vs_naive", "win_loss"]].to_string())
            ir, idx = evaluate_index(panel, ik, H, fc)
            ir.to_csv(OUT / f"backtest_index_{tag}_H{H}.csv", index=False)
            print(f"--- TrendX(90) index, H={H}: actual path {np.round(idx[-H-1:], 2).tolist()}")
            print(ir.round(3).to_string(index=False))
            c80, c95 = interval_check(panel, ks, H)
            print(f"naive random-walk PI coverage on hold-out (pooled commodities): 80% -> {c80:.0%}, 95% -> {c95:.0%}")

        # (d) interval widths for the index and a typical commodity, from the full panel's daily log returns
        idx = jevons(panel[ik])
        s_idx = np.diff(np.log(idx.values)).std(ddof=1)
        s_com = pd.Series({k: np.diff(np.log(panel[k].values)).std(ddof=1) for k in ik})
        print(f"\n(d) daily log-return sd: index {s_idx*100:.3f}%; commodities median {s_com.median()*100:.2f}% "
              f"(p25 {s_com.quantile(.25)*100:.2f}%, p75 {s_com.quantile(.75)*100:.2f}%, max {s_com.max()*100:.2f}% "
              f"{s_com.idxmax()})")
        for h in (1, 5, 10, 21, 63):
            print(f"   h={h:2d} business days: 95% PI half-width index +-{1.96*s_idx*np.sqrt(h)*100:.2f}%  | "
                  f"median commodity +-{1.96*s_com.median()*np.sqrt(h)*100:.1f}%")
        n = 21
        avg_factor = np.sqrt((n + 1) * (2 * n + 1) / (6 * n))
        print(f"   next-month AVERAGE (21 days) vs last level: 95% half-width index +-{1.96*s_idx*avg_factor*100:.2f}%")
        # does the index show momentum / mean reversion? lag-1 autocorrelation of daily index returns
        r = np.diff(np.log(idx.values))
        ac1 = np.corrcoef(r[:-1], r[1:])[0, 1]
        print(f"   lag-1 autocorrelation of index daily returns: {ac1:.2f} (n={len(r)}, 95% band +-{1.96/np.sqrt(len(r)):.2f})")
        acs = []
        for k in ks:
            rr = np.diff(np.log(panel[k].values))
            if rr.std() > 0:
                acs.append(np.corrcoef(rr[:-1], rr[1:])[0, 1])
        acs = np.array(acs)
        print(f"   commodity lag-1 return autocorrelation: median {np.nanmedian(acs):.2f}; "
              f"outside +-{1.96/np.sqrt(len(r)):.2f}: {np.mean(np.abs(acs) > 1.96/np.sqrt(len(r))):.0%} (5% expected by chance)")


if __name__ == "__main__":
    main()
