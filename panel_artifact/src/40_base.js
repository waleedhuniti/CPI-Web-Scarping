
// ============================================================ app: helpers, project config, data caches, statistics
const ROUTE2ID = { cpi: "cpi", sppi: "sppi", trendx: "te" };
const routeOf = (id) => (id === "te" ? "trendx" : id);
function projLabel(p) { return { cpi: "CPI", sppi: "SPPI", te: "TrendX" }[p] || projects[p]?.short || projects[p]?.name || p; }
const PAGES = [
  ["dashboard", "home", "Dashboard", "لوحة المتابعة"],
  ["outlets", "store", "Outlets", "المنافذ"],
  ["price-history", "pulse", "Price History", "سجل الأسعار التاريخي"],
  ["schedules", "alarm", "Schedules", "الجداول"],
  ["years-months", "calendar", "Years & Months", "السنوات والأشهر"],
  ["scrapers", "doc", "Scrapers", "الكاشطات"],
  ["price-logs", "file", "Price Logs", "سجل التشغيلات"],
  ["manual", "hand", "Manual Entry", "الإدخال اليدوي"],      // CPI and SPPI only (not TrendX)
];
const pageName = (pg) => { const x = PAGES.find((p) => p[0] === pg); return x ? L(x[2], x[3]) : pg; };

// ---------------- formatting (Latin digits in both languages, Dubai time)
const fmtN = (n, d) => (n == null || n === "" || !isFinite(n) ? "—" : Number(n).toLocaleString("en", d == null ? {} : { minimumFractionDigits: d, maximumFractionDigits: d }));
const locale = () => (LANG === "ar" ? "ar-u-nu-latn" : "en-GB");
// a Dubai calendar day "2026-11-02" (no time zone shift)
function fmtDay(d, opts = {}) {
  if (!d) return "—";
  try { return new Date(String(d).slice(0, 10) + "T12:00:00Z").toLocaleDateString(locale(), { timeZone: "UTC", day: "numeric", month: "short", ...(opts.year ? { year: "numeric" } : {}), ...(opts.weekday ? { weekday: "short" } : {}) }); }
  catch (e) { return String(d).slice(0, 10); }
}
const fmtMonth = (m) => { try { return new Date(m + "-15T12:00:00Z").toLocaleDateString(locale(), { timeZone: "UTC", month: "short", year: "numeric" }); } catch (e) { return m; } };
const fmtMonthLong = (m) => { try { return new Date(m + "-15T12:00:00Z").toLocaleDateString(locale(), { timeZone: "UTC", month: "long", year: "numeric" }); } catch (e) { return m; } };
function fmtDate(iso) { return iso ? fmtDay(dubaiDay(iso)) : "—"; }
function fmtTimeDubai(iso) { try { return new Date(iso).toLocaleTimeString("en-GB", { timeZone: "Asia/Dubai", hour: "2-digit", minute: "2-digit", hour12: false }); } catch (e) { return ""; } }
function dubaiDT(iso) { return iso ? `${dubaiDay(iso)} ${fmtTimeDubai(iso)}` : ""; }
function relTime(iso) {
  const s = (Date.now() - Date.parse(iso)) / 1000; if (!isFinite(s)) return "—";
  if (s < 3600) return L(`${Math.max(1, Math.round(s / 60))} min ago`, `قبل ${Math.max(1, Math.round(s / 60))} د`);
  if (s < 86400) return L(`${Math.round(s / 3600)} h ago`, `قبل ${Math.round(s / 3600)} س`);
  return L(`${Math.round(s / 86400)} days ago`, `قبل ${Math.round(s / 86400)} يوم`);
}
const runState = (lr) => (lr ? (lr.status === "done" ? "ok" : lr.status === "error" ? "bad" : "warn") : "");
const dayAdd = (d, n) => new Date(Date.parse(d + "T12:00:00Z") + n * 86400000).toISOString().slice(0, 10);
const daySpan = (a, b) => Math.round((Date.parse(b + "T12:00:00Z") - Date.parse(a + "T12:00:00Z")) / 86400000);
const todayDubai = () => dubaiDay(new Date().toISOString());
const monthEnd = (m) => dayAdd(dayAdd(m + "-01", 32).slice(0, 7) + "-01", -1);

// ---------------- small html builders
const ICON_EXTRA = {
  store: '<path d="M4 21V8l8-5 8 5v13"/><path d="M9 21v-6h6v6"/><path d="M9 10h.01M15 10h.01"/>',
  pulse: '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
  alarm: '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2 2M5 3 2 6M19 3l3 3"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
  doc: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/>',
  file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
  box: '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
  records: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 17v-3M12 17v-5M15 17v-2"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/>',
  check: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  ban: '<circle cx="12" cy="12" r="9"/><path d="m5.6 5.6 12.8 12.8"/>',
  hex: '<path d="M12 2 21 7v10l-9 5-9-5V7z"/>',
  chip: '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
  warn: '<path d="M12 3 2 21h20z"/><path d="M12 10v5M12 18h.01"/>',
  bag: '<path d="M5 8h14l-1 13H6z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  refresh: '<path d="M20 11a8 8 0 0 0-14-5l-2 2"/><path d="M4 4v4h4"/><path d="M4 13a8 8 0 0 0 14 5l2-2"/><path d="M20 20v-4h-4"/>',
  reset: '<path d="M4 12a8 8 0 1 0 2.3-5.7L4 8.6"/><path d="M4 4v4.6h4.6"/>',
  funnel: '<path d="M3 4h18l-7 8.5V19l-4 2v-8.5z"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  listico: '<path d="M9 6h11M9 12h11M9 18h11"/><path d="M4.5 6h.01M4.5 12h.01M4.5 18h.01"/>',
  grid4: '<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',
  download: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  close: '<path d="M6 6l12 12M18 6 6 18"/>',
  hand: '<path d="M8 13V5.5a1.5 1.5 0 0 1 3 0V12"/><path d="M11 11V4.5a1.5 1.5 0 0 1 3 0V12"/><path d="M14 11.5V6a1.5 1.5 0 0 1 3 0v8a7 7 0 0 1-7 7h-.5a6 6 0 0 1-5-2.7L3 15.5a1.5 1.5 0 0 1 2.4-1.8L8 16"/>',
  hotel: '<path d="M3 21V7l9-4 9 4v14"/><path d="M8 21v-4h8v4M8 10h.01M12 10h.01M16 10h.01M8 13.5h.01M12 13.5h.01M16 13.5h.01"/>',
};
Object.assign(ICONS, ICON_EXTRA);
const chip = (text, tone = "grey", attrs = "") => `<span class="chip ${tone}"${attrs}>${esc(text)}</span>`;
const loadingHtml = (text) => `<div class="loading" role="status">${esc(text)}</div>`;
function errBox(msg, retryId) {
  return `<div class="errbox" role="alert"><span class="bang" aria-hidden="true">!</span><span class="msg">${esc(msg)}</span>${retryId ? `<button type="button" id="${esc(retryId)}" data-retry>${ico("refresh")}${esc(L("Retry", "أعد المحاولة"))}</button>` : ""}</div>`;
}
function emptyHtml(icon, title, text, action = "") {
  return `<div class="empty-state"><span class="es-ico">${ico(icon)}</span><h3>${esc(title)}</h3>${text ? `<p>${esc(text)}</p>` : ""}${action}</div>`;
}
// a KPI card: tint (blue | green | red | amber), value "—" until known, delta chip only with a real value
function kpiHtml(o) {
  const delta = o.delta == null ? "" : o.delta === 0 ? `<span class="delta zero">0</span>` : `<span class="delta${o.delta < 0 ? " down" : ""}">${o.delta > 0 ? "+" : "−"}${fmtN(Math.abs(o.delta))}${o.deltaLabel ? " " + esc(o.deltaLabel) : ""}</span>`;
  const tag = o.href ? "a" : "div";
  return `<${tag} class="kpi ${o.tint || ""}" id="${esc(o.id)}"${o.href ? ` href="${esc(o.href)}"` : ""}><span class="ktile">${ico(o.icon)}</span>
    <span class="kb"><span class="kv" data-v>${esc(o.value ?? "—")}</span><span class="kl">${esc(o.label)}</span>${o.sub ? `<span class="ks" data-s>${esc(o.sub)}</span>` : `<span class="ks" data-s></span>`}</span>${delta}</${tag}>`;
}
function setKpi(id, value, sub, delta, deltaLabel) {
  const el = document.getElementById(id); if (!el) return;
  $("[data-v]", el).textContent = value;
  if (sub !== undefined) $("[data-s]", el).textContent = sub || "";
  el.querySelector(".delta")?.remove();
  if (delta != null) el.insertAdjacentHTML("beforeend", delta === 0 ? `<span class="delta zero">0</span>` : `<span class="delta${delta < 0 ? " down" : ""}">${delta > 0 ? "+" : "−"}${fmtN(Math.abs(delta))}${deltaLabel ? " " + esc(deltaLabel) : ""}</span>`);
}
// outlet state vocabulary (§5.1): always text, with the reason in the title
const STATE = {
  ok: ["Read OK", "قُرئ بالكامل", "ok"], partial: ["Partial", "جزئي", "warn"], blocked: ["Blocked", "محجوب", "bad"],
  failed: ["Failed", "فشل", "bad"], notread: ["Not read", "لم يُقرأ", "grey"], manual: ["Manual", "يدوي", "manual"],
};
const stateText = (s) => L(STATE[s]?.[0] || s, STATE[s]?.[1] || s);
const stateChip = (s, reason = "", since = "") => `<span class="chip ${STATE[s]?.[2] || "grey"}"${reason ? ` title="${esc(reason)}"` : ""}>${esc(stateText(s))}${since ? " " + esc(since) : ""}</span>${reason ? ` <span class="muted">${esc(reason)}</span>` : ""}`;
// run status vocabulary (Price Logs, Schedules, Home)
const RUNST = { completed: ["Completed", "مكتمل", "ok"], partial: ["Partial", "جزئي", "warn"], failed: ["Failed", "فشل", "bad"], running: ["Running", "يعمل", "blue"], warnings: ["Completed with warnings", "مكتمل مع تحذيرات", "warn"] };
const runChip = (rs) => `<span class="chip ${RUNST[rs.code]?.[2] || "grey"}">${esc(L(RUNST[rs.code]?.[0] || rs.code, RUNST[rs.code]?.[1] || rs.code))}${rs.text ? ": " + esc(rs.text) : ""}</span>`;

// ---------------- per-project caches (one session)
const S = {};
const st = (pid) => (S[pid] ??= { rows: new Map() });
async function ensureRuns(pid, fresh) {
  const s = st(pid);
  if (s.runs && !fresh) return s.runs;
  const snap = await db.collection(`projects/${pid}/runs`).orderBy("startedAt", "desc").limit(60).get();
  s.runs = snap.docs.map((d) => ({ id: d.id, ...plain(d) }));
  if (pid === current) runs = s.runs;
  return s.runs;
}
async function ensureBasket(pid) {
  const s = st(pid);
  if (s.basket) return s.basket;
  s.basket = await loadBasket(pid);
  return s.basket;
}
// the rows of one run (all chunks), cached
async function runRows(pid, run) {
  const s = st(pid);
  if (s.rows.has(run.id)) return s.rows.get(run.id);
  const list = (await rowDocs(pid, run)).flatMap((d) => plain(d).rows || []);
  s.rows.set(run.id, list);
  return list;
}
async function getDoc(path) { try { const s = await db.doc(path).get(); return s.exists ? plain(s) : null; } catch (e) { return null; } }   // optional reads only: an error reads as "absent"
// reads that decide a write or an empty state: null only when the doc does not exist; a failed read throws
async function getDocStrict(path) { const s = await db.doc(path).get(); return s.exists ? plain(s) : null; }
function afterRunsChanged() { if (S[current]) { S[current].runs = null; S[current].dayRuns = null; } if (typeof rerender === "function") rerender(); }

// ---------------- runs: Dubai day, one run per day, legacy browser runs
const isAutoRun = (r) => /-auto$/.test(r.id);
const runDay = (r) => r.run_date || dubaiDay(r.startedAt);
// latest finished run of each Dubai day (ascending), and the set of the other runs of those days ("duplicate")
function dayRunsOf(list) {
  const by = new Map();
  for (const r of list) {
    if (!isAutoRun(r) || r.status === "running" || !r.finishedAt && r.status !== "done" && r.status !== "error") continue;
    const d = runDay(r), cur = by.get(d);
    if (!cur || String(r.startedAt) > String(cur.startedAt)) by.set(d, r);
  }
  const days = [...by.entries()].sort((a, b) => a[0].localeCompare(b[0])).map(([d, r]) => ({ day: d, run: r }));
  const kept = new Set(days.map((x) => x.run.id));
  const dup = new Set(list.filter((r) => isAutoRun(r) && !kept.has(r.id) && by.has(runDay(r))).map((r) => r.id));
  return { days, dup };
}

// ---------------- CPI: outlet states from the run log (one parser, used on every page)
const CPI_OUTLETS = [
  { code: "carrefour", en: "Carrefour", ar: "كارفور", daily: true, stores: ["Carrefour"] },
  { code: "lulu", en: "Lulu Hypermarket", ar: "لولو هايبرماركت", daily: true, stores: ["Lulu"] },
  { code: "sharafdg", en: "Sharaf DG", ar: "شرف دي جي", stores: ["Sharaf DG"] },
  { code: "zara", en: "Zara", ar: "زارا", stores: ["Zara"] },
  { code: "max", en: "Max", ar: "ماكس", stores: ["Max"] },
  { code: "centrepoint", en: "Centrepoint", ar: "سنتربوينت", stores: ["Centrepoint (Centrepoint)", "Splash (Centrepoint)", "Babyshop (Centrepoint)", "Shoexpress (Centrepoint)", "Shoe Mart (Centrepoint)"],
    children: [["Splash", "سبلاش", "Splash (Centrepoint)"], ["Babyshop", "بيبي شوب", "Babyshop (Centrepoint)"], ["Shoexpress", "شو إكسبرس", "Shoexpress (Centrepoint)"], ["Shoe Mart", "شو مارت", "Shoe Mart (Centrepoint)"], ["Centrepoint", "سنتربوينت", "Centrepoint (Centrepoint)"]] },
];
const retailerKey = (name) => (/carrefour/i.test(name) ? "carrefour" : /lulu/i.test(name) ? "lulu" : /sharaf/i.test(name) ? "sharafdg" : String(name || "").trim().split(/\s+/)[0].toLowerCase());
const outletEn = (code) => CPI_OUTLETS.find((o) => o.code === code)?.en || code;
function cpiLogStates(run) {
  const out = {};
  for (const l of run?.log || []) {
    let m = /^(.+?) barcode: (\d+) pages read, (\d+) failed/.exec(l);
    if (m) {
      const k = retailerKey(m[1]), read = +m[2], failed = +m[3], tot = read + failed, share = tot ? failed / tot : 1;
      const state = share <= 0.05 ? "ok" : share < 0.9 ? "partial" : "blocked";
      out[k] = { ...(out[k] || {}), state, read, failed, share, line: l, cats: out[k]?.cats || [] };
      continue;
    }
    m = /^(\w+) \| (.+): (\d+) products from (\d+) pages/.exec(l);
    if (m) { const k = retailerKey(m[1]); (out[k] ??= { cats: [] }).cats.push({ cat: m[2], products: +m[3], pages: +m[4] }); }
  }
  for (const k of Object.keys(out)) if (!out[k].state) out[k].state = "notread";
  return out;
}
function cpiReason(o, k) {
  if (!o || o.state === "notread") return L("no log line", "لا سطر في السجل");
  if (o.state === "blocked") return L(`${fmtN(o.failed)} of ${fmtN(o.read + o.failed)} pages refused`, `رُفضت ${fmtN(o.failed)} من ${fmtN(o.read + o.failed)} صفحة`);
  return L(`${fmtN(o.failed)}/${fmtN(o.read + o.failed)} pages failed`, `فشلت ${fmtN(o.failed)}/${fmtN(o.read + o.failed)} صفحة`);
}
const cpiBlockedSet = (run) => new Set(Object.entries(cpiLogStates(run)).filter(([, v]) => v.state === "blocked").map(([k]) => k));
function cpiCarried(run) { let n = 0; for (const k of cpiBlockedSet(run)) n += run.summary?.[`${k}_category`]?.accepted || 0; return n; }
const cpiSeen = (run) => Math.max(0, (run?.accepted || 0) - cpiCarried(run));
function annotateRows(pid, run, rows) {
  if (pid === "cpi") { const b = cpiBlockedSet(run); return rows.map((r) => ({ ...r, obs_state: r.source === "category" && b.has(r.retailer) ? "blocked_carried" : "seen" })); }
  if (pid === "te") { const c = dubaiDT(run.startedAt); return rows.map((r) => ({ ...r, collected_dubai: c })); }
  return rows;
}
// the run status chip (§5.1)
function runStatus(pid, run) {
  if (!run) return { code: "failed", text: "" };
  if (run.status === "running") return { code: "running", text: "" };
  if (pid === "te") {
    const n = run.count ?? run.accepted ?? 0;
    if (run.status === "error" || n < 20) return { code: "failed", text: L(`only ${n} rows`, `${n} صفاً فقط`) };
    if (n < TE_BASKET_N) return { code: "partial", text: L(`${n} of ${TE_BASKET_N} rows`, `${n} من ${TE_BASKET_N} صفاً`) };
    return { code: "completed", text: "" };
  }
  if (pid !== "cpi") return { code: run.status === "done" ? "completed" : "failed", text: "" };
  const s = cpiLogStates(run), keys = ["carrefour", "lulu"];
  if (!Object.keys(s).length) return { code: run.status === "done" ? "completed" : "failed", text: "" };
  const seen = cpiSeen(run), states = keys.map((k) => s[k]?.state || "notread");
  if (!seen || !states.some((x) => x === "ok" || x === "partial")) return { code: "failed", text: L("no outlet read", "لم يُقرأ أي منفذ") };
  if (states.every((x) => x === "ok")) {
    if (run.status === "error") {
      const k = keys.find((k) => s[k]?.failed > 0), o = s[k];
      return { code: "warnings", text: o ? L(`${o.failed}/${o.read + o.failed} ${outletEn(k).split(" ")[0]} pages failed`, `فشلت ${o.failed}/${o.read + o.failed} صفحة ${outletEn(k).split(" ")[0]}`) : (run.log || []).find((l) => /error|fail/i.test(l)) || "" };
    }
    return { code: "completed", text: "" };
  }
  const parts = keys.filter((k) => (s[k]?.state || "notread") !== "ok").map((k) => {
    const o = s[k], nm = outletEn(k).split(" ")[0];
    if (!o || o.state === "notread") return L(`${nm} not read`, `${nm} لم يُقرأ`);
    if (o.state === "blocked") return L(`${nm} blocked (${fmtN(o.failed)} pages refused)`, `${nm} محجوب (رُفضت ${fmtN(o.failed)} صفحة)`);
    return L(`${nm} ${o.failed}/${o.read + o.failed} pages failed`, `${nm} فشلت ${o.failed}/${o.read + o.failed} صفحة`);
  });
  return { code: "partial", text: parts.join(", ") };
}
// "Blocked since": walk back through the daily runs to the first run of the current blocked streak
function cpiBlockedSince(days, k) {
  let since = null, n = 0;
  for (let i = days.length - 1; i >= 0; i--) { const o = cpiLogStates(days[i].run)[k]; if (o?.state !== "blocked") break; since = days[i].day; n++; }
  return since ? { day: since, runs: n } : null;
}
// CPI exact-match rows (index grade): barcode matches, catalogue name matches and name searches; product sets are Tier B
const EXACT_DETAIL = new Set(["barcode_search_match", "name_match", "barcode_match_unit_label"]);
const isExact = (r) => (r.source === "barcode" && EXACT_DETAIL.has(r.detail)) || r.detail === "catalogue name match" || r.source === "name_search";
const isTierB = (r) => /product[ _]set/i.test(r.detail || "");
const regPrice = (r) => { const v = num(r.regular_price); return v != null && v > 0 ? v : num(r.price); };

// ---------------- TrendX
const TE_DEFAULT_INDEX = { base: "2026-10-02", exclude_categories: ["Index", "Electricity"], method: "chained_jevons", monthly: "mean_of_daily" };
let TE_EXCL = TE_DEFAULT_INDEX.exclude_categories, TE_BASKET_N = 107;
const TE_CATS = ["Energy", "Agricultural", "Industrial", "Metals", "Livestock"];
const teCatName = (c) => L(c, { Energy: "الطاقة", Agricultural: "الزراعة", Industrial: "الصناعة", Metals: "المعادن", Livestock: "الماشية", Index: "المؤشرات", Electricity: "الكهرباء", All: "الكل" }[c] || c);
// every TrendX run with its rows (one small chunk per run), ascending by day; cached
async function teDays() {
  const s = st("te");
  if (s.teDays) return s.teDays;
  const list = await ensureRuns("te");
  const { days } = dayRunsOf(list);
  const out = [];
  for (const { day, run } of days) {
    const rows = await runRows("te", run);
    out.push({ day: rows[0]?.run_date || day, run, rows });
  }
  const pd = projects.te?.index; if (pd?.exclude_categories) TE_EXCL = pd.exclude_categories;
  s.teDays = out.sort((a, b) => a.day.localeCompare(b.day));
  await teLinkLoad(s.teDays);          // the 2024 base; a failure only leaves the first-day base
  return s.teDays;
}
const teKey = (r) => `${r.category}|${r.commodity}|${r.unit}`;
// chained Jevons over commodities priced on both consecutive run days (one chain per category, or All)
function teIndexRaw(days, cat = "All") {
  const out = []; let I = 100, prev = null;
  for (const d of days) {
    const m = new Map();
    for (const r of d.rows) { if (TE_EXCL.includes(r.category) || (cat !== "All" && r.category !== cat)) continue; const p = Number(r.price); if (p > 0) m.set(teKey(r), p); }
    if (prev) { let s = 0, n = 0; for (const [k, p] of m) { const q = prev.get(k); if (q > 0) { s += Math.log(p / q); n++; } } if (n) I *= Math.exp(s / n); out.push({ x: d.day, y: I, n }); }
    else out.push({ x: d.day, y: 100, n: m.size });
    prev = m;
  }
  return out;
}
const meanOf = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);
// 2024 = 100: the daily chained index is linked to the monthly store (projects/te/history, scripts/trendx/build_history_store.py) at
// the store's last external month, so its level carries the manager's base (mean of 2024 = 100, carried-back series included, as
// the store's "all series" index). Without the store the index falls back to its first day = 100 and the labels say so.
let teLink = null;   // { ok, month, factor: {All, Energy, ...} }
async function teLinkLoad(days) {
  if (teLink) return teLink;
  try {
    const h = await teHistoryLoad(); if (!h) { teLink = { ok: false }; return teLink; }
    const inIdx = new Set(h.series.filter((s) => +s.in_index).map((s) => s.series_id)), catOf = Object.fromEntries(h.series.map((s) => [s.series_id, s.category]));
    const months = [...new Set(Object.values(h.obs).flat().filter((x) => x[3] !== "te" && x[3] !== "carried_back").map((x) => x[0]))].sort();
    const Lm = months[months.length - 1];
    const gm = (cat) => { const v = []; for (const [sid, o] of Object.entries(h.obs)) { if (!inIdx.has(sid) || (cat !== "All" && catOf[sid] !== cat)) continue; const p = o.find((x) => x[0] === Lm); if (p && p[2] > 0) v.push(Math.log(p[2])); } return v.length ? Math.exp(v.reduce((a, b) => a + b, 0) / v.length) : null; };
    const factor = {};
    for (const c of ["All", ...TE_CATS]) { const m = meanOf(teIndexRaw(days, c).filter((p) => p.x.startsWith(Lm)).map((p) => p.y)), g = gm(c); factor[c] = m && g ? g / m : 1; }
    teLink = { ok: !!Lm, month: Lm, factor };
  } catch (e) { teLink = { ok: false, error: e?.message || String(e) }; }
  return teLink;
}
function teIndex(days, cat = "All") { const f = teLink?.ok ? (teLink.factor[cat] ?? 1) : 1; return teIndexRaw(days, cat).map((p) => ({ ...p, y: p.y * f })); }
const teBaseLabel = () => (teLink?.ok ? L("mean of 2024 = 100", "متوسط 2024 = 100") : `${fmtDay(TE_DEFAULT_INDEX.base, { year: true })} = 100`);
function teMonthly(series, month) { const v = series.filter((p) => p.x.startsWith(month)).map((p) => p.y); return { mean: meanOf(v), n: v.length }; }

// ---------------- SPPI (project data under projects/sppi; §9 extended shape, the minimal draft shape also read)
let sppiCache = null;                            // { meta, metaPath, metaRaw, version, weeks, periods, obs: Map }
const SPPI_META_PATH = "projects/sppi/meta/current";
async function sppiLoad(fresh) {
  if (sppiCache && !fresh) return sppiCache;
  let meta = null, metaPath = SPPI_META_PATH;
  const m1 = await getDocStrict(SPPI_META_PATH);          // a failed read throws: never shown as "no basket"
  if (m1) meta = m1;
  else {
    const p = projects.sppi || await getDocStrict("projects/sppi");
    if (p?.meta && typeof p.meta === "object") { meta = p.meta; metaPath = "projects/sppi"; }
    else if (p && (p.weeks || p.items || p.outlets)) { meta = p; metaPath = "projects/sppi"; }
  }
  if (!meta) { sppiCache = { meta: null }; return sppiCache; }
  const metaRaw = JSON.stringify(meta);
  const weeks = (meta.weeks || []).map((w, i) => {
    const id = w.id || w.week || `C${i + 1}`;
    const month = w.month || String(w.tickets?.out || w.from || w.collected_on || "").slice(0, 7);
    return { ...w, id, month, n: w.n || i + 1,
      tickets: w.tickets || (w.from ? { out: w.from, back: w.to } : {}), packages: w.packages || (w.from ? { checkin: w.from, checkout: w.to } : {}),
      label_en: w.label_en || w.label || id, label_ar: w.label_ar || w.label || id };
  });
  // collections are numbered inside their month (W1/W2/W3 of Nov are collections 1-3 of period 2026-11)
  const byMonth = {}; for (const w of weeks) { byMonth[w.month] = (byMonth[w.month] || 0) + 1; w.cn = byMonth[w.month]; }
  const periods = (meta.periods && meta.periods.length ? meta.periods : [...new Set(weeks.map((w) => w.month))].map((m) => ({ id: m, month: m }))).map((p) => ({ ...p, id: p.id || p.month, month: p.month || p.id }));
  const obs = new Map();
  for (const w of weeks) {
    const d = await getDocStrict(`projects/sppi/observations/${w.id}`);   // a failed read throws: never shown as an empty collection
    obs.set(w.id, { raw: d ? JSON.stringify(d) : null, version: d?.version ?? null, rows: (d?.rows || []).map((r) => sppiNormRow(r, w.id)) });
  }
  sppiCache = { meta, metaPath, metaRaw, version: meta.version ?? null, weeks, periods, obs,
    outlets: meta.outlets || [], items: meta.items || [], sample: meta.sample || [], collectors: meta.collectors || [], files: meta.files || [] };
  return sppiCache;
}
function sppiNormRow(r, wid) {
  const survey = r.survey || (r.kind === "route" ? "tickets" : r.kind === "hotel" ? "packages" : r.kind) || (r.leg === "package" ? "packages" : "tickets");
  const has = [r.lowest, r.highest, r.price].some((v) => num(v) != null);
  return { ...r, week: r.week || wid, survey, status: r.status || (has ? "ok" : "not_available"), flags: r.flags || [], source: r.source || "scraped",
    lowest: num(r.lowest), highest: num(r.highest), price: num(r.price) };
}
const sppiItem = (code) => sppiCache?.items.find((i) => i.code === code);
const sppiOutlet = (code) => sppiCache?.outlets.find((o) => o.code === code);
const sppiName = (x) => (x ? (LANG === "ar" ? x.name_ar || x.name_en || x.code : x.name_en || x.name_ar || x.code) : "");
const sppiWeekLabel = (w) => L(`Collection ${w.cn}`, `الجمع ${w.cn}`);
const sppiSurveyOf = (it) => (it?.kind === "hotel" ? "packages" : "tickets");
const sppiActiveRows = (wid) => (sppiCache?.obs.get(wid)?.rows || []).filter((r) => r.status !== "withdrawn");
// the row that stands for a cell: a manual row wins over a scraped one (latest entry first)
function sppiCell(wid, outlet, item, leg) {
  const rs = sppiActiveRows(wid).filter((r) => r.outlet === outlet && r.item === item && (r.leg || "package") === leg);
  if (!rs.length) return null;
  return rs.find((r) => r.source === "manual") ? rs.filter((r) => r.source === "manual").sort((a, b) => String(b.entered_at).localeCompare(String(a.entered_at)))[0] : rs[0];
}
// outlet state for one collection (§5.1 SPPI parser)
function sppiOutletState(wid, outlet) {
  const rs = sppiActiveRows(wid).filter((r) => r.outlet === outlet);
  if (!rs.length) return { state: "notread", reason: L("no rows", "لا صفوف") };
  if (rs.some((r) => r.source === "manual")) return { state: "manual", reason: L(`${rs.filter((r) => r.source === "manual").length} manual`, `${rs.filter((r) => r.source === "manual").length} يدوي`) };
  const ok = rs.filter((r) => r.status === "ok").length, bl = rs.filter((r) => r.status === "blocked").length;
  if (ok === rs.length) return { state: "ok", reason: L(`${ok} cells`, `${ok} خلية`) };
  if (bl === rs.length) return { state: "blocked", reason: rs.find((r) => r.note)?.note || L(`${bl} cells refused`, `${bl} خلية محجوبة`) };
  return { state: "partial", reason: L(`${ok} of ${rs.length} cells ok`, `${ok} من ${rs.length} خلية سليمة`) };
}
// a ticket total from its out and back legs (template rule): low = out + back, high falls back to low per leg, price = mean of the totals
// A leg counts only when it is a manual price or a scraped price with status ok / partial / to_review (never blocked, not_available,
// failed or withdrawn). A total built from a leg marked to_review carries status "to_review" and is shown with the review chip.
const SPPI_LEG_OK = new Set(["ok", "partial", "to_review"]);
const sppiLegUsable = (x) => !!x && x.lowest != null && x.status !== "withdrawn" && (x.source === "manual" || SPPI_LEG_OK.has(x.status));
function sppiTotal(out, back) {
  if (!sppiLegUsable(out) || !sppiLegUsable(back)) return null;
  const low = out.lowest + back.lowest, high = (out.highest ?? out.lowest) + (back.highest ?? back.lowest);
  const review = [out, back].some((x) => x.source !== "manual" && x.status === "to_review");
  return { lowest: low, highest: high, price: (low + high) / 2, status: review ? "to_review" : "ok" };
}
// priced cells of a collection (ok rows with a price; totals are computed on the page and not counted again)
const hasPrice = (r) => r.lowest != null || r.price != null;
const sppiPriced = (wid) => sppiActiveRows(wid).filter((r) => (r.status === "ok" || r.source === "manual") && (r.lowest != null || r.price != null)).length;
const sppiExpected = (survey) => (sppiCache?.sample || []).filter((s) => s.status !== "retired" && (!survey || s.survey === survey)).reduce((n, s) => n + (s.legs || ["package"]).length, 0);
