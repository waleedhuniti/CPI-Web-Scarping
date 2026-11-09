// ============================================================ TrendX: monthly history with a 2024 = 100 base (Price History › History tab)
// Data: projects/te/history/latest {asset, built, ...} pointing at an uploaded JSON built by scripts/trendx/build_history_store.py:
// {series:[...], obs:{series_id:[[period, value, idx2024, source, backfilled, linked], ...]}, index:[...], backfill:[...]}.
// Real history (World Bank, EIA) from Jan 2024, chained onto our own monthly means from Oct 2026. A series without a free history
// source is carried back (its first collected price held constant to Jan 2024): flagged, shown grey, and never used for modelling.
let teHist = null, teHistErr = null;
async function teHistoryLoad() {
  if (teHist) return teHist;
  const ptr = await getDocStrict("projects/te/history/latest");
  if (!ptr?.asset) return null;
  const r = await fetch("/_blob/" + ptr.asset); if (!r.ok) throw new Error("history file HTTP " + r.status);
  teHist = { ptr, ...(await r.json()) }; return teHist;
}
const fmtYM = (ym) => { try { return new Date(ym + "-15T12:00:00Z").toLocaleDateString(locale(), { timeZone: "UTC", month: "short", year: "2-digit" }); } catch (e) { return ym; } };
const baseChip = (s) => s.base_method === "actual" ? (s.proxy ? chip(L("Proxy history", "تاريخ بديل"), "yellow") : chip(L("Real history", "تاريخ حقيقي"), "ok")) : chip(L("Carried back", "مُثبّت رجوعاً"), "grey");
async function drawTeHistory(box) {
  box.innerHTML = loadingHtml(L("Reading the 2024-based history…", "تُقرأ سلاسل أساس 2024…"));
  let h;
  try { h = await teHistoryLoad(); } catch (e) { box.innerHTML = errBox(L("The history file could not be read. ", "تعذّرت قراءة ملف التاريخ. ") + dbErr(e), "th-retry"); $("#th-retry").onclick = () => drawTeHistory(box); return; }
  if (!h) { box.innerHTML = emptyHtml("calendar", L("No 2024 history stored yet", "لا تاريخ بأساس 2024 بعد"), L("Run scripts/trendx/build_history_store.py and upload its history_2024.json; the pointer is projects/te/history/latest.", "شغّل scripts/trendx/build_history_store.py وارفع history_2024.json؛ المؤشر في projects/te/history/latest.")); return; }
  const S = h.series, act = S.filter((s) => s.base_method === "actual"), prox = act.filter((s) => +s.proxy), carried = S.filter((s) => s.base_method !== "actual");
  const idx = (h.index || []).filter((r) => r.trendx_2024eq100_actual_history !== "");
  const last = idx[idx.length - 1], lastFull = idx.length > 1 ? idx[idx.length - 2] : last;
  const state = { q: "", kind: "", cat: "" };
  const cats = [...new Set(S.map((s) => s.category))];
  box.innerHTML = `
    <div class="kpis four" style="margin-bottom:4px">
      ${kpiHtml({ id: "th-k-idx", icon: "trend", label: L("Index, latest full month", "المؤشر، آخر شهر كامل") })}
      ${kpiHtml({ id: "th-k-act", icon: "check", tint: "green", label: L("Series with real 2024 history", "سلاسل لها تاريخ 2024 حقيقي") })}
      ${kpiHtml({ id: "th-k-prox", icon: "hex", tint: "amber", label: L("Of them through a proxy", "منها عبر سلسلة بديلة") })}
      ${kpiHtml({ id: "th-k-car", icon: "warn", tint: "red", label: L("Carried back (flagged)", "مُثبّتة رجوعاً (معلَّمة)") })}
    </div>
    <section class="card stack"><div class="card-h"><h3>${esc(L("TrendX monthly index, mean of 2024 = 100", "مؤشر TrendX الشهري، متوسط 2024 = 100"))}</h3>
      <p class="sub">${esc(L(`Equal-weight geometric mean of the ${act.length} index series with real history (World Bank, EIA), chained onto our daily collection from Oct 2026. The lighter line adds the ${carried.filter((s) => +s.in_index).length} carried-back series: it shows what the backfill rule hides. The last month is partial.`, `متوسط هندسي متساوي الأوزان لـ ${act.length} سلسلة لها تاريخ حقيقي (البنك الدولي، EIA)، موصولة بجمعنا اليومي من أكتوبر 2026. الخط الأفتح يضيف ${carried.filter((s) => +s.in_index).length} سلسلة مُثبّتة رجوعاً ليُظهر ما تخفيه قاعدة التثبيت. آخر شهر غير مكتمل.`))}</p></div>
      ${lineChart({ id: "th-chart", height: 280, title: L("TrendX 2024 = 100", "TrendX 2024 = 100"), xFmt: fmtYM, yFmt: (v) => v.toFixed(1), noArea: false,
        series: [{ label: L("Real-history series", "سلاسل التاريخ الحقيقي"), points: idx.map((r) => ({ x: r.period, y: +r.trendx_2024eq100_actual_history, n: +r.n_series_actual })) },
                 { label: L("All index series (incl. carried back)", "كل سلاسل المؤشر (مع المُثبّتة)"), color: "#94a3b8", points: idx.map((r) => ({ x: r.period, y: +r.trendx_2024eq100_all_series, n: +r.n_series_all })) }] })}
      <p class="muted" style="margin:0">${esc(L(`Built ${h.built}. Sources: ${h.sources?.wb}; ${h.sources?.eia}; ${h.sources?.fx}; ${h.sources?.te}. Files: ${h.ptr.repo_path || "data/trendx/store/"} in the repository.`, `بُني ${h.built}. المصادر: ${h.sources?.wb}؛ ${h.sources?.eia}؛ ${h.sources?.fx}؛ ${h.sources?.te}. الملفات: ${h.ptr.repo_path || "data/trendx/store/"} في المستودع.`))}</p></section>
    <section class="card stack"><div class="card-h"><h3>${esc(L("Series", "السلاسل"))}</h3><span class="spacer"></span>
      <select id="th-kind" aria-label="${esc(L("History kind", "نوع التاريخ"))}"><option value="">${esc(L("All kinds", "كل الأنواع"))}</option><option value="actual">${esc(L("Real history", "تاريخ حقيقي"))}</option><option value="proxy">${esc(L("Proxy history", "تاريخ بديل"))}</option><option value="carried">${esc(L("Carried back", "مُثبّت رجوعاً"))}</option></select>
      <select id="th-cat" aria-label="${esc(L("Category", "الفئة"))}"><option value="">${esc(L("All categories", "كل الفئات"))}</option>${cats.map((c) => `<option value="${esc(c)}">${esc(teCatName(c))}</option>`).join("")}</select>
      <label class="search" style="flex:1 1 220px"><span class="sr-only">${esc(L("Search series", "ابحث في السلاسل"))}</span>${ico("search")}<input id="th-q" type="search" placeholder="${esc(L("Search series", "ابحث في السلاسل"))}"></label></div>
      <div id="th-table"></div>
      <p class="muted" style="margin:0">${esc(L("2024 mean: the base of each series in its TE unit. Proxy: real history of a related product or market (named), used for movement, not level. Carried back: the first collected price held constant to Jan 2024, flagged E; excluded from correlation and modelling and replaced when a source is found. Select a series for its monthly path.", "متوسط 2024: أساس كل سلسلة بوحدة TE. بديل: تاريخ حقيقي لمنتج أو سوق قريب (مسمّى)، للحركة لا للمستوى. مُثبّت رجوعاً: أول سعر مجموع ثُبّت إلى يناير 2024 بعلامة E؛ يُستبعد من الارتباط والنمذجة ويُستبدل حين يتوفر مصدر. اختر سلسلة لعرض مسارها الشهري."))}</p></section>`;
  setKpi("th-k-idx", last ? fmtN(+lastFull.trendx_2024eq100_actual_history, 1) : "—", lastFull ? L(`${fmtYM(lastFull.period)} · ${lastFull.n_series_actual} series · latest ${fmtYM(last.period)} ${fmtN(+last.trendx_2024eq100_actual_history, 1)} (partial)`, `${fmtYM(lastFull.period)} · ${lastFull.n_series_actual} سلسلة · الأحدث ${fmtYM(last.period)} ${fmtN(+last.trendx_2024eq100_actual_history, 1)} (جزئي)`) : "");
  setKpi("th-k-act", fmtN(act.length), L(`of ${S.length} series (${S.filter((s) => +s.in_index).length} in the index)`, `من ${S.length} سلسلة (${S.filter((s) => +s.in_index).length} في المؤشر)`));
  setKpi("th-k-prox", fmtN(prox.length), L("related product or market", "منتج أو سوق قريب"));
  setKpi("th-k-car", fmtN(carried.length), L("no free licensed history yet", "لا تاريخ مجاني مرخّص بعد"));
  const lastIdx = (sid) => { const o = (h.obs[sid] || []).filter((x) => x[2] != null); return o.length ? o[o.length - 1] : null; };
  const draw = () => {
    const rows = S.filter((s) => (!state.cat || s.category === state.cat) && (!state.kind || (state.kind === "carried" ? s.base_method !== "actual" : state.kind === "proxy" ? s.base_method === "actual" && +s.proxy : s.base_method === "actual" && !+s.proxy)) && (!state.q || s.commodity.toLowerCase().includes(state.q.toLowerCase())));
    $("#th-table").innerHTML = `<div class="tw tall"><table id="th-series"><caption class="sr-only">${esc(L("TrendX series and their 2024 base", "سلاسل TrendX وأساسها 2024"))}</caption><thead><tr><th scope="col">${esc(L("Commodity", "السلعة"))}</th><th scope="col">${esc(L("Category", "الفئة"))}</th><th scope="col">${esc(L("History", "التاريخ"))}</th><th scope="col">${esc(L("Source series", "سلسلة المصدر"))}</th><th scope="col" class="num">${esc(L("2024 mean", "متوسط 2024"))}</th><th scope="col" class="num">${esc(L("Latest (2024 = 100)", "الأحدث (2024 = 100)"))}</th><th scope="col"><span class="sr-only">${esc(L("Open", "فتح"))}</span></th></tr></thead><tbody>
      ${rows.map((s) => { const li = lastIdx(s.series_id); return `<tr${s.base_method !== "actual" ? ' class="muted-row"' : ""}><td><b>${esc(s.commodity)}</b><br><span class="muted ltr">${esc(s.unit)}</span></td><td>${esc(teCatName(s.category))}${+s.in_index ? "" : ` <span class="chip grey">${esc(L("not in index", "خارج المؤشر"))}</span>`}</td><td>${baseChip(s)}</td><td><span dir="auto">${esc(s.base_method === "actual" ? `${s.history_source}: ${s.history_series}${s.proxy_of ? ` (${L("proxy", "بديل")}: ${s.proxy_of})` : ""}` : s.conversion || "—")}</span></td><td class="num">${s.base_2024_mean !== "" ? fmtN(+s.base_2024_mean, 2) : "—"}</td><td class="num">${li ? `${fmtN(li[2], 1)}<br><span class="muted">${esc(fmtYM(li[0]))}</span>` : "—"}</td><td><button type="button" class="ghost" data-th="${esc(s.series_id)}">${esc(L("Open", "فتح"))}</button></td></tr>`; }).join("")}
      </tbody></table></div>`;
  };
  $("#th-kind").onchange = (e) => { state.kind = e.target.value; draw(); }; $("#th-cat").onchange = (e) => { state.cat = e.target.value; draw(); }; $("#th-q").oninput = (e) => { state.q = e.target.value; draw(); };
  $("#th-table").onclick = (e) => { const b = e.target.closest("[data-th]"); if (!b) return; const s = S.find((x) => x.series_id === b.dataset.th); if (s) teSeriesPanel(h, s); };
  draw();
}
function teSeriesPanel(h, s) {
  const o = h.obs[s.series_id] || [], real = o.filter((x) => !x[4]);
  openSidePanel(s.commodity, `<div class="stack">
    <div class="row">${baseChip(s)}${+s.in_index ? "" : chip(L("not in index", "خارج المؤشر"), "grey")}<span class="muted ltr">${esc(s.unit)}</span></div>
    <dl class="kv"><dt>${esc(L("Source", "المصدر"))}</dt><dd>${esc(s.base_method === "actual" ? `${s.history_source} — ${s.history_series} (${s.licence})` : L("none yet: carried back from the first collected price", "لا شيء بعد: مُثبّت من أول سعر مجموع"))}</dd>
      ${s.proxy_of ? `<dt>${esc(L("Proxy of", "بديل عن"))}</dt><dd>${esc(s.proxy_of)}</dd>` : ""}<dt>${esc(L("Conversion", "التحويل"))}</dt><dd>${esc(s.conversion || "—")}</dd>
      <dt>${esc(L("2024 mean", "متوسط 2024"))}</dt><dd>${s.base_2024_mean !== "" ? fmtN(+s.base_2024_mean, 4) : "—"} <span class="muted ltr">${esc(s.unit)}</span></dd>${s.link_month ? `<dt>${esc(L("Linked at", "موصول عند"))}</dt><dd>${esc(fmtYM(s.link_month))}</dd>` : ""}</dl>
    ${lineChart({ height: 220, title: s.commodity + " (2024 = 100)", xFmt: fmtYM, yFmt: (v) => v.toFixed(1), series: [{ label: L("2024 = 100", "2024 = 100"), points: (real.length ? real : o).map((x) => ({ x: x[0], y: x[2] })) }], empty: L("No real observations.", "لا مشاهدات حقيقية.") })}
    <div class="tw tall"><table><caption class="sr-only">${esc(s.commodity)}</caption><thead><tr><th scope="col">${esc(L("Month", "الشهر"))}</th><th scope="col" class="num">${esc(L("Value", "القيمة"))}</th><th scope="col" class="num">2024 = 100</th><th scope="col">${esc(L("Source", "المصدر"))}</th></tr></thead><tbody>
      ${o.slice().reverse().map((x) => `<tr${x[4] ? ' class="muted-row"' : ""}><td>${esc(fmtYM(x[0]))}</td><td class="num">${fmtN(x[1], 4)}</td><td class="num">${x[2] != null ? fmtN(x[2], 1) : "—"}</td><td>${x[4] ? chip(L("E · carried back", "E · مُثبّت"), "grey") : x[3] === "te" ? chip(L("our collection", "جمعنا") + (x[5] ? " · " + L("linked", "موصول") : ""), "blue") : chip(x[3] === "eia" ? "EIA" : L("World Bank", "البنك الدولي"), "ok")}</td></tr>`).join("")}
    </tbody></table></div></div>`, () => {});
}
function teHistorySheet(h) {
  const months = [...new Set(Object.values(h.obs).flat().map((x) => x[0]))].sort();
  return { title: "TrendX monthly, 2024 = 100", subtitle: `built ${h.built} • value_2024eq100 per series • E = carried back (excluded from modelling)`, headers: ["Commodity", "Category", "Unit", "History", "Source series", "2024 mean", ...months], widths: [22, 14, 14, 14, 40, 12, ...months.map(() => 10)], priceCols: [],
    rows: h.series.map((s) => { const m = Object.fromEntries((h.obs[s.series_id] || []).map((x) => [x[0], x])); return [s.commodity, s.category, s.unit, s.base_method === "actual" ? (+s.proxy ? "proxy" : "actual") : "carried back", s.history_series || "", s.base_2024_mean !== "" ? +s.base_2024_mean : null, ...months.map((ym) => m[ym] ? (m[ym][4] ? `E ${(+m[ym][2]).toFixed(2)}` : +(+m[ym][2]).toFixed(3)) : null)]; }) };
}
