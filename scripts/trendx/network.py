"""TrendX dependency network ("what moves this commodity, and what it moves in our numbers") and a small numpy neural-network
forecaster with honest rolling-origin backtests.

    python3 -I scripts/trendx/network.py --store data/trendx/store \
        --wb data/trendx/raw/WB_CMO-Historical-Data-Monthly_<date>.xlsx \
        --ppi <private Dubai PPI json> --out <scratch dir>/network.json [--refit-every 1] [--no-cpi]

Data
- Long history: World Bank Pink Sheet "Monthly Prices" (CC BY 4.0), column per TrendX series from the MAP table of
  build_history_store.py (EIA-kind series use their WB equivalent; gasoline / heating oil / propane have none and use the
  store's own 2024+ months, too short for edges or the network model).
- Current level and forecast origin: the store's history_2024.json (2024 mean = 100, real observations only, the partial
  last month treated as unknown).
- UAE CPI, all items and 12 COICOP divisions, monthly: GCC-Stat Marsa SDMX REST (open licence with citation
  "Source: GCC-Statistical Centre, Sultanate of Oman http://gccstat.org"). One request, one retry; a refusal is recorded and
  the network is built without CPI nodes.
- Dubai PPI, 4-digit ISIC activities and the general index: the private PPI file (never written to the repository; the output
  of this script lives in the scratchpad, the repository gets the script and the Arabic method note only).

Method: monthly log changes from 1990-01 (earlier World Bank history is often annual contract prices repeated monthly).
Edges: Pearson r of the target's change on the driver's change lagged 0..6 months (best lag kept) over >= 36 common months,
|r| >= 0.25, plus a ridge beta controlling for the target's own lag-1 change. Score = |r| / max |r| within kind.
Network model: per target an MLP (24 tanh units, Adam, L2, early stopping on a validation tail, 5-seed ensemble) on the
target's own lags 1..3 and the best lag (1..3) of its top-6 drivers, predicting the 1-, 2- and 3-month cumulative log change.
Backtest: 24 rolling origins, refit at each origin, MAE in percent of the origin level, against naive (no change) and ridge.
Numpy only (no sklearn/torch).
"""
import argparse
import csv
import json
import math
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # the repository's own code: the MAP table is read from build_history_store, not retyped
from build_history_store import MAP, read_wb  # noqa: E402

START = "1990-01"
MIN_OVERLAP, R_MIN, MAX_LAG = 36, 0.25, 6
ORIGINS, HS = 24, (1, 2, 3)
HIDDEN, SEEDS, LR, WD, MAX_EPOCHS, PATIENCE = 24, 5, 0.005, 1e-3, 500, 40
GCC_URL = ("https://sdmx.marsa.gccstat.org/FusionRegistry/ws/public/sdmxapi/rest/data/"
           "GCCSTAT.ES,DF_ES_CPI,1.0/ARE.IDX.M./all/?format=csv")
GCC_CITE = "Source: GCC-Statistical Centre, Sultanate of Oman http://gccstat.org"

LABEL_AR = {
    "crude_oil": "النفط الخام (WTI)", "brent": "خام برنت", "natural_gas": "الغاز الطبيعي (هنري هب)", "gasoline": "البنزين",
    "heating_oil": "زيت التدفئة", "propane": "البروبان", "coal": "الفحم", "eu_gas": "الغاز الأوروبي (TTF)",
    "german_gas": "الغاز الألماني", "uk_gas": "الغاز البريطاني", "lng_jkm": "الغاز المسال (JKM)",
    "urals_oil": "خام الأورال (بديل: خام دبي)", "gold": "الذهب", "silver": "الفضة", "platinum": "البلاتين", "copper": "النحاس",
    "iron_ore": "خام الحديد", "iron_ore_cny": "خام الحديد (يوان)", "soybeans": "فول الصويا", "wheat": "القمح", "corn": "الذرة",
    "rice": "الأرز", "palm_oil": "زيت النخيل", "rubber": "المطاط", "coffee": "البن", "cotton": "القطن", "sugar": "السكر",
    "cocoa": "الكاكاو", "tea": "الشاي", "sunflower_oil": "زيت دوار الشمس", "rapeseed": "بذور اللفت (بديل: زيت اللفت)",
    "orange_juice": "عصير البرتقال", "lumber": "الخشب", "beef": "لحوم الأبقار", "poultry": "الدواجن", "aluminum": "الألمنيوم",
    "lead": "الرصاص", "tin": "القصدير", "zinc": "الزنك", "nickel": "النيكل", "urea": "اليوريا",
    "di-ammonium": "فوسفات ثنائي الأمونيوم (DAP)",
}
COICOP_AR = {
    "00": "الرقم القياسي العام لأسعار المستهلك", "01": "الأغذية والمشروبات غير الكحولية", "02": "المشروبات الكحولية والتبغ",
    "03": "الملابس والأحذية", "04": "السكن والمياه والكهرباء والغاز وأنواع الوقود الأخرى",
    "05": "الأثاث والتجهيزات المنزلية وصيانة المنزل", "06": "الصحة", "07": "النقل", "08": "الاتصالات", "09": "الترفيه والثقافة",
    "10": "التعليم", "11": "المطاعم والفنادق", "12": "سلع وخدمات متنوعة",
}
# The prototype's commodity keys (PPI file "map": c1/c2 per 4-digit activity) -> TrendX series that carry that commodity.
PRIOR_KEY = {
    "DUBAI": ["urals_oil", "brent", "crude_oil"], "BRENT": ["brent", "crude_oil", "urals_oil"],
    "NGAS": ["eu_gas", "lng_jkm", "natural_gas", "german_gas", "uk_gas"], "GOLD": ["gold"], "ALUM": ["aluminum"],
    "COPP": ["copper"], "NICK": ["nickel"], "IRON": ["iron_ore", "iron_ore_cny"], "STEEL": ["iron_ore", "iron_ore_cny"],
    "PLAST": ["brent", "crude_oil", "urals_oil", "natural_gas", "eu_gas"], "CHEM": ["natural_gas", "eu_gas", "brent", "crude_oil", "urals_oil"],
    "CEMENT": ["coal", "natural_gas"], "FERT": ["urea", "di-ammonium", "natural_gas"], "PULP": ["lumber"],
    "WHEAT": ["wheat"], "BARLEY": ["wheat", "corn"], "SUGAR": ["sugar"], "PALM": ["palm_oil"], "SOY": ["soybeans"],
    "SUNF": ["sunflower_oil", "palm_oil"], "POULT": ["poultry", "corn", "soybeans"], "BEEF": ["beef"], "COCOA": ["cocoa"],
}
ENERGY = ["brent", "crude_oil", "urals_oil", "natural_gas", "eu_gas", "lng_jkm", "coal", "german_gas", "uk_gas"]
FOOD_CATS = ("Agricultural", "Livestock")
CPI_PRIOR = {"00": ENERGY, "04": ENERGY, "07": ["brent", "crude_oil", "urals_oil", "gasoline", "heating_oil"]}  # + food -> 01, 11


def mi(ym):
    y, m = ym.split("-"); return int(y) * 12 + int(m) - 1


def ym(i):
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


# ----------------------------------------------------------------------------------------------------------- data loading
def load_store(store):
    rows = [r for r in csv.DictReader(open(Path(store) / "series.csv", encoding="utf-8")) if r["base_method"] == "actual"]
    hist = json.load(open(Path(store) / "history_2024.json", encoding="utf-8"))
    last_full = ym(mi(hist["span"][1]) - 1)  # the last month of the store is partial (our own collection so far)
    return rows, hist, last_full


def commodity_series(rows, hist, wb_path, last_full):
    """id -> dict(level_log: {month int: log price}, label, category, source, wbcol). WB history for the log changes; the
    store's 2024+ real months for the three EIA-only series."""
    wb, units, updated = read_wb(wb_path)
    out = {}
    for r in rows:
        sid, m = r["series_id"], MAP[r["commodity"]]
        col = m.get("col") or m.get("wb")
        if col:
            lv = {mi(k): math.log(v) for k, v in wb[col].items() if v and v > 0 and mi(k) <= mi(last_full)}
            src = f"World Bank CMO Pink Sheet ({updated}), column '{col.strip()}' {units[col]}, {ym(min(lv))}..{ym(max(lv))}"
        else:
            lv = {mi(o[0]): math.log(o[2]) for o in hist["obs"][sid] if o[4] == 0 and o[2] > 0 and mi(o[0]) <= mi(last_full)}
            src = f"no World Bank column; TrendX store (EIA, 2024 = 100) {ym(min(lv))}..{ym(max(lv))} only"
        if r.get("proxy") == "1" and r.get("proxy_of"): src += f"; proxy: {r['proxy_of']}"
        out[sid] = dict(level_log=lv, label=r["commodity"], category=r["category"], source=src, wbcol=col or f"store:{sid}")
    return out


def store_levels(hist, last_full):
    lv = {}
    for sid, obs in hist["obs"].items():
        real = {o[0]: o[2] for o in obs if o[4] == 0 and o[2]}
        if last_full in real: lv[sid] = (last_full, real[last_full])
        elif real:
            k = max(p for p in real if p <= last_full); lv[sid] = (k, real[k])
    return lv


def fetch_gcc_cpi(dl_dir, issues):
    """UAE CPI by COICOP division from GCC-Stat Marsa SDMX: one request, one retry on a plain timeout only; a refused
    answer (403/429/challenge) is recorded and never routed around. Returns {code: {month int: log index}} or {}."""
    import requests
    dl_dir.mkdir(parents=True, exist_ok=True); f = dl_dir / "are_cpi_idx_m.csv"
    if not f.exists():
        for attempt in (1, 2):
            try:
                rsp = requests.get(GCC_URL, timeout=60, headers={"User-Agent": "TrendX network (Digital Dubai CPI research)"})
            except requests.Timeout:
                if attempt == 1: time.sleep(3); continue
                issues.append("GCC-Stat SDMX timed out twice; network built without CPI nodes"); return {}, None
            except Exception as e:  # noqa: BLE001
                issues.append(f"GCC-Stat SDMX request failed ({type(e).__name__}); network built without CPI nodes"); return {}, None
            if rsp.status_code == 200 and rsp.text.startswith(("﻿COUNTRY", "COUNTRY")):
                f.write_text(rsp.text, encoding="utf-8"); break
            issues.append(f"GCC-Stat SDMX refused/unexpected answer (HTTP {rsp.status_code}); recorded as refused, "
                          "network built without CPI nodes"); return {}, None
    series, names = {}, {}
    for r in csv.reader(open(f, encoding="utf-8-sig")):
        if r[0] != "ARE" or r[2] != "IDX" or r[4] != "M": continue
        code, name, per, val = r[6], r[7].strip('"'), r[8], r[9]
        try: v = float(val)
        except ValueError: continue
        if v > 0: series.setdefault(code, {})[mi(per)] = math.log(v); names[code] = name
    return series, names


def load_ppi(path):
    d = json.load(open(path, encoding="utf-8"))
    months = [mi(m) for m in d["months"]]
    out = {}
    for s in d["series"]:
        if s["c"] == "X" or s["lv"] == "حد رابع":
            lv = {months[i]: math.log(v) for i, v in enumerate(s["v"]) if v is not None and v > 0}
            if lv: out[s["c"]] = dict(level_log=lv, name_en=s["e"].strip() or s["n"], name_ar=s["n"] or s["e"])
    return out, d.get("map", {})


# ------------------------------------------------------------------------------------------------------------- the matrix
def build_matrix(nodes, t0, t1):
    """D[node, t] = log change month t over t-1 for t in [t0, t1]; NaN where either level is missing."""
    T = t1 - t0 + 1; D = np.full((len(nodes), T), np.nan)
    for i, n in enumerate(nodes):
        lv = n["level_log"]
        for t in range(t0, t1 + 1):
            if t in lv and (t - 1) in lv: D[i, t - t0] = lv[t] - lv[t - 1]
    return D


def lag_corr(D, j, lag, tmax=None):
    """Pearson r of D[j, t] on D[:, t-lag] for every driver row, over their common months (<= tmax); returns r, n."""
    T = D.shape[1] if tmax is None else tmax + 1
    Y = D[j, lag:T]; X = D[:, :T - lag]
    mask = np.isfinite(X) & np.isfinite(Y)[None, :]
    n = mask.sum(1); Xm = np.where(mask, X, 0.0); Ym = np.where(mask, Y[None, :], 0.0)
    sx, sy = Xm.sum(1), Ym.sum(1); sxx, syy, sxy = (Xm * Xm).sum(1), (Ym * Ym).sum(1), (Xm * Ym).sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        den = np.sqrt((n * sxx - sx ** 2) * (n * syy - sy ** 2))
        r = np.where(den > 0, (n * sxy - sx * sy) / den, np.nan)
    return r, n


def ridge_beta(D, i, j, lag):
    """beta of target j's change on driver i's change lagged `lag`, controlling for the target's own lag-1 change."""
    T = D.shape[1]; L = max(lag, 1)
    y = D[j, L:]; x1 = D[i, L - lag:T - lag]; x2 = D[j, L - 1:T - 1]
    m = np.isfinite(y) & np.isfinite(x1) & np.isfinite(x2)
    if m.sum() < MIN_OVERLAP: return None
    X = np.column_stack([x1[m], x2[m]]); yv = y[m]
    mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1.0; Xs = (X - mu) / sd; yc = yv - yv.mean()
    n = len(yv); b = np.linalg.solve(Xs.T @ Xs + 0.01 * n * np.eye(2), Xs.T @ yc)
    return float(b[0] / sd[0])


# ------------------------------------------------------------------------------------------------------- the neural network
class MLP:
    def __init__(self, n_in, n_out, seed, hidden=HIDDEN):
        rng = np.random.default_rng(seed)
        self.p = [rng.normal(0, 1 / math.sqrt(n_in), (n_in, hidden)), np.zeros(hidden),
                  rng.normal(0, 1 / math.sqrt(hidden), (hidden, n_out)), np.zeros(n_out)]

    def forward(self, X, p=None):
        W1, b1, W2, b2 = p or self.p; H = np.tanh(X @ W1 + b1); return H @ W2 + b2, H

    def fit(self, X, Y, Xv, Yv, lr=LR, wd=WD, epochs=MAX_EPOCHS, patience=PATIENCE):
        m = [np.zeros_like(a) for a in self.p]; v = [np.zeros_like(a) for a in self.p]
        best, best_p, wait, b1, b2, eps = np.inf, [a.copy() for a in self.p], 0, 0.9, 0.999, 1e-8
        n = len(X)
        for ep in range(1, epochs + 1):
            W1, bb1, W2, bb2 = self.p
            out, H = self.forward(X); err = out - Y  # n x k
            g_out = 2 * err / (n * Y.shape[1])
            gW2 = H.T @ g_out + 2 * wd * W2; gb2 = g_out.sum(0)
            gH = g_out @ W2.T * (1 - H ** 2)
            gW1 = X.T @ gH + 2 * wd * W1; gb1 = gH.sum(0)
            for k, g in enumerate([gW1, gb1, gW2, gb2]):
                m[k] = b1 * m[k] + (1 - b1) * g; v[k] = b2 * v[k] + (1 - b2) * g * g
                self.p[k] = self.p[k] - lr * (m[k] / (1 - b1 ** ep)) / (np.sqrt(v[k] / (1 - b2 ** ep)) + eps)
            vl = float(np.mean((self.forward(Xv)[0] - Yv) ** 2))
            if vl < best - 1e-7: best, best_p, wait = vl, [a.copy() for a in self.p], 0
            else:
                wait += 1
                if wait >= patience: break
        self.p = best_p
        return self


class Scaler:
    def fit(self, A): self.mu = A.mean(0); self.sd = A.std(0); self.sd[self.sd == 0] = 1.0; return self
    def t(self, A): return (A - self.mu) / self.sd
    def inv(self, A): return A * self.sd + self.mu


class Fitted:
    """ensemble of MLPs + ridge on the same standardized features, fitted once per origin and reusable for later origins."""

    def __init__(self, Xtr, Ytr, seeds=SEEDS):
        n = len(Xtr); nv = max(12, int(round(0.15 * n)))
        self.sx, self.sy = Scaler().fit(Xtr[:-nv]), Scaler().fit(Ytr[:-nv])
        self.Xs, self.Ys = self.sx.t(Xtr), self.sy.t(Ytr)
        self.nets = [MLP(self.Xs.shape[1], self.Ys.shape[1], seed).fit(self.Xs[:-nv], self.Ys[:-nv], self.Xs[-nv:], self.Ys[-nv:]) for seed in range(seeds)]
        A = np.column_stack([np.ones(n), self.Xs]); best = (np.inf, None)
        for lam in (1.0, 10.0, 100.0, 1000.0):  # ridge: intercept + standardized features, lambda by the validation tail
            R = lam * np.eye(A.shape[1]); R[0, 0] = 0
            B = np.linalg.solve(A[:-nv].T @ A[:-nv] + R, A[:-nv].T @ self.Ys[:-nv])
            vmae = float(np.mean(np.abs(A[-nv:] @ B - self.Ys[-nv:])))
            if vmae < best[0]: best = (vmae, lam)
        R = best[1] * np.eye(A.shape[1]); R[0, 0] = 0
        self.B = np.linalg.solve(A.T @ A + R, A.T @ self.Ys)

    def predict(self, xq):
        Xq = self.sx.t(xq[None, :])
        nn = self.sy.inv(np.mean([net.forward(Xq)[0] for net in self.nets], axis=0))[0]
        rd = self.sy.inv(np.column_stack([np.ones(1), Xq]) @ self.B)[0]
        return nn, rd

    def pieces(self): return self.nets, self.sx, self.sy, self.Xs, self.Ys


def permutation_importance(pieces, seed=0):
    nets, sx, sy, Xs, Ys = pieces; rng = np.random.default_rng(seed)
    def mse(X): return float(np.mean((np.mean([n.forward(X)[0] for n in nets], axis=0) - Ys) ** 2))
    base = mse(Xs); out = []
    for k in range(Xs.shape[1]):
        Xp = Xs.copy(); Xp[:, k] = rng.permutation(Xp[:, k]); out.append(max(0.0, mse(Xp) - base))
    mx = max(out) if out and max(out) > 0 else 1.0
    return [o / mx for o in out]


def design(D, j, feats):
    """rows t (<= tmax) with X[t] = features at t (lags >= 1) and Y[t, h-1] = sum of D[j, t+1..t+h]; returns X, Y, t index."""
    T = D.shape[1]; Xcols = [np.roll(D[node], lag) for node, lag in feats]
    for (node, lag), c in zip(feats, Xcols): c[:lag] = np.nan
    X = np.column_stack(Xcols)
    Y = np.full((T, len(HS)), np.nan); cum = np.zeros(T)
    for h in range(1, max(HS) + 1):
        f = np.roll(D[j], -h); f[T - h:] = np.nan; cum = cum + f
        if h in HS: Y[:, HS.index(h)] = cum
    return X, Y


def run_target(D, j, feats, t_end, refit_every):
    """rolling-origin backtest over the last ORIGINS months ending at t_end (the target's last change) + the forecast.
    Rows with any missing feature or horizon are dropped; the origin row needs its features only."""
    X, Yall = design(D, j, feats)
    okX = np.isfinite(X).all(1); okY = np.isfinite(Yall).all(1)
    maes = {k: {h: [] for h in HS} for k in ("nn", "naive", "ridge")}; resid = {h: [] for h in HS}
    cache = None
    for k, o in enumerate(range(t_end - ORIGINS, t_end)):
        if not okX[o]: continue
        rows = np.where(okX[:o + 1] & okY[:o + 1])[0]; rows = rows[rows + max(HS) <= o]
        if len(rows) < 40: continue
        if cache is None or k % refit_every == 0: cache = Fitted(X[rows], Yall[rows])
        nn, rd = cache.predict(X[o])
        for hi, h in enumerate(HS):
            if o + h > t_end or not np.isfinite(Yall[o, hi]): continue
            y = Yall[o, hi]
            maes["nn"][h].append(100 * abs(math.exp(nn[hi]) - math.exp(y)))
            maes["naive"][h].append(100 * abs(1 - math.exp(y)))
            maes["ridge"][h].append(100 * abs(math.exp(rd[hi]) - math.exp(y)))
            resid[h].append(y - nn[hi])
    # forecast from t_end
    rows = np.where(okX[:t_end + 1] & okY[:t_end + 1])[0]
    if not okX[t_end] or len(rows) < 40: return None
    fit = Fitted(X[rows], Yall[rows]); nn, rd = fit.predict(X[t_end])
    imp = permutation_importance(fit.pieces())
    return dict(maes=maes, resid=resid, nn=nn, ridge=rd, importance=imp, n_train=int(len(rows)))


# ----------------------------------------------------------------------------------------------------------------- texts
def fmt_pct(x): return f"{x:+.0f} %" if x is not None else "n/a"


H_EN = {1: "1 month", 2: "2 months", 3: "3 months"}
H_AR = {1: "شهر واحد", 2: "شهرين", 3: "3 أشهر"}


def verdict(skill, best_feat, naive_mae, extra_en="", extra_ar=""):
    def part_en(h, s):
        if s is None: return f"no test at {H_EN[h]}"
        if s > 0.005: return f"beats no-change by {100 * s:.0f} % at {H_EN[h]}"
        return f"ties no-change at {H_EN[h]}" if abs(s) <= 0.005 else f"is worse than no-change at {H_EN[h]} ({100 * s:.0f} %)"
    def part_ar(h, s):
        if s is None: return f"لا اختبار عند {H_AR[h]}"
        if s > 0.005: return f"تتفوق على «لا تغيير» بنسبة {100 * s:.0f}٪ عند {H_AR[h]}"
        return f"تعادل «لا تغيير» عند {H_AR[h]}" if abs(s) <= 0.005 else f"أسوأ من «لا تغيير» عند {H_AR[h]} ({100 * s:.0f}٪)"
    en = "The network " + ", ".join(part_en(h, s) for h, s in zip(HS, skill)) + "."
    ar = "الشبكة " + "، و".join(part_ar(h, s) for h, s in zip(HS, skill)) + "."
    if naive_mae and naive_mae[0] is not None and naive_mae[0] < 0.1:
        en += f" The series is nearly flat (no-change error {naive_mae[0]:.2f} % at 1 month), so percent skill is not meaningful here."
        ar += f" السلسلة شبه ثابتة (خطأ «لا تغيير» {naive_mae[0]:.2f}٪ عند شهر)، فالنسبة المئوية للمهارة غير ذات معنى هنا."
    if best_feat: en += f" Most used input: {best_feat[0]} (lag {best_feat[1]})."; ar += f" أكثر المدخلات استخداماً: {best_feat[0]} (إبطاء {best_feat[1]})."
    return en + extra_en, ar + extra_ar


# ------------------------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True); ap.add_argument("--wb", required=True); ap.add_argument("--ppi", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--refit-every", type=int, default=1); ap.add_argument("--no-cpi", action="store_true")
    a = ap.parse_args(); t_start = time.time(); issues = []
    out_path = Path(a.out); out_path.parent.mkdir(parents=True, exist_ok=True)

    rows, hist, last_full = load_store(a.store)
    comm = commodity_series(rows, hist, a.wb, last_full)
    levels = store_levels(hist, last_full)
    cpi, cpi_names = ({}, None) if a.no_cpi else fetch_gcc_cpi(out_path.parent / "dl", issues)
    ppi, ppi_map = load_ppi(a.ppi)

    # nodes
    nodes = []
    for sid, c in comm.items():
        nodes.append(dict(id=sid, label_en=c["label"], label_ar=LABEL_AR.get(sid, c["label"]), type="commodity", category=c["category"],
                          n_obs=0, source=c["source"], level_log=c["level_log"], wbcol=c["wbcol"]))
    for code in sorted(cpi):
        nodes.append(dict(id="cpi_are_all" if code == "00" else f"cpi_are_{code}", label_en=("UAE CPI, all items" if code == "00" else f"UAE CPI {code}: {cpi_names[code]}"),
                          label_ar=COICOP_AR.get(code, cpi_names[code]), type="cpi", category="CPI division", n_obs=0,
                          source=f"GCC-Stat Marsa SDMX, {GCC_URL} (COICOP {code}, national base); {GCC_CITE}", level_log=cpi[code], wbcol=f"cpi:{code}", code=code))
    for code, p in ppi.items():
        nodes.append(dict(id=f"ppi_{code}", label_en=("Dubai PPI, general index" if code == "X" else f"Dubai PPI {code}: {p['name_en']}"),
                          label_ar=("الرقم القياسي العام لأسعار المنتجين في دبي" if code == "X" else f"{code} {p['name_ar']}"), type="ppi",
                          category="PPI activity", n_obs=0, source="Dubai PPI (DSC), ISIC 4-digit activities and general index, private file; values not published here",
                          level_log=p["level_log"], wbcol=f"ppi:{code}", code=code))
    idx = {n["id"]: i for i, n in enumerate(nodes)}
    t0, t1 = mi(START), mi(last_full)
    D = build_matrix(nodes, t0, t1)
    for i, n in enumerate(nodes):
        n["n_obs"] = int(np.isfinite(D[i]).sum())
        if n["type"] == "commodity" and n["n_obs"] > 0:
            z = float(np.mean(D[i][np.isfinite(D[i])] == 0))
            if z > 0.3: n["source"] += f"; {100 * z:.0f} % of monthly changes are exactly zero (annual or sticky quotes repeated monthly)"
    com_ids = [n["id"] for n in nodes if n["type"] == "commodity"]
    com_rows = np.array([idx[s] for s in com_ids])

    # edges: driver = commodity, target = any node; best lag 0..6; skip pairs that share a World Bank column
    edges = []; best_lag13 = {}  # (driver, target) -> (lag in 1..3, r) on data up to the first backtest origin, for the NN
    for j, tgt in enumerate(nodes):
        tj_end = int(np.where(np.isfinite(D[j]))[0].max()) if np.isfinite(D[j]).any() else -1
        if tj_end < 0: continue
        best = {}; sel_max = tj_end - ORIGINS - 1
        for lag in range(0, MAX_LAG + 1):
            r, n = lag_corr(D, j, lag)
            rs, ns = lag_corr(D, j, lag, tmax=sel_max) if lag >= 1 and lag <= 3 else (None, None)
            for k, i in enumerate(com_rows):
                if i == j or nodes[i]["wbcol"] == tgt["wbcol"]: continue
                if n[i] >= MIN_OVERLAP and np.isfinite(r[i]) and (i not in best or abs(r[i]) > abs(best[i][1])): best[i] = (lag, float(r[i]), int(n[i]))
                if rs is not None and ns[i] >= MIN_OVERLAP and np.isfinite(rs[i]):
                    key = (nodes[i]["id"], tgt["id"])
                    if key not in best_lag13 or abs(rs[i]) > abs(best_lag13[key][1]): best_lag13[key] = (lag, float(rs[i]))
        for i, (lag, r, n) in best.items():
            if abs(r) < R_MIN: continue
            beta = ridge_beta(D, i, j, lag)
            drv = nodes[i]; kind = "driver" if tgt["type"] == "commodity" else "impact"
            prior = None
            if tgt["type"] == "ppi" and tgt["code"] in ppi_map:
                mp = ppi_map[tgt["code"]]
                for ck in (mp.get("c1"), mp.get("c2")):
                    if ck and drv["id"] in PRIOR_KEY.get(ck, []): prior = (f"matches the prototype's input mapping ({mp.get('rawE') or ck})", f"يتفق مع جدول المدخلات في النموذج الأولي ({mp.get('raw') or ck})")
            elif tgt["type"] == "cpi":
                code = tgt["code"]
                if drv["id"] in CPI_PRIOR.get(code, []) or (code in ("01", "11") and drv["category"] in FOOD_CATS):
                    prior = ("consistent with the usual pass-through (energy to fuel and transport, farm prices to food)", "يتفق مع الانتقال السعري المعتاد (الطاقة إلى الوقود والنقل، أسعار المزرعة إلى الغذاء)")
            lead_en = "same month" if lag == 0 else f"{drv['id']} leads by {lag} month{'s' if lag > 1 else ''}"
            lead_ar = "الشهر نفسه" if lag == 0 else f"{drv['id']} يسبق بـ{lag} شهر"
            note_en = f"r = {r:+.2f} at lag {lag} ({lead_en}), n = {n} months to {last_full if tgt['type'] == 'commodity' else ym(t0 + tj_end)}"
            note_ar = f"r = {r:+.2f} عند إبطاء {lag} ({lead_ar})، n = {n} شهراً"
            if beta is not None: note_en += f"; beta = {beta:+.2f} controlling for the target's own lag-1 change"; note_ar += f"؛ بيتا = {beta:+.2f} مع ضبط تغير الهدف السابق"
            if prior: note_en += ". " + prior[0]; note_ar += ". " + prior[1]
            edges.append(dict(**{"from": drv["id"], "to": tgt["id"]}, lag=lag, r=round(r, 3), beta=None if beta is None else round(beta, 3), kind=kind,
                              sign="+" if r > 0 else "-", score=abs(r), note_en=note_en, note_ar=note_ar))
    for kind in ("driver", "impact"):
        mx = max([e["score"] for e in edges if e["kind"] == kind] or [1.0])
        for e in edges:
            if e["kind"] == kind: e["score"] = round(e["score"] / mx, 3)

    # the network model per target
    nn_out = {}; done_by_col = {}
    targets = [n for n in nodes if (n["type"] == "commodity" and n["n_obs"] >= 120) or n["type"] == "cpi" or n["id"] == "ppi_X"]
    for tgt in targets:
        j = idx[tgt["id"]]
        if tgt["wbcol"] in done_by_col:  # identical World Bank history (differs only by the quote currency): reuse the fit
            src = done_by_col[tgt["wbcol"]]; base = nn_out[src]
            res = dict(base); res["forecast"] = forecast_levels(base["_pred"], base["_resid"], tgt, levels, last_full, t0, D, j)
            res["verdict_en"] = base["verdict_en"] + f" Shares the World Bank history of {src}; the store series differ only by quote currency."
            res["verdict_ar"] = base["verdict_ar"] + f" يشترك في تاريخ البنك الدولي مع {src}؛ تختلف سلاسل المخزن بعملة التسعير فقط."
            nn_out[tgt["id"]] = res; continue
        cands = sorted(((-abs(v[1]), idx[d], v[0], d) for (d, t), v in best_lag13.items() if t == tgt["id"]))
        drivers = []; used_cols = set()
        for _, _, lag, d in cands:
            col = nodes[idx[d]]["wbcol"]
            if col in used_cols: continue  # one of each identical history
            used_cols.add(col); drivers.append((d, lag))
            if len(drivers) == 6: break
        feats = [(j, l) for l in (1, 2, 3)] + [(idx[d], l) for d, l in drivers]
        fin = np.where(np.isfinite(D[j]))[0]
        t_end = int(fin.max())
        res = run_target(D, j, feats, t_end, a.refit_every)
        if res is None: issues.append(f"{tgt['id']}: too few complete rows for the network model"); continue
        maes = {k: [float(np.mean(res["maes"][k][h])) if res["maes"][k][h] else None for h in HS] for k in ("nn", "naive", "ridge")}
        skill = [None if (maes["nn"][i] is None or not maes["naive"][i]) else round(1 - maes["nn"][i] / maes["naive"][i], 3) for i in range(len(HS))]
        feat_names = [(tgt["id"], l) for l in (1, 2, 3)] + drivers
        imp = sorted([dict(node=n, lag=l, score=round(s, 3)) for (n, l), s in zip(feat_names, res["importance"])], key=lambda x: -x["score"])
        best_feat = (imp[0]["node"], imp[0]["lag"]) if imp else None
        extra_en = extra_ar = ""
        if tgt["type"] != "commodity":
            extra_en = f" Series ends {ym(t0 + t_end)}; the forecast runs from there."; extra_ar = f" تنتهي السلسلة في {ym(t0 + t_end)}؛ التوقع يبدأ منها."
        ven, var = verdict(skill, best_feat, maes["naive"], extra_en, extra_ar)
        fmap = {}
        for n, l in feat_names: fmap.setdefault(n, []).append(l)
        entry = dict(features=[dict(node=n, lags=ls) for n, ls in fmap.items()], h=list(HS),
                     backtest=dict(origins=ORIGINS, nn_mae_pct=[None if v is None else round(v, 3) for v in maes["nn"]],
                                   naive_mae_pct=[None if v is None else round(v, 3) for v in maes["naive"]],
                                   ridge_mae_pct=[None if v is None else round(v, 3) for v in maes["ridge"]], skill_vs_naive=skill),
                     forecast=forecast_levels(res["nn"], res["resid"], tgt, levels, last_full, t0, D, j), importance=imp, verdict_en=ven, verdict_ar=var,
                     _pred=res["nn"], _resid=res["resid"])
        nn_out[tgt["id"]] = entry; done_by_col[tgt["wbcol"]] = tgt["id"]
        print(f"{tgt['id']:<16} skill {skill}  nn {['%.2f' % v if v else '-' for v in maes['nn']]} naive {['%.2f' % v if v else '-' for v in maes['naive']]} "
              f"{time.time() - t_start:6.0f}s", file=sys.stderr)
    for e in nn_out.values(): e.pop("_pred", None); e.pop("_resid", None)

    # examples: wheat, brent, gold + the two best mean skills among the rest
    def mean_skill(sid):
        s = [v for v in nn_out[sid]["backtest"]["skill_vs_naive"] if v is not None]; return sum(s) / len(s) if s else -9
    rest = sorted((sid for sid in nn_out if sid not in ("wheat", "brent", "gold")), key=mean_skill, reverse=True)
    examples = [s for s in ("wheat", "brent", "gold") if s in nn_out] + rest[:2]

    n_cpi = sum(1 for n in nodes if n["type"] == "cpi"); n_ppi = sum(1 for n in nodes if n["type"] == "ppi")
    note_en = (f"Monthly log changes {START}..{last_full}. Commodity history: World Bank Pink Sheet columns mapped in build_history_store.MAP "
               f"(EIA series use their WB equivalent; gasoline, heating oil and propane have none and carry only the store's 2024+ months, so they have no edges "
               f"and no model). Levels and forecast origin: the TrendX store, 2024 = 100, real observations only, {last_full} = last full month. "
               f"{n_cpi} UAE CPI nodes (GCC-Stat Marsa SDMX, national base, to {ym(t0 + int(np.where(np.isfinite(D[idx['cpi_are_all']]))[0].max())) if 'cpi_are_all' in idx else 'n/a'}), "
               f"{n_ppi} Dubai PPI nodes (general index and ISIC 4-digit activities, private source). Edges: best of lags 0..6 by |Pearson r| over >= {MIN_OVERLAP} common months, kept when |r| >= {R_MIN}; "
               f"beta from a ridge regression controlling for the target's own lag-1 change; score = |r| / max |r| within kind. Pairs that share one World Bank column "
               f"(eu_gas/german_gas/uk_gas, iron_ore/iron_ore_cny) are not linked to each other. With 7 lags tried per pair, an |r| near 0.25 on 90-130 months can arise by chance; "
               f"correlation is not causation. Network model: MLP ({HIDDEN} tanh units, Adam, L2 {WD}, early stopping on the last 15 % of the training rows, {SEEDS}-seed mean) on the "
               f"target's own lags 1-3 and the best lag (1-3, chosen on data before the first backtest origin) of its top-6 drivers, predicting the 1-, 2- and 3-month cumulative log change; "
               f"training from {START}; {ORIGINS} rolling origins refit every {a.refit_every} origin(s); MAE in percent of the origin level against naive (no change) and ridge on the same features; "
               f"80 % band from the backtest residual quantiles (24 residuals: rough). Forecast changes come from the USD history; for FX-converted store series the level is the store's quote currency."
               + (" Issues: " + "; ".join(issues) if issues else ""))
    note_ar = (f"تغيرات لوغاريتمية شهرية {START}..{last_full}. تاريخ السلع من أعمدة البنك الدولي (Pink Sheet) وفق جدول MAP في build_history_store "
               f"(سلاسل EIA تستخدم مكافئها في البنك الدولي؛ البنزين وزيت التدفئة والبروبان بلا عمود فلا روابط ولا نموذج لها). المستوى ونقطة انطلاق التوقع من مخزن TrendX "
               f"(2024 = 100، مشاهدات حقيقية فقط، آخر شهر كامل {last_full}). {n_cpi} عقدة لمؤشر أسعار المستهلك الإماراتي (GCC-Stat SDMX، أساس وطني) و{n_ppi} عقدة لمؤشر أسعار المنتجين في دبي "
               f"(الرقم العام والأنشطة رباعية الرقم، مصدر خاص). الروابط: أفضل إبطاء 0..6 بقيمة |r| على {MIN_OVERLAP} شهراً مشتركاً على الأقل، تُحفظ عند |r| ≥ {R_MIN}؛ بيتا من انحدار ridge مع ضبط تغير الهدف السابق؛ "
               f"الدرجة = |r| / أقصى |r| ضمن النوع. الأزواج التي تتشارك عموداً واحداً في البنك الدولي لا تُربط ببعضها. مع 7 إبطاءات لكل زوج قد تظهر |r| قرب 0.25 صدفةً على 90–130 شهراً؛ الارتباط ليس سببية. "
               f"النموذج: شبكة عصبية بطبقة مخفية ({HIDDEN} وحدة tanh، Adam، تنظيم L2، إيقاف مبكر على آخر 15٪ من صفوف التدريب، متوسط {SEEDS} بذور) على إبطاءات الهدف 1–3 وأفضل إبطاء (1–3) لأقوى 6 محركات، "
               f"تتنبأ بالتغير التراكمي لشهر وشهرين وثلاثة؛ التدريب من {START}؛ {ORIGINS} نقطة انطلاق متحركة مع إعادة التدريب كل {a.refit_every} نقطة؛ الخطأ المطلق المتوسط كنسبة من مستوى الانطلاق مقابل «لا تغيير» وانحدار ridge على المدخلات نفسها؛ "
               f"نطاق 80٪ من مئينات بواقي الاختبار (24 باقياً: تقريبي)."
               + (" ملاحظات: " + "; ".join(issues) if issues else ""))

    out = dict(built=date.today().isoformat(), window=dict(**{"from": START, "to": last_full}), method_note_en=note_en, method_note_ar=note_ar,
               nodes=[{k: n[k] for k in ("id", "label_en", "label_ar", "type", "category", "n_obs", "source")} for n in nodes],
               edges=edges, nn=nn_out, examples=examples)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    rt = time.time() - t_start
    print(f"wrote {out_path}: {len(nodes)} nodes ({len(com_ids)} commodity, {n_cpi} cpi, {n_ppi} ppi), {len(edges)} edges "
          f"({sum(e['kind'] == 'driver' for e in edges)} driver, {sum(e['kind'] == 'impact' for e in edges)} impact), {len(nn_out)} models, {rt:.0f} s", file=sys.stderr)
    for i in issues: print("ISSUE:", i, file=sys.stderr)


def forecast_levels(pred, resid, tgt, levels, last_full, t0, D, j):
    """levels 2024 = 100 for the next 3 months from the target's last real month, with an 80 % band from the backtest residuals."""
    t_end = int(np.where(np.isfinite(D[j]))[0].max()); origin = ym(t0 + t_end)
    if tgt["type"] == "commodity":
        if tgt["id"] in levels and levels[tgt["id"]][0] == origin: lvl = levels[tgt["id"]][1]
        else: return []
    else:  # CPI / PPI: rebase the series itself to its 2024 mean = 100
        lv = tgt["level_log"]; base = [math.exp(v) for k, v in lv.items() if mi("2024-01") <= k <= mi("2024-12")]
        if len(base) < 12: return []
        lvl = math.exp(lv[t0 + t_end]) / (sum(base) / len(base)) * 100
    out = []
    for hi, h in enumerate(HS):
        r = np.array(resid[h]) if resid[h] else np.array([0.0])
        q10, q90 = (float(np.quantile(r, 0.1)), float(np.quantile(r, 0.9))) if len(r) >= 5 else (float("nan"), float("nan"))
        m = lvl * math.exp(pred[hi])
        out.append(dict(period=ym(t0 + t_end + h), mean=round(m, 2), lo80=None if math.isnan(q10) else round(lvl * math.exp(pred[hi] + q10), 2),
                        hi80=None if math.isnan(q90) else round(lvl * math.exp(pred[hi] + q90), 2)))
    return out


if __name__ == "__main__":
    main()
