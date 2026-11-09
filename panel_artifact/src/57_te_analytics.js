// ============================================================ TrendX analytics engine
// Ports the methods of the Dubai PPI analysis prototype (PPI Analysis Platform, POC v2: quarterly contributions, diffusion,
// lag correlation, seven forecasting models with an accuracy-weighted combination, bottom-up aggregation) onto the TrendX monthly
// store (mean of 2024 = 100, scripts/trendx/build_history_store.py). Everything runs in the browser from the store. Carried-back
// series (obs_status E) are never modelled. The Dubai PPI itself is read from an uploaded asset (projects/te/ppi/latest) when
// present, so global prices can be linked to our own numbers with the prototype's own mapping table.
const pct = (a, b) => (a != null && b != null && b !== 0 && isFinite(a) && isFinite(b) ? (a / b) * 100 - 100 : null);
const meanA = (a) => (a.length ? a.reduce((s, x) => s + x, 0) / a.length : null);
const qOf = (ym) => `${ym.slice(0, 4)}Q${Math.ceil(+ym.slice(5, 7) / 3)}`;
const qMonths = (k) => { const y = k.slice(0, 4), q = +k.slice(5); return [1, 2, 3].map((i) => `${y}-${String((q - 1) * 3 + i).padStart(2, "0")}`); };
const qPrev = (k) => { let y = +k.slice(0, 4), q = +k.slice(5) - 1; if (q < 1) { q = 4; y--; } return `${y}Q${q}`; };
const qLY = (k) => `${+k.slice(0, 4) - 1}Q${k.slice(5)}`;
const qLabel = (k) => L(`Q${k.slice(5)} ${k.slice(0, 4)}`, `الربع ${["", "الأول", "الثاني", "الثالث", "الرابع"][+k.slice(5)]} ${k.slice(0, 4)}`);
const ymAdd = (ym, h) => { let y = +ym.slice(0, 4), m = +ym.slice(5, 7) + h; while (m > 12) { m -= 12; y++; } while (m < 1) { m += 12; y--; } return `${y}-${String(m).padStart(2, "0")}`; };
const sg = (x, d = 2) => (x == null || !isFinite(x) ? "—" : `${x > 0 ? "+" : x < 0 ? "−" : ""}${fmtN(Math.abs(x), d)}`);
const dirOf = (x) => (x == null ? "" : x > 1 ? "u" : x < -1 ? "d" : "s");
const DIRS = { u: ["Rising", "صاعد"], d: ["Falling", "هابط"], s: ["Stable", "مستقر"] };
const dirTag = (d) => (d ? chip(L(DIRS[d][0], DIRS[d][1]), d === "u" ? "bad" : d === "d" ? "ok" : "grey") : "—");
const isUp = (x) => x >= 0;
const vUp = (x) => (isUp(x) ? L("rose", "ارتفع") : L("fell", "تراجع"));
const wUp = (x) => (isUp(x) ? L("rise", "ارتفاع") : L("fall", "تراجع"));
const ppu = () => L("pp", "نقطة مئوية");
const clsOf = (x) => (x == null ? "" : x > 0.005 ? "chg-up" : x < -0.005 ? "chg-dn" : "");
const pctCell = (x, d = 1) => `<span class="${clsOf(x)}">${x == null ? "—" : sg(x, d) + "%"}</span>`;

// ---------------- the model: monthly levels (2024 = 100) for every series, the index, category aggregates, quarters
let teA = null;
async function teModel() {
  if (teA) return teA;
  const h = await teHistoryLoad(); if (!h) return null;
  const M = h.index.map((r) => r.period), at = Object.fromEntries(M.map((m, i) => [m, i]));
  const ser = h.series.map((s) => { const v = M.map(() => null); for (const o of h.obs[s.series_id] || []) if (!o[4] && o[2] != null && at[o[0]] != null) v[at[o[0]]] = +o[2]; return { ...s, v, real: s.base_method === "actual", inIdx: !!+s.in_index }; });
  const num = (x) => (x === "" || x == null ? null : +x);
  const X = h.index.map((r) => num(r.trendx_2024eq100_actual_history)), XA = h.index.map((r) => num(r.trendx_2024eq100_all_series));
  const last = M.length - 1, partial = M[last] >= todayDubai().slice(0, 7);
  const quarters = [...new Set(M.map(qOf))], full = (k) => qMonths(k).every((m) => at[m] != null) && !(partial && qMonths(k).includes(M[last]));
  const act = ser.filter((s) => s.real && s.inIdx);
  const gmean = (members) => M.map((_, i) => { const l = members.map((s) => s.v[i]).filter((x) => x > 0).map(Math.log); return l.length ? Math.exp(meanA(l)) : null; });
  const cat = {}; for (const c of TE_CATS) { const mem = act.filter((s) => s.category === c); if (mem.length) cat[c] = { members: mem, v: gmean(mem) }; }
  teA = { h, M, at, ser, act, X, XA, last, partial, quarters, fullQ: quarters.filter(full), cat, fc: {} };
  return teA;
}
const teSid = (A, id) => (id === "__index" ? { series_id: "__index", commodity: L("TrendX index", "مؤشر TrendX"), category: "All", unit: "2024 = 100", v: A.X, real: true, inIdx: true } : id.startsWith("cat:") ? { series_id: id, commodity: teCatName(id.slice(4)), category: id.slice(4), unit: "2024 = 100", v: A.cat[id.slice(4)]?.v || [], real: true, inIdx: true } : A.ser.find((s) => s.series_id === id));
const qAvgV = (A, v, k) => { const ms = qMonths(k).map((m) => A.at[m]); if (ms.some((i) => i == null)) return null; const a = ms.map((i) => v[i]); return a.every((x) => x != null) ? meanA(a) : null; };
// contribution of a member to the change of an equal-weight geometric aggregate, in percentage points of that aggregate's change
function teContrib(A, mem, agg, k, ref) {
  const a = qAvgV(A, mem.v, k), b = qAvgV(A, mem.v, ref), A1 = qAvgV(A, agg.v, k), A0 = qAvgV(A, agg.v, ref), n = agg.members.length;
  if (!(a > 0 && b > 0 && A1 > 0 && A0 > 0)) return null;
  const tot = Math.log(A1 / A0); if (Math.abs(tot) < 1e-9) return 0;
  return (Math.log(a / b) / n) / tot * pct(A1, A0);      // log shares, scaled so that members sum to the aggregate's % change
}
function teQuarterRow(A, s, k, agg) {
  const a = qAvgV(A, s.v, k), p = qAvgV(A, s.v, qPrev(k)), y = qAvgV(A, s.v, qLY(k));
  return { s, cur: a, prev: p, ly: y, qq: pct(a, p), yy: pct(a, y), cq: agg ? teContrib(A, s, agg, k, qPrev(k)) : null, cy: agg ? teContrib(A, s, agg, k, qLY(k)) : null };
}
const teIdxAgg = (A) => ({ members: A.act, v: A.X });

// ---------------- forecasting (the prototype's seven models, tuned and combined by out-of-sample accuracy)
const TE_METHODS = [["naive", "Persistence", "الاستمرارية"], ["snaive", "Seasonal persistence", "الاستمرارية الموسمية"], ["ma3", "Moving average (3 months)", "المتوسط المتحرك (3 أشهر)"], ["ses", "Simple exponential smoothing", "التمهيد الأسي البسيط"],
  ["holt", "Holt linear smoothing", "تمهيد هولت الخطي"], ["trend", "Linear trend", "الاتجاه الخطي"], ["arx", "Regression on global prices", "الانحدار على الأسعار العالمية"]];
const teMName = (m) => { const x = TE_METHODS.find((y) => y[0] === m); return x ? L(x[1], x[2]) : "—"; };
function ols(x, y) { const n = x.length, mx = meanA(x), my = meanA(y); let sxy = 0, sxx = 0, syy = 0; for (let i = 0; i < n; i++) { sxy += (x[i] - mx) * (y[i] - my); sxx += (x[i] - mx) ** 2; syy += (y[i] - my) ** 2; } const b = sxx ? sxy / sxx : 0; return { a: my - b * mx, b, r2: sxx && syy ? (sxy * sxy) / (sxx * syy) : 0, n }; }
function pearson(a, b) { const x = [], y = []; for (let i = 0; i < a.length; i++) if (a[i] != null && b[i] != null) { x.push(a[i]); y.push(b[i]); } if (x.length < 6) return null; const mx = meanA(x), my = meanA(y); let sxy = 0, sx = 0, sy = 0; for (let i = 0; i < x.length; i++) { sxy += (x[i] - mx) * (y[i] - my); sx += (x[i] - mx) ** 2; sy += (y[i] - my) ** 2; } return sx && sy ? sxy / Math.sqrt(sx * sy) : null; }
const sesFit = (y, a) => { let l = y[0]; for (let i = 1; i < y.length; i++) l = a * y[i] + (1 - a) * l; return l; };
const holtFit = (y, a, b) => { let l = y[0], t = y[1] - y[0]; for (let i = 1; i < y.length; i++) { const pl = l; l = a * y[i] + (1 - a) * (l + t); t = b * (l - pl) + (1 - b) * t; } return { l, t }; };
function tune(y, fn, grid) { let best = null; for (const p of grid) { let sse = 0; for (let o = Math.max(12, y.length - 24); o < y.length; o++) { const f = fn(y.slice(0, o), p); sse += (y[o] - f) ** 2; } if (best == null || sse < best.sse) best = { p, sse }; } return best.p; }
const AG = [0.2, 0.35, 0.5, 0.65, 0.8, 0.95], HG = []; AG.forEach((a) => [0.1, 0.3, 0.5].forEach((b) => HG.push([a, b])));
const chgSeries = (v) => v.map((x, i) => (i ? pct(x, v[i - 1]) : null));
const TE_MIN_N = 30;
// v: monthly levels on a month axis (nulls allowed before the history starts); last: index of the origin; H: horizon
// reg (optional): { x: regressor levels on the same axis (may run past `last`), lag, future: (absIdx) => {v: % change, actual} }
function teForecast(v, last, H, reg, cacheKey) {
  const A = teA; if (cacheKey && A?.fc[cacheKey]) return A.fc[cacheKey];
  const first = v.findIndex((x) => x != null), start = Math.max(first < 0 ? 0 : first, last - 71), y = v.slice(start, last + 1), n = y.length, off = start;
  const res = { methods: {}, H, last: y[n - 1], n, start, origin: last };
  if (y.some((x) => x == null) || n < TE_MIN_N) { res.short = true; if (cacheKey) A.fc[cacheKey] = res; return res; }
  const aS = tune(y.slice(0, n - 12), (h, a) => sesFit(h, a), AG), pH = tune(y.slice(0, n - 12), (h, p) => { const s = holtFit(h, p[0], p[1]); return s.l + s.t; }, HG);
  let lag = 0, arxOk = false;
  if (reg) { lag = reg.lag || 0; arxOk = true; }
  const cch = (i) => { if (!reg) return null; const j = i - lag; return j >= 1 && j < reg.x.length ? pct(reg.x[j], reg.x[j - 1]) : null; };
  const arxFit = (endAbs) => { const xs = [], ys = []; for (let i = off + 1; i <= endAbs; i++) { const a = pct(v[i], v[i - 1]), c = cch(i); if (a != null && c != null) { xs.push(c); ys.push(a); } } return xs.length >= 12 ? ols(xs, ys) : null; };
  const one = {
    naive: (h) => h[h.length - 1],
    snaive: (h) => (h.length > 13 ? (h[h.length - 1] * h[h.length - 12]) / h[h.length - 13] : null),
    ma3: (h) => meanA(h.slice(-3)),
    ses: (h) => sesFit(h, aS),
    holt: (h) => { const s = holtFit(h, pH[0], pH[1]); return s.l + s.t; },
    trend: (h) => { const w = h.slice(-12); return h[h.length - 1] + ols(w.map((_, i) => i), w).b; },
    arx: (h, abs) => { if (!arxOk) return null; const f = arxFit(abs - 1), c = cch(abs); return f && c != null ? h[h.length - 1] * (1 + (f.a + f.b * c) / 100) : null; },
  };
  for (const [m] of TE_METHODS) { const errs = []; for (let o = n - 12; o < n; o++) { const f = one[m](y.slice(0, o), off + o); if (f != null) errs.push(((y[o] - f) / y[o]) * 100); }
    res.methods[m] = { mape: errs.length >= 6 ? meanA(errs.map(Math.abs)) : null, sd: errs.length >= 6 ? Math.sqrt(meanA(errs.map((e) => e * e))) : null, f: [] }; }
  const hS = sesFit(y, aS), hH = holtFit(y, pH[0], pH[1]), w12 = y.slice(-12), sl = ols(w12.map((_, i) => i), w12).b, fit = arxOk ? arxFit(last) : null;
  res.arx = fit ? { ...fit, lag, used: [] } : null;
  let px = y[n - 1];
  for (let h = 1; h <= H; h++) {
    res.methods.naive.f.push(y[n - 1]);
    res.methods.snaive.f.push(n > 13 && n - 13 + h < n ? (y[n - 1] * y[n - 13 + h]) / y[n - 13] : null);
    res.methods.ma3.f.push(meanA(y.slice(-3)));
    res.methods.ses.f.push(hS); res.methods.holt.f.push(hH.l + h * hH.t); res.methods.trend.f.push(y[n - 1] + h * sl);
    if (fit) { const j = last + h - lag, c = cch(last + h), cf = c != null ? { v: c, actual: true } : reg.future ? reg.future(j) : { v: 0, actual: false }; res.arx.used.push(cf); px = px * (1 + (fit.a + fit.b * cf.v) / 100); res.methods.arx.f.push(px); } else res.methods.arx.f.push(null);
  }
  const ok = TE_METHODS.map((m) => m[0]).filter((m) => res.methods[m].mape != null && res.methods[m].f[0] != null);
  res.best = ok.slice().sort((a, b) => res.methods[a].mape - res.methods[b].mape)[0] || null;
  res.ens = []; for (let h = 0; h < H; h++) { let sw = 0, sf = 0; for (const m of ok) { if (res.methods[m].f[h] == null) continue; const w = 1 / (res.methods[m].mape + 0.05); sw += w; sf += w * res.methods[m].f[h]; } res.ens.push(sw ? sf / sw : null); }
  const s0 = res.best ? res.methods[res.best].sd : null;
  res.lo = res.ens.map((f, h) => (f != null && s0 != null ? f * (1 - (1.2816 * s0 / 100) * Math.sqrt(h + 1)) : null));
  res.hi = res.ens.map((f, h) => (f != null && s0 != null ? f * (1 + (1.2816 * s0 / 100) * Math.sqrt(h + 1)) : null));
  res.mape = res.best ? res.methods[res.best].mape : null;
  if (cacheKey) A.fc[cacheKey] = res;
  return res;
}
const teFcOf = (A, id, H) => { const s = teSid(A, id); return s ? teForecast(s.v, A.last, H, null, `${id}|${H}`) : null; };
const teFutureMonths = (A, H, from = A.last) => Array.from({ length: H }, (_, h) => ymAdd(A.M[from], h + 1));
function teTrendClass(A, s) {
  const i = A.last, v = s.v, f = teFcOf(A, s.series_id, 3), fc = f?.ens && f.ens[2] != null ? pct(f.ens[2], v[i]) : null;
  return { m1: pct(v[i], v[i - 1]), m3: pct(v[i], v[i - 3]), m12: pct(v[i], v[i - 12]), fc, now: dirOf(pct(v[i], v[i - 3])), next: dirOf(fc), best: f?.best || null, mape: f?.mape ?? null, short: !!f?.short };
}
// bottom-up: an equal-weight geometric aggregate of member forecasts (the index and the categories are built that way)
function teBottomUp(A, members, H) { const fs = members.map((s) => teFcOf(A, s.series_id, H)); return Array.from({ length: H }, (_, h) => { const l = fs.map((f, i) => (f?.ens && f.ens[h] > 0 ? Math.log(f.ens[h]) : members[i].v[A.last] > 0 ? Math.log(members[i].v[A.last]) : null)).filter((x) => x != null); return l.length ? Math.exp(meanA(l)) : null; }); }
// lag correlation between the monthly % changes of a (target) and b (driver), b shifted back by 0..maxLag months, over the last n months ending at `end`
function teBestLag(a, b, end, n = 30, maxLag = 6) {
  const ca = chgSeries(a), cb = chgSeries(b), prof = []; let best = { lag: 0, r: null };
  for (let l = 0; l <= maxLag; l++) { const xs = [], ys = []; for (let i = Math.max(1, end - n + 1); i <= end; i++) { xs.push(ca[i]); ys.push(i - l >= 1 ? cb[i - l] : null); } const r = pearson(xs, ys); prof.push(r); if (r != null && (best.r == null || Math.abs(r) > Math.abs(best.r))) best = { lag: l, r }; }
  return { ...best, prof };
}
const corrReading = (r, lag) => (r == null ? L("Insufficient data", "بيانات غير كافية") : Math.abs(r) < 0.3 ? L("Weak correlation", "ارتباط ضعيف") : lag === 0 ? L("Same-month pass-through", "انتقال في الشهر نفسه") : L(`Passes through after ${lag} month${lag > 1 ? "s" : ""}`, `ينتقل بعد ${lag} ${lag === 1 ? "شهر" : lag === 2 ? "شهرين" : "أشهر"}`));

// ---------------- narrative (publication-safe wording: commodities and categories only)
function teReason(A, s, k, kind, agg) {
  const r = teQuarterRow(A, s, k, agg), c = kind === "Q" ? r.qq : r.yy, ref = kind === "Q" ? qPrev(k) : qLY(k), rl = qLabel(ref), ql = qLabel(k);
  if (c == null) return L("Not enough history for this comparison.", "لا يكفي التاريخ لهذه المقارنة.");
  const subj = s.series_id === "__index" ? L("The TrendX index", "مؤشر TrendX") : s.series_id.startsWith("cat:") ? L(`The ${teCatName(s.category)} aggregate`, `مجمّع ${teCatName(s.category)}`) : L(`${s.commodity}`, `${s.commodity}`);
  if (Math.abs(c) < 0.05) return L(`${subj} was broadly unchanged in ${ql} compared with ${rl}.`, `استقر ${subj} خلال ${ql} مقارنة بـ${rl} دون تغير يُذكر.`);
  let t = L(`${subj} ${vUp(c)} by ${fmtN(Math.abs(c), 1)}% in ${ql} compared with ${rl} (quarterly averages, 2024 = 100)`, `${vUp(c)} ${subj} بنسبة ${fmtN(Math.abs(c), 1)}% خلال ${ql} مقارنة بـ${rl} (متوسطات ربعية، 2024 = 100)`);
  if (kind === "Q") { const ms = qMonths(k).map((m) => A.at[m]); let bi = -1, bv = 0; for (const i of ms) { const m = i != null ? pct(s.v[i], s.v[i - 1]) : null; if (m != null && isUp(m) === isUp(c) && Math.abs(m) > bv) { bv = Math.abs(m); bi = i; } }
    if (bi >= 0 && bv >= 1) t += L(`, with the largest monthly move in ${fmtMonth(A.M[bi])} (${sg(pct(s.v[bi], s.v[bi - 1]), 1)}%)`, `، وتركزت أبرز الحركة الشهرية في ${fmtMonth(A.M[bi])} (${sg(pct(s.v[bi], s.v[bi - 1]), 1)}%)`); }
  if (r.cq != null && agg && s.series_id !== "__index") t += L(`; its contribution to the ${kind === "Q" ? "quarterly" : "annual"} change of the index is ${sg(kind === "Q" ? r.cq : r.cy)} ${ppu()}`, `؛ ومساهمته في التغير ${kind === "Q" ? "الربعي" : "السنوي"} للمؤشر ${sg(kind === "Q" ? r.cq : r.cy)} ${ppu()}`);
  if (s.proxy && +s.proxy) t += L(" (history through a proxy series)", " (التاريخ عبر سلسلة بديلة)");
  return t + ".";
}
function teInsights(A, k, H) {
  const agg = teIdxAgg(A), X = teQuarterRow(A, teSid(A, "__index"), k), rows = A.act.map((s) => teQuarterRow(A, s, k, agg)).filter((r) => r.cq != null), out = [];
  if (X.qq == null) return [L("The selected quarter is not complete in the store.", "الربع المختار غير مكتمل في المستودع.")];
  out.push(L(`<b>The TrendX index ${vUp(X.qq)} by ${fmtN(Math.abs(X.qq), 1)}%</b> in ${qLabel(k)} compared with ${qLabel(qPrev(k))}${X.yy != null ? `, and ${vUp(X.yy)} by ${fmtN(Math.abs(X.yy), 1)}% year on year` : ""}.`,
    `<b>${vUp(X.qq)} مؤشر TrendX بنسبة ${fmtN(Math.abs(X.qq), 1)}%</b> خلال ${qLabel(k)} مقارنة بـ${qLabel(qPrev(k))}${X.yy != null ? `، وبنسبة ${fmtN(Math.abs(X.yy), 1)}% ${isUp(X.yy) ? "ارتفاعاً" : "تراجعاً"} على أساس سنوي` : ""}.`));
  const by = rows.slice().sort((a, b) => Math.abs(b.cq) - Math.abs(a.cq)), same = by.find((r) => isUp(r.cq) === isUp(X.qq)), opp = by.find((r) => isUp(r.cq) !== isUp(X.qq));
  if (same) out.push(L(`<b>${esc(same.s.commodity)}</b> was the largest contributor to the quarterly change at ${sg(same.cq)} ${ppu()} (its own change ${sg(same.qq, 1)}%).`, `<b>${esc(same.s.commodity)}</b> هو المساهم الأكبر في التغير الربعي بمقدار ${sg(same.cq)} ${ppu()} (تغيره ${sg(same.qq, 1)}%).`));
  if (opp && Math.abs(opp.cq) >= 0.1) out.push(L(`By contrast, <b>${esc(opp.s.commodity)}</b> partly offset the ${wUp(X.qq)} with ${sg(opp.cq)} ${ppu()}.`, `في المقابل حدّ <b>${esc(opp.s.commodity)}</b> من ${isUp(X.qq) ? "الارتفاع" : "التراجع"} بمساهمة ${sg(opp.cq)} ${ppu()}.`));
  const up = rows.filter((r) => r.qq > 0.05);
  out.push(L(`Breadth: prices rose in <b>${up.length} of ${rows.length}</b> commodities with real history (equal weights).`, `اتساع الحركة: ارتفعت أسعار <b>${up.length} من ${rows.length}</b> سلعة لها تاريخ حقيقي (أوزان متساوية).`));
  const cats = Object.entries(A.cat).map(([c, g]) => ({ c, r: teQuarterRow(A, { ...teSid(A, "cat:" + c) }, k) })).filter((x) => x.r.qq != null).sort((a, b) => Math.abs(b.r.qq) - Math.abs(a.r.qq))[0];
  if (cats) out.push(L(`Among categories, <b>${teCatName(cats.c)}</b> moved most: ${sg(cats.r.qq, 1)}% q/q.`, `بين الفئات سجّلت <b>${teCatName(cats.c)}</b> أكبر حركة: ${sg(cats.r.qq, 1)}% ربعياً.`));
  const f = teFcOf(A, "__index", H), fm = teFutureMonths(A, H);
  if (f?.ens && f.ens[2] != null) out.push(L(`Analytical outlook: the index is projected at about <b>${fmtN(f.ens[2], 1)}</b> in ${fmtMonth(fm[2])} (${sg(pct(f.ens[2], A.X[A.last]), 1)}% versus ${fmtMonth(A.M[A.last])}${A.partial ? ", a partial month" : ""}); best model ${teMName(f.best)}, MAPE ${fmtN(f.mape, 2)}%.`,
    `التقدير التحليلي: يُتوقع أن يبلغ المؤشر نحو <b>${fmtN(f.ens[2], 1)}</b> في ${fmtMonth(fm[2])} (${sg(pct(f.ens[2], A.X[A.last]), 1)}% عن ${fmtMonth(A.M[A.last])}${A.partial ? "، شهر جزئي" : ""})؛ أدق نموذج ${teMName(f.best)}، خطأ ${fmtN(f.mape, 2)}%.`));
  return out;
}

// ---------------- the Dubai PPI (the prototype's data, uploaded as an asset; pointer projects/te/ppi/latest)
// Mapping from the prototype's commodity keys to TrendX series (first candidate with real history wins; carried-back never used)
const PPI_KEY2SID = { DUBAI: ["urals_oil", "brent"], BRENT: ["brent"], NGAS: ["eu_gas"], GOLD: ["gold"], ALUM: ["aluminum"], COPP: ["copper"], NICK: ["nickel"], IRON: ["iron_ore"], STEEL: ["hrc_steel", "steel"], PLAST: ["polyethylene", "polypropylene"], CHEM: ["methanol", "styrene"], CEMENT: ["bitumen"], FERT: ["urea", "di-ammonium"], PULP: ["kraft_pulp"], WHEAT: ["wheat"], BARLEY: ["barley"], SUGAR: ["sugar"], PALM: ["palm_oil"], SOY: ["soybeans"], SUNF: ["sunflower_oil"], POULT: ["poultry"], BEEF: ["beef"], COCOA: ["cocoa"], ALLC: ["__index"] };
let tePpi = undefined;
async function tePpiLoad() {
  if (tePpi !== undefined) return tePpi;
  try {
    const ptr = await getDocStrict("projects/te/ppi/latest"); if (!ptr?.asset) { tePpi = null; return null; }
    const r = await fetch("/_blob/" + ptr.asset); if (!r.ok) throw new Error("PPI file HTTP " + r.status);
    const d = await r.json(); const at = Object.fromEntries(d.months.map((m, i) => [m, i]));
    const S = Object.fromEntries(d.series.map((s) => [s.c, s])), lvEN = d.meta?.lvEN || {};
    const L4 = d.series.filter((s) => s.lv === "حد رابع").map((s) => s.c), last = Math.max(...d.series.filter((s) => s.c === "X").map((s) => s.v.length - 1 - [...s.v].reverse().findIndex((x) => x != null)));
    tePpi = { ptr, ...d, at, S, L4, last, iLink: at[d.meta?.link] ?? -1, lvEN, name: (c) => (LANG === "ar" ? S[c]?.n : S[c]?.e) || c, lvName: (lv) => (LANG === "ar" ? lv : lvEN[lv] || lv) };
  } catch (e) { tePpi = { error: e?.message || String(e) }; }
  return tePpi;
}
// align a TrendX series onto the PPI month axis (null where our store has no month)
const teOnPpi = (A, P, v) => P.months.map((m) => (A.at[m] != null ? v[A.at[m]] : null));
function tePpiDriver(A, P, code) {
  const mp = P.map?.[code] || {}; for (const key of [mp.c1, mp.c2]) { if (!key) continue; for (const sid of PPI_KEY2SID[key] || []) { const s = teSid(A, sid); if (s && s.real) return { key, sid, s, second: key === mp.c2 }; } }
  return null;
}
// the link of one PPI activity to its TrendX driver: lag correlation on the overlapping months, ARX forecast driven by our actual
// months past the PPI's last month and by our own commodity forecast beyond them
function tePpiLink(A, P, code, H, cwin = 30) {
  const key = `ppi|${code}|${H}|${cwin}`; if (A.fc[key]) return A.fc[key];
  const s = P.S[code], drv = tePpiDriver(A, P, code), out = { code, drv, v: s.v, last: P.last };
  if (drv) {
    const x = teOnPpi(A, P, drv.s.v), ext = x.slice(); for (let j = P.months.length; j <= P.last + H + 6; j++) ext[j] = A.at[ymAdd(P.months[0], j)] != null ? drv.s.v[A.at[ymAdd(P.months[0], j)]] : null;
    const overlap = P.months.filter((m, j) => s.v[j] != null && x[j] != null).length;
    out.overlap = overlap;
    out.lag = teBestLag(s.v, ext, P.last, Math.min(cwin, overlap), 6);
    const fcD = teFcOf(A, drv.sid, H + 12), base = ymAdd(P.months[0], 0);
    const future = (j) => { const ym = ymAdd(base, j), i = A.at[ym]; if (i != null && drv.s.v[i] != null && drv.s.v[i - 1] != null) return { v: pct(drv.s.v[i], drv.s.v[i - 1]), actual: true }; const h = (+ym.slice(0, 4) - +A.M[A.last].slice(0, 4)) * 12 + (+ym.slice(5) - +A.M[A.last].slice(5)); const f = (k) => (k <= 0 ? drv.s.v[A.last + k] : fcD?.ens?.[k - 1]); const a = f(h), b = f(h - 1); return a != null && b != null ? { v: pct(a, b), actual: false } : { v: 0, actual: false }; };
    out.fc = teForecast(s.v, P.last, H, out.lag.r != null ? { x: ext, lag: out.lag.lag, future } : null);
  } else out.fc = teForecast(s.v, P.last, H, null);
  A.fc[key] = out; return out;
}
// bottom-up PPI general index from the 4-digit activities with their base weights (the prototype's formula, link month as reference)
function tePpiBottomUp(A, P, H) {
  const iL = P.iLink >= 0 ? P.iLink : P.last, X = P.S.X.v, mem = P.L4.filter((c) => P.S[c].v[P.last] != null && P.S[c].v[iL] > 0);
  const base = mem.reduce((s, c) => s + P.S[c].w * P.S[c].v[P.last] / P.S[c].v[iL], 0), out = [];
  for (let h = 0; h < H; h++) { let s = 0; for (const c of mem) { const f = tePpiLink(A, P, c, H).fc, val = f?.ens && f.ens[h] != null ? f.ens[h] : P.S[c].v[P.last]; s += (P.S[c].w * val) / P.S[c].v[iL]; } out.push(X[P.last] * s / base); }
  return out;
}
// the feed for the prototype's "Import an automated feed" card: commodity rows {type, month, code, key, value}, our monthly
// movement chained onto the prototype's own level at its last month (so units never matter), for the months it lacks
function tePpiFeed(A, P) {
  const rows = [], cm = P.cmonths || [], cl = cm.length - 1;
  for (const c of P.comm || []) {
    const sids = PPI_KEY2SID[c.k] || [], sid = sids.find((id) => teSid(A, id)?.real); if (!sid) continue;
    const s = teSid(A, sid); let jl = cl; while (jl >= 0 && c.v[jl] == null) jl--; if (jl < 0) continue;
    const Lm = cm[jl], iL = A.at[Lm]; if (iL == null || !(s.v[iL] > 0)) continue;
    for (let i = iL + 1; i <= A.last; i++) if (s.v[i] > 0) rows.push({ type: "commodity", month: A.M[i], code: "", key: c.k, value: +(c.v[jl] * s.v[i] / s.v[iL]).toFixed(4), trendx_series: sid, chained_from: Lm, partial: i === A.last && A.partial ? 1 : 0 });
  }
  return rows;
}
