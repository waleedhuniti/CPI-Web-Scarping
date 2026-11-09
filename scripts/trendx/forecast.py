"""Monthly forecasts for the TrendX store (base 2024 = 100): every series with enough REAL history, and the index.

    python3 scripts/trendx/forecast.py <store dir> [horizon months, default 6]

Method, chosen per series by a rolling-origin backtest over the last 12 months (horizons 1 and 3, errors in log space):
  naive      y[t+h] = y[t]
  drift      y[t+h] = y[t] + h * d, d = mean monthly log change over the last 24 months, shrunk by half towards zero
  damped     damped-trend exponential smoothing (alpha .5, beta .1, phi .9)
A method replaces naive only when its backtest MAE is at least 5 % lower; otherwise the forecast is "no change" (naive): with
two to three years of monthly data that is usually the honest answer. Intervals: the 1-step backtest residual sigma, scaled by
sqrt(h) and widened by 1.25 (the daily research found nominal bands too narrow); z = 1.2816 (80 %) and 1.96 (95 %), in log
space, so the bands are asymmetric in levels. Carried-back values (obs_status E) are never used: a series needs >= 12 real
months. The last month of the store is usually partial (our own collection so far this month): it is the forecast origin and
is marked so. Output: forecast.json (for the portal) and forecast.csv.
"""
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

Z80, Z95, WIDEN, MIN_N, IMPROVE = 1.2816, 1.96, 1.25, 12, 0.05


def months_after(ym, h):
    y, m = map(int, ym.split("-")); m += h
    while m > 12: m -= 12; y += 1
    return f"{y:04d}-{m:02d}"


def f_naive(y, h): return y[-1]


def f_drift(y, h):
    w = y[-25:] if len(y) > 25 else y
    d = (w[-1] - w[0]) / (len(w) - 1) if len(w) > 1 else 0.0
    return y[-1] + h * d * 0.5


def f_damped(y, h, alpha=0.5, beta=0.1, phi=0.9):
    lvl, tr = y[0], (y[1] - y[0]) if len(y) > 1 else 0.0
    for v in y[1:]:
        prev = lvl
        lvl = alpha * v + (1 - alpha) * (prev + phi * tr)
        tr = beta * (lvl - prev) + (1 - beta) * phi * tr
    return lvl + sum(phi ** k for k in range(1, h + 1)) * tr


METHODS = {"naive": f_naive, "drift": f_drift, "damped": f_damped}


def backtest(y, hs=(1, 3), last=12):
    """rolling origin over the last `last` months: MAE per method per horizon, and the 1-step residuals of each method."""
    n = len(y); mae = {m: {h: [] for h in hs} for m in METHODS}; res1 = {m: [] for m in METHODS}
    for o in range(max(4, n - last - max(hs)), n - 1):
        hist = y[: o + 1]
        for m, f in METHODS.items():
            for h in hs:
                if o + h < n:
                    e = y[o + h] - f(hist, h); mae[m][h].append(abs(e))
                    if h == 1: res1[m].append(e)
    out = {m: {h: (statistics.fmean(v) if v else None) for h, v in d.items()} for m, d in mae.items()}
    return out, res1


def forecast_series(vals, origin_ym, H):
    """vals: list of (ym, level) real observations sorted; returns dict or None."""
    y = [math.log(v) for _, v in vals if v and v > 0]
    if len(y) < MIN_N: return None
    bt, res1 = backtest(y)
    score = {m: sum(v for v in d.values() if v is not None) for m, d in bt.items() if all(v is not None for v in d.values())}
    if "naive" not in score: return None
    best = min(score, key=score.get)
    method = best if score[best] <= score["naive"] * (1 - IMPROVE) else "naive"
    r = res1[method] or res1["naive"]
    sigma = (statistics.pstdev(r) if len(r) > 1 else abs(r[0]) if r else 0.05) * WIDEN
    f = METHODS[method]; pts = []
    for h in range(1, H + 1):
        mu = f(y, h); s = sigma * math.sqrt(h)
        pts.append(dict(period=months_after(origin_ym, h), h=h, mean=round(math.exp(mu), 3), lo80=round(math.exp(mu - Z80 * s), 3), hi80=round(math.exp(mu + Z80 * s), 3), lo95=round(math.exp(mu - Z95 * s), 3), hi95=round(math.exp(mu + Z95 * s), 3)))
    return dict(method=method, n_obs=len(y), sigma_log=round(sigma, 5), backtest={m: {str(h): (round(v, 5) if v is not None else None) for h, v in d.items()} for m, d in bt.items()}, last=round(math.exp(y[-1]), 3), points=pts)


def main(store, H=6):
    store = Path(store)
    S = list(csv.DictReader(open(store / "series.csv", encoding="utf-8")))
    O = list(csv.DictReader(open(store / "observations.csv", encoding="utf-8")))
    by = defaultdict(list)
    for o in O:
        if o["obs_status"] == "A" and o["value_2024eq100"] not in ("", None):
            by[o["series_id"]].append((o["period"], float(o["value_2024eq100"]), o["source"]))
    origin = max(o["period"] for o in O)
    partial = any(o["source"] == "te" and o["period"] == origin for o in O)
    out = {"built": date.today().isoformat(), "origin": origin, "origin_partial": partial, "horizon": H, "base": "mean of 2024 = 100",
           "method_note": __doc__.split("Method,")[1].split("Output:")[0].strip(), "series": {}, "index": {}}
    rows = []
    for s in S:
        sid = s["series_id"]; vals = sorted(by.get(sid, []))
        fc = forecast_series([(p, v) for p, v, _ in vals], origin, H) if vals and vals[-1][0] == origin or (vals and len(vals) >= MIN_N) else None
        if fc is None:
            out["series"][sid] = dict(commodity=s["commodity"], category=s["category"], unit=s["unit"], in_index=int(s["in_index"]), status="insufficient_history", n_obs=len(vals),
                                      note="carried back: no real monthly history yet" if s["base_method"] != "actual" else "fewer than 12 real months")
            continue
        last_real = vals[-1][0]
        if last_real != origin:   # series ends before the origin (no quote this month): forecast from its own last month
            fc = forecast_series([(p, v) for p, v, _ in vals], last_real, H)
        out["series"][sid] = dict(commodity=s["commodity"], category=s["category"], unit=s["unit"], in_index=int(s["in_index"]), status="ok", origin=last_real, base_2024_mean=s["base_2024_mean"], proxy=int(s["proxy"]), **fc)
        for p in fc["points"]:
            rows.append(dict(series_id=sid, commodity=s["commodity"], origin=last_real, **p, method=fc["method"], sigma_log=fc["sigma_log"], last=fc["last"]))
    # the index: forecast the two monthly index columns directly
    I = list(csv.DictReader(open(store / "index_2024.csv", encoding="utf-8")))
    for col, key in (("trendx_2024eq100_actual_history", "actual_history"), ("trendx_2024eq100_all_series", "all_series")):
        vals = [(r["period"], float(r[col])) for r in I if r[col] not in ("", None)]
        fc = forecast_series(vals, vals[-1][0], H) if vals else None
        out["index"][key] = dict(status="ok", origin=vals[-1][0], history=[{"period": p, "value": v} for p, v in vals], **fc) if fc else dict(status="insufficient_history", n_obs=len(vals))
        if fc:
            for p in fc["points"]: rows.append(dict(series_id=f"index_{key}", commodity=f"TrendX index ({key})", origin=vals[-1][0], **p, method=fc["method"], sigma_log=fc["sigma_log"], last=fc["last"]))
    (store / "forecast.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    with open(store / "forecast.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["empty"]); w.writeheader(); w.writerows(rows)
    ok = [s for s in out["series"].values() if s["status"] == "ok"]
    meth = defaultdict(int)
    for s in ok: meth[s["method"]] += 1
    print(f"{len(ok)} series forecast ({dict(meth)}), {len(out['series']) - len(ok)} without enough real history; origin {origin}{' (partial)' if partial else ''}; "
          f"index: " + ", ".join(f"{k} {v.get('last')} -> {v['points'][-1]['mean'] if v.get('points') else '-'} ({v.get('method')})" for k, v in out["index"].items()))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 6)
