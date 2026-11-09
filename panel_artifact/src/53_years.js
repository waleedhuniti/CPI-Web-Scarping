
// ============================================================ Years & Months: accordion of years, then months (derived from run dates)
const FRESH_GROUPS = ["0112", "0113", "0116", "0117"];
function pgYears(r, seq) {
  const pid = r.pid;
  $("#page").innerHTML = titleRow(L("Years & Months", "السنوات والأشهر"), `<button class="primary" type="button" id="ym-create" aria-expanded="false" aria-controls="ym-form">${ico("plus")}${esc(L("Create Year", "إنشاء سنة"))}</button>`)
    + `<form class="card" id="ym-form" hidden novalidate><label class="f" style="max-width:220px"><span>${esc(L("Year (yyyy)", "السنة (yyyy)"))}</span><input id="ym-year" inputmode="numeric" maxlength="4" dir="ltr" aria-describedby="ym-err"></label><p class="f-err" id="ym-err" hidden></p>
      <div class="row"><button class="primary" type="submit">${esc(L("Save year", "حفظ السنة"))}</button><button type="button" id="ym-cancel">${esc(L("Cancel", "إلغاء"))}</button></div></form>
    <section class="card"><div class="row" style="justify-content:space-between"><span class="muted" id="ym-count">— ${esc(L("years", "سنوات"))}</span><button class="sq" type="button" id="ym-refresh" aria-label="${esc(L("Refresh", "تحديث"))}" title="${esc(L("Refresh", "تحديث"))}">${ico("refresh")}</button></div>
      <div id="ym-list">${loadingHtml(L("Loading years…", "تُحمَّل السنوات…"))}</div></section>`;
  const form = $("#ym-form");
  $("#ym-create").onclick = () => { form.hidden = !form.hidden; $("#ym-create").setAttribute("aria-expanded", String(!form.hidden)); if (!form.hidden) { $("#ym-year").value = todayDubai().slice(0, 4); $("#ym-year").focus(); } };
  $("#ym-cancel").onclick = () => { form.hidden = true; $("#ym-create").setAttribute("aria-expanded", "false"); $("#ym-create").focus(); };
  form.onsubmit = async (e) => {
    e.preventDefault();
    const y = $("#ym-year").value.trim(), err = $("#ym-err");
    const bad = !/^20\d\d$/.test(y) ? L("Write a year such as 2027.", "اكتب سنة مثل 2027.") : (st(pid).years || []).includes(y) ? L("This year already exists.", "هذه السنة موجودة.") : "";
    err.hidden = !bad; err.textContent = bad; if (bad) return;
    try { await db.doc(`projects/${pid}/years/${y}`).set({ year: +y, created_at: new Date().toISOString() }); toast(L(`Year ${y} created`, `أُنشئت السنة ${y}`)); delete st(pid).yearDocs; form.hidden = true; drawYears(pid, seq); }
    catch (x) { err.hidden = false; err.textContent = dbErr(x); }
  };
  $("#ym-refresh").onclick = () => { delete st(pid).yearDocs; if (S[pid]) { S[pid].runs = null; S[pid].teDays = null; } if (pid === "sppi") sppiCache = null; drawYears(pid, seq); };
  drawYears(pid, seq);
}
async function yearDocs(pid) { const s = st(pid); if (!s.yearDocs) { try { s.yearDocs = (await db.collection(`projects/${pid}/years`).get()).docs.map((d) => d.id); } catch (e) { s.yearDocs = []; } } return s.yearDocs; }
async function drawYears(pid, seq) {
  const box = $("#ym-list");
  let months = [], monthRow, extra = "";
  try {
    const ydocs = await yearDocs(pid);
    if (pid === "sppi") {
      const d = await sppiLoad();
      months = d.meta ? [...new Set([...d.periods.map((p) => p.month), ...d.weeks.map((w) => w.month)])].sort() : [];
      monthRow = (m) => ymSppiMonth(d, m);
      if (d.meta) { const tbd = d.items.filter((i) => i.status !== "retired" && i.collection?.lead_days == null);
        extra = `<details class="acc"><summary>${ico("chevr", "chev flip")}${esc(L(`Timing: to be determined for ${tbd.length} of ${d.items.filter((i) => i.status !== "retired").length} items`, `التوقيت: يُحدد لاحقاً لـ ${tbd.length} من ${d.items.filter((i) => i.status !== "retired").length} بنداً`))}</summary><div class="acc-body"><p class="muted" style="margin:0">${esc(L("Collected monthly; the collection timing of each item is still to be determined.", "الجمع شهري؛ توقيت جمع كل بند لم يُحدد بعد."))}</p><ul style="margin:0;columns:2">${tbd.map((i) => `<li><span class="mono">${esc(i.code)}</span> ${esc(sppiName(i))}: ${esc(L("Timing: to be determined", "التوقيت: يُحدد لاحقاً"))}</li>`).join("")}</ul></div></details>`; }
    } else if (pid === "cpi") {
      const list = await ensureRuns("cpi"), dr = dayRunsOf(list);
      months = [...new Set(list.map((x) => runDay(x).slice(0, 7)))].sort();
      monthRow = (m) => ymCpiMonth(list, dr, m);
    } else {
      const days = await teDays();
      months = [...new Set(days.map((x) => x.day.slice(0, 7)))].sort();
      monthRow = (m) => ymTeMonth(days, m, months);
    }
    st(pid).years = [...new Set([...months.map((m) => m.slice(0, 4)), ...ydocs])].sort();
  } catch (e) { if (alive(seq)) { box.innerHTML = errBox(L("Unable to load years and months right now. ", "تعذّر تحميل السنوات والأشهر الآن. ") + dbErr(e), "ym-retry"); bindRetry(); } return; }
  if (!alive(seq)) return;
  const years = st(pid).years;
  $("#ym-count").textContent = years.length ? L(`${years.length} years`, `${years.length} سنوات`) : L("No data yet", "لا بيانات بعد");
  if (!years.length) { box.innerHTML = emptyHtml("calendar", L("No data yet", "لا بيانات بعد"), L("Years appear from the run dates, or create one.", "تظهر السنوات من تواريخ التشغيل، أو أنشئ واحدة.")); return; }
  box.innerHTML = `<div id="ym-list-in">${years.slice().reverse().map((y, yi) => { const ms = months.filter((m) => m.startsWith(y)).reverse();
    return `<details class="acc"${yi === 0 ? " open" : ""}><summary>${ico("chevr", "chev flip")}<span style="font-size:18px">${esc(y)}</span><span class="muted">${esc(L(`${ms.length} months`, `${ms.length} أشهر`))}</span></summary><div class="acc-body">${ms.map(monthRow).join("") || `<p class="muted" style="margin:0">${esc(L("No collection in this year yet.", "لا جمع في هذه السنة بعد."))}</p>`}</div></details>`; }).join("")}${extra}</div>`;
  box.onclick = (e) => {
    const c = e.target.closest("[data-check]"); if (c) return ymCheck(c.dataset.check, c);
    const x = e.target.closest("[data-dl]"); if (x) { const m = x.dataset.dl; return exportAllRuns(st("cpi").runs.filter((rr) => runDay(rr).startsWith(m)), `CPI ${m} - all prices.xlsx`, x); }
    const t = e.target.closest("[data-te-report]"); if (t) return teMonthReport(t.dataset.teReport, t);
  };
}
const ymStatusChip = (s) => chip(s[0], s[1]);
function ymCpiMonth(list, dr, m) {
  const today = todayDubai(), first = dr.days[0]?.day || m + "-01";
  const start = first > m + "-01" ? first : m + "-01", end = monthEnd(m) < today ? monthEnd(m) : today;
  const period = start <= end ? calDays(start, end) : [];
  const have = new Map(dr.days.filter((x) => x.day.startsWith(m)).map((x) => [x.day, x.run]));
  const mRuns = list.filter((x) => runDay(x).startsWith(m));
  const missing = period.filter((d) => !have.has(d)), dups = mRuns.filter((x) => dr.dup.has(x.id));
  const seen = mRuns.reduce((n, x) => n + cpiSeen(x), 0);
  const blocked = {}; for (const [d, run] of have) for (const k of cpiBlockedSet(run)) (blocked[k] ??= []).push(d);
  const partialDays = [...have].filter(([, run]) => runStatus("cpi", run).code !== "completed" && runStatus("cpi", run).code !== "warnings").length;
  const ended = monthEnd(m) < today;
  const status = !ended ? [L("Open", "مفتوح"), "blue"] : missing.length || partialDays ? [L("Partial", "جزئي"), "warn"] : [L("Complete", "مكتمل"), "ok"];
  const strip = period.map((d) => { const run = have.get(d), code = run ? runStatus("cpi", run).code : null; return `<i class="${!run ? "n" : code === "completed" || code === "warnings" ? "g" : "a"}" title="${esc(`${fmtDay(d)}: ${!run ? L("no run", "لا تشغيل") : L(RUNST[code][0], RUNST[code][1])}`)}">${+d.slice(8)}</i>`; }).join("");
  return `<details class="acc" id="ym-${m}"><summary>${ico("chevr", "chev flip")}<span>${esc(fmtMonthLong(m))}</span><span class="muted">${esc(L(`${have.size} of ${period.length} days`, `${have.size} من ${period.length} يوماً`))}</span>${ymStatusChip(status)}<span class="muted">${esc(L(`${mRuns.length} runs · ${fmtN(seen)} seen prices`, `${mRuns.length} تشغيلاً · ${fmtN(seen)} سعراً مرئياً`))}</span></summary>
    <div class="acc-body"><div class="daystrip" role="img" aria-label="${esc(L(`Days of ${fmtMonthLong(m)}: green read, amber partial or blocked, grey no run`, `أيام ${fmtMonthLong(m)}: الأخضر مقروء، والبرتقالي جزئي أو محجوب، والرمادي بلا تشغيل`))}">${strip}</div>
      <dl class="kv"><dt>${esc(L("Days collected", "أيام الجمع"))}</dt><dd>${esc(L(`${have.size} of ${period.length} (from ${fmtDay(start)})`, `${have.size} من ${period.length} (من ${fmtDay(start)})`))}</dd>
        <dt>${esc(L("Missing days", "أيام ناقصة"))}</dt><dd>${esc(missing.map((d) => fmtDay(d)).join(", ") || L("none", "لا شيء"))}</dd>
        <dt>${esc(L("Runs", "التشغيلات"))}</dt><dd>${fmtN(mRuns.length)}${dups.length ? " · " + esc(L(`duplicate: ${dups.map((x) => `${fmtDay(runDay(x))} ${fmtTimeDubai(x.startedAt)}`).join(", ")} (the latest finished run of that day counts)`, `مكرر: ${dups.map((x) => `${fmtDay(runDay(x))} ${fmtTimeDubai(x.startedAt)}`).join("، ")} (يُحتسب آخر تشغيل منتهٍ في ذلك اليوم)`)) : ""}</dd>
        <dt>${esc(L("Seen prices", "أسعار مرئية"))}</dt><dd>${fmtN(seen)}</dd>
        <dt>${esc(L("Blocked days", "أيام محجوبة"))}</dt><dd>${Object.keys(blocked).length ? Object.entries(blocked).map(([k, ds]) => esc(`${outletEn(k)}: ${ds.sort().map((d) => +d.slice(8)).join(", ")}`)).join("; ") : esc(L("none", "لا شيء"))}</dd></dl>
      <div class="row"><button type="button" data-check="${m}">${ico("check")}${esc(L("Check completeness", "افحص الاكتمال"))}</button><button type="button" data-dl="${m}">${ico("download")}${esc(L("Download month for Dataiku", "تنزيل الشهر لـ Dataiku"))}</button><span class="muted">${esc(L("m/m comparison: not shown in v1", "المقارنة الشهرية: غير معروضة في هذه النسخة"))}</span></div>
      <div id="ym-check-${m}" aria-live="polite"></div></div></details>`;
}
// completeness (on demand): reads the month's rows; ≥1 observation in days 1-15 and in 16-end; fresh items need a span > 7 days;
// non-fresh items seen on fewer than 3 days are low-coverage
async function ymCheck(m, btn) {
  const out = $("#ym-check-" + m); btn.disabled = true;
  try {
    const { days } = dayRunsOf(await ensureRuns("cpi")), b = await ensureBasket("cpi"), md = days.filter((x) => x.day.startsWith(m));
    const seenDays = new Map();
    for (let i = 0; i < md.length; i++) {
      out.innerHTML = loadingHtml(L(`Reading run ${i + 1} of ${md.length}…`, `يُقرأ التشغيل ${i + 1} من ${md.length}…`));
      const run = md[i].run, rows = annotateRows("cpi", run, await runRows("cpi", run));
      for (const x of rows) if (x.accepted === "yes" && x.obs_state === "seen") (seenDays.get(x.item_code) || seenDays.set(x.item_code, new Set()).get(x.item_code)).add(md[i].day);
    }
    let usable = 0, missing = 0, low = 0, half = 0;
    const want = b.filter((i) => i.match_mode !== "service" && i.match_mode !== "market");
    for (const it of want) {
      const ds = [...(seenDays.get(it.item_code) || [])].sort();
      if (!ds.length) { missing++; continue; }
      const h1 = ds.some((d) => +d.slice(8) <= 15), h2 = ds.some((d) => +d.slice(8) >= 16), fresh = FRESH_GROUPS.includes(it.group_code);
      if (!fresh && ds.length < 3) { low++; continue; }
      if (h1 && h2 && (!fresh || daySpan(ds[0], ds[ds.length - 1]) > 7)) usable++; else half++;
    }
    out.innerHTML = `<div class="kpis four">${kpiHtml({ id: `ym-u-${m}`, icon: "check", tint: "green", label: L("Usable", "صالح"), value: fmtN(usable) })}${kpiHtml({ id: `ym-m-${m}`, icon: "ban", tint: "red", label: L("Missing", "ناقص"), value: fmtN(missing) })}${kpiHtml({ id: `ym-l-${m}`, icon: "warn", tint: "amber", label: L("Low coverage", "تغطية منخفضة"), value: fmtN(low) })}${kpiHtml({ id: `ym-h-${m}`, icon: "calendar", label: L("One half only", "نصف شهر فقط"), value: fmtN(half) })}</div>
      <p class="muted" style="margin:0">${esc(L(`${fmtN(want.length)} priced basket lines (services and market prices excluded); ${md.length} daily runs read; carried rows of blocked outlets are not observations.`, `${fmtN(want.length)} بنداً مسعّراً (دون الخدمات وأسعار السوق)؛ قُرئ ${md.length} تشغيلاً يومياً؛ الصفوف المنقولة للمنافذ المحجوبة ليست ملاحظات.`))}</p>`;
  } catch (e) { out.innerHTML = errBox(dbErr(e)); }
  finally { btn.disabled = false; }
}
function ymTeMonth(days, m, months) {
  const today = todayDubai(), first = days[0]?.day || m + "-01";
  const start = first > m + "-01" ? first : m + "-01", end = monthEnd(m) < today ? monthEnd(m) : today;
  const period = start <= end ? calDays(start, end) : [], md = days.filter((x) => x.day.startsWith(m)), have = new Set(md.map((x) => x.day));
  const missing = period.filter((d) => !have.has(d)), ended = monthEnd(m) < today;
  const recs = md.reduce((n, x) => n + x.rows.length, 0), stale = md.reduce((n, x) => n + x.rows.filter((r) => r.price_date && daySpan(r.price_date, x.day) > 7).length, 0);
  const all = teMonthly(teIndex(days), m), cats = TE_CATS.map((c) => [c, teMonthly(teIndex(days, c), m)]);
  const status = !ended ? [L(`Open: provisional, ${md.length} days`, `مفتوح: مؤقت، ${md.length} يوماً`), "blue"] : missing.length ? [L("Complete with gaps", "مكتمل مع فجوات"), "warn"] : [L("Complete", "مكتمل"), "ok"];
  const prevM = months[months.indexOf(m) - 1];
  const mm = prevM ? (ended ? (() => { const p = teMonthly(teIndex(days), prevM); return p.mean ? L(`${fmtMonth(m)} vs ${fmtMonth(prevM)}: ${((all.mean / p.mean - 1) * 100).toFixed(2)}%`, `${fmtMonth(m)} مقابل ${fmtMonth(prevM)}: ${((all.mean / p.mean - 1) * 100).toFixed(2)}%`) : ""; })() : L("Not comparable yet: provisional", "غير قابل للمقارنة بعد: مؤقت")) : "";
  const strip = period.map((d) => `<i class="${have.has(d) ? "g" : "n"}" title="${esc(`${fmtDay(d)}: ${have.has(d) ? L("run", "تشغيل") : L("no run", "لا تشغيل")}`)}">${+d.slice(8)}</i>`).join("");
  return `<details class="acc" id="ym-${m}"><summary>${ico("chevr", "chev flip")}<span>${esc(fmtMonthLong(m))}</span><span class="muted">${esc(L(`${have.size} of ${period.length} days`, `${have.size} من ${period.length} يوماً`))}</span>${ymStatusChip(status)}<span class="muted">${esc(L(`monthly index ${all.mean?.toFixed(2) ?? "—"}`, `المؤشر الشهري ${all.mean?.toFixed(2) ?? "—"}`))}</span></summary>
    <div class="acc-body"><div class="daystrip" role="img" aria-label="${esc(L(`Days of ${fmtMonthLong(m)}: green run, grey no run`, `أيام ${fmtMonthLong(m)}: الأخضر تشغيل، والرمادي بلا تشغيل`))}">${strip}</div>
      <dl class="kv"><dt>${esc(L("Days", "الأيام"))}</dt><dd>${esc(L(`${have.size} of ${period.length} (from ${fmtDay(start)})`, `${have.size} من ${period.length} (من ${fmtDay(start)})`))}</dd><dt>${esc(L("Missing days", "أيام ناقصة"))}</dt><dd>${esc(missing.map((d) => fmtDay(d)).join(", ") || L("none", "لا شيء"))}</dd>
        <dt>${esc(L("Runs", "التشغيلات"))}</dt><dd>${fmtN(md.length)}</dd><dt>${esc(L("Records", "السجلات"))}</dt><dd>${fmtN(recs)}</dd><dt>${esc(L("Stale quotes (> 7 days)", "تسعيرات قديمة (> 7 أيام)"))}</dt><dd>${fmtN(stale)}</dd>
        <dt>${esc(L("Monthly index (mean of daily)", "المؤشر الشهري (متوسط الأيام)"))}</dt><dd><b>${all.mean?.toFixed(2) ?? "—"}</b> · ${cats.map(([c, v]) => `${esc(teCatName(c))} ${v.mean?.toFixed(2) ?? "—"}`).join(" · ")}</dd>
        ${mm ? `<dt>m/m</dt><dd>${esc(mm)}</dd>` : ""}</dl>
      <div class="row"><button type="button" data-te-report="${m}">${ico("download")}${esc(L("Monthly report (Excel)", "التقرير الشهري (Excel)"))}</button></div></div></details>`;
}
// the TrendX monthly report: Monthly, Daily index, All Days prices, Notes (built in the browser from the shared index)
async function teMonthReport(m, btn) {
  if (!downloads) return toast(L("Downloads are not available in this view", "التنزيل غير متاح في هذا العرض"), true);
  const old = btn.innerHTML; btn.disabled = true; btn.textContent = L("Preparing…", "يُجهَّز…");
  try {
    const days = await teDays(), md = days.filter((x) => x.day.startsWith(m)), ExcelJS = await loadExcel(), wb = new ExcelJS.Workbook();
    const head = (ws, cols) => { ws.addRow(cols); const r = ws.getRow(1); r.font = { bold: true, color: { argb: "FFFFFFFF" } }; r.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF1B2A52" } }; ws.views = [{ state: "frozen", ySplit: 1 }]; cols.forEach((_, i) => (ws.getColumn(i + 1).width = i < 3 ? 22 : 14)); };
    const mon = wb.addWorksheet("Monthly"); head(mon, ["Category", "Commodity", "Unit", "Monthly mean", "Days", "% change (first to last day)", "In index"]);
    const by = new Map(); for (const d of md) for (const x of d.rows) { const k = teKey(x); if (!by.has(k)) by.set(k, { x, ps: [] }); by.get(k).ps.push(Number(x.price)); }
    for (const { x, ps } of [...by.values()].sort((a, b) => a.x.category.localeCompare(b.x.category) || a.x.commodity.localeCompare(b.x.commodity))) mon.addRow([x.category, x.commodity, x.unit, +meanOf(ps).toFixed(4), ps.length, ps.length > 1 ? +((ps[ps.length - 1] / ps[0] - 1) * 100).toFixed(3) : null, TE_EXCL.includes(x.category) ? "no" : "yes"]);
    const di = wb.addWorksheet("Daily index"); const sers = ["All", ...TE_CATS].map((c) => [c, teIndex(days, c)]); head(di, ["Date", ...sers.map(([c]) => c)]);
    for (const d of md) di.addRow([d.day, ...sers.map(([, s]) => +((s.find((p) => p.x === d.day)?.y) ?? 0).toFixed(4))]);
    di.addRow([]); di.addRow(["Monthly mean", ...sers.map(([, s]) => +(teMonthly(s, m).mean ?? 0).toFixed(4))]);
    const ad = wb.addWorksheet("All Days prices"); head(ad, ["run_date", "price_date", "Category", "Commodity", "Unit", "Price", "Change", "Change %", "collected_dubai"]);
    for (const d of md) for (const x of d.rows) ad.addRow([d.day, x.price_date || "", x.category, x.commodity, x.unit, Number(x.price), x.change ?? null, x.pct ?? null, dubaiDT(d.run.startedAt)]);
    const nt = wb.addWorksheet("Notes"); head(nt, ["Item", "Value"]);
    const all = days.length ? calDays(days[0].day > m + "-01" ? days[0].day : m + "-01", monthEnd(m) < todayDubai() ? monthEnd(m) : todayDubai()) : [];
    [["Method", "Chained Jevons on the run date: geometric mean of price relatives of commodities priced on both consecutive run days"], ["Base", `${teBaseLabel()}${teLink?.ok ? ` (daily index linked to the monthly history at ${teLink.month})` : " (stands for September)"}`], ["Monthly", "Mean of the daily index values of the month"],
      ["Exclusions", TE_EXCL.join(", ")], ["Missing days", all.filter((d) => !md.some((x) => x.day === d)).join(", ") || "none"], ["Stale quotes", "Shown as published; price_date kept per row"], ["Source", "Trading Economics commodities page"]].forEach((r) => nt.addRow(r));
    const buf = await wb.xlsx.writeBuffer();
    await downloads.save({ filename: `TrendX monthly report ${m}.xlsx`, data: new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }) });
  } catch (e) { if (e?.code !== "cancelled" && e?.code !== "declined") toast(e?.message || String(e), true); }
  finally { btn.disabled = false; btn.innerHTML = old; }
}
function ymSppiMonth(d, m) {
  const ws = d.weeks.filter((w) => w.month === m), per = d.periods.find((p) => p.month === m);
  const exp = { tickets: sppiExpected("tickets"), packages: sppiExpected("packages") };
  const done = ws.length && ws.every((w) => w.status === "complete");
  const status = done ? [L("Complete", "مكتمل"), "ok"] : [L("Open", "مفتوح"), "blue"];
  return `<details class="acc" id="ym-${m}" open><summary>${ico("chevr", "chev flip")}<span>${esc(per ? L(per.label_en || fmtMonth(m), per.label_ar || fmtMonth(m)) : fmtMonth(m))}</span><span class="muted">${esc(L(`${ws.length} collections`, `${ws.length} مرات جمع`))}</span>${ymStatusChip(status)}</summary>
    <div class="acc-body"><div class="tw"><table><thead><tr><th scope="col">${esc(L("Collection", "الجمع"))}</th><th scope="col">${esc(L("Ticket window", "فترة التذاكر"))}</th><th scope="col">${esc(L("Package window", "فترة الباقات"))}</th><th scope="col">${esc(L("Collected on", "تاريخ الجمع"))}</th><th scope="col" class="num">${esc(L("Tickets priced / expected", "التذاكر المسعّرة / المتوقعة"))}</th><th scope="col" class="num">${esc(L("Packages priced / expected", "الباقات المسعّرة / المتوقعة"))}</th><th scope="col">${esc(L("Blocked", "محجوب"))}</th><th scope="col">${esc(L("Status", "الحالة"))}</th></tr></thead><tbody>
      ${ws.map((w) => { const rs = sppiActiveRows(w.id), pr = (sv) => rs.filter((x) => x.survey === sv && (x.status === "ok" || x.source === "manual") && hasPrice(x)).length, bl = [...new Set(rs.filter((x) => x.status === "blocked").map((x) => sppiName(sppiOutlet(x.outlet)) || x.outlet))];
        return `<tr><th scope="row">${esc(sppiWeekLabel(w))}</th><td>${esc(fmtDay(w.tickets?.out))} → ${esc(fmtDay(w.tickets?.back))}</td><td>${esc(fmtDay(w.packages?.checkin))}–${esc(fmtDay(w.packages?.checkout))}</td><td>${esc(fmtDay(w.collected_on))}</td><td class="num">${pr("tickets")} / ${exp.tickets}</td><td class="num">${pr("packages")} / ${exp.packages}</td><td>${esc(bl.join(", ") || "—")}</td><td>${w.status === "complete" ? chip(L("Complete", "مكتمل"), "ok") : chip(L("Open", "مفتوح"), "blue")}</td></tr>`; }).join("")}</tbody></table></div>
      ${d.files?.length ? `<p style="margin:0"><b>${esc(L("Office workbooks: ", "ملفات المكتب: "))}</b>${d.files.map((f) => `<a href="/_blob/${esc(f.asset)}" target="_blank" rel="noopener">${esc(f.label || f.asset)}</a>`).join(" · ")}</p>` : ""}
      <p class="muted" style="margin:0">${esc(L("No SPPI index in v1; m/m not shown.", "لا مؤشر SPPI في هذه النسخة؛ المقارنة الشهرية غير معروضة."))}</p></div></details>`;
}
