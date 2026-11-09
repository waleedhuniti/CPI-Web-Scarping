
// ============================================================ Dashboard (31.png, 32.png)
const TREND_TITLE = { cpi: ["Internal price monitor (12 Oct = 100), not the CPI", "مؤشر أسعار داخلي (12 أكتوبر = 100)، ليس الرقم القياسي لأسعار المستهلك"], te: ["TrendX Index (2 Oct 2026 = 100)", "مؤشر TrendX (2 أكتوبر 2026 = 100)"] };
function pgDashboard(r, seq) {
  const pid = r.pid, p = routeOf(pid);
  const kp = (id, icon, tint, label, href) => kpiHtml({ id: "db-kpi-" + id, icon, tint, label, href, value: "—" });
  $("#page").innerHTML = `<h1 class="sr-only">${esc(pageName("dashboard"))} · ${esc(projLabel(pid))}</h1>
    <div class="kpis dash">
      ${kp("outlets", "store", "", L("Total Outlets", "إجمالي المنافذ"), `#${p}-outlets`)}
      ${kp("commodities", "box", "", L("Commodities Tracked", "السلع المتابَعة"), `#${p}-price-history/commodities`)}
      ${kp("records", "records", "", L("Price Records", "سجلات الأسعار"), `#${p}-price-logs`)}
      ${kp("scrapers", "gear", "", L("Active Scrapers", "الكاشطات الفعّالة"), `#${p}-scrapers`)}
    </div>
    <section class="card" id="db-trend" aria-labelledby="db-trend-h"><div class="card-h"><h2 id="db-trend-h">${esc(pid === "sppi" ? L("Collections", "مرات الجمع") : L(TREND_TITLE[pid][0], TREND_TITLE[pid][1]))}</h2><span class="spacer"></span><span id="db-trend-chip"></span></div><div id="db-trend-body">${loadingHtml(L("Loading…", "يُحمَّل…"))}</div></section>
    <section class="card" id="db-latest" aria-labelledby="db-latest-h"><div class="card-h"><h2 id="db-latest-h">${esc(L("Latest collection", "آخر جمع"))}</h2><span class="spacer"></span><span id="db-latest-chip"></span></div><div id="db-latest-body">${loadingHtml(L("Loading…", "يُحمَّل…"))}</div></section>
    <section class="card" id="db-donut" aria-labelledby="db-donut-h"><div class="card-h"><h2 id="db-donut-h">${esc(pid === "cpi" ? L("Basket composition", "تكوين السلة") : L("Commodity distribution", "توزيع السلع"))}</h2><span class="spacer"></span><span id="db-donut-tools"></span></div><div id="db-donut-body">${loadingHtml(L("Loading…", "يُحمَّل…"))}</div></section>
    <section class="card" id="db-activity" aria-labelledby="db-activity-h"><div class="card-h"><h2 id="db-activity-h">${esc(L("Recent Activity", "النشاط الأخير"))}</h2></div><div id="db-activity-body">${loadingHtml(L("Loading…", "يُحمَّل…"))}</div><p style="margin:0"><a class="link-btn" style="font-size:15px" href="#${p}-price-logs">${esc(L("View all in Price Logs", "عرض الكل في سجل التشغيلات"))} ${ico("chevr", "flip")}</a></p></section>
    ${pid === "cpi" ? `<details class="card" id="db-internal"><summary>${esc(L("Index by group (COICOP 2018) · Internal", "المؤشر حسب المجموعة (COICOP 2018) · داخلي"))}</summary><div id="db-internal-body"></div></details>` : ""}
    ${pid === "te" ? `<p class="notice info" id="db-te-note" style="margin:0">${esc(L("The public site (build_pages_site.py) still includes Electricity in its index; this page leaves Electricity and Index out.", "الموقع العام (build_pages_site.py) ما زال يُدخل الكهرباء في مؤشره؛ هذه الصفحة تستبعد الكهرباء والمؤشرات."))}</p>` : ""}`;
  const fail = (box, e) => { const b = document.getElementById(box); if (b && alive(seq)) b.innerHTML = errBox(L("Unable to load this data right now. ", "تعذّر تحميل هذه البيانات الآن. ") + dbErr(e), box + "-retry"); bindRetry(); };
  activeScraperCount(pid).then((n) => alive(seq) && setKpi("db-kpi-scrapers", pid === "sppi" && !n && !sppiCache?.meta ? "—" : fmtN(n), pid === "sppi" && !n && !sppiCache?.meta ? L("No data yet", "لا بيانات بعد") : L("routine collectors and active custom scrapers", "المهام المجدولة والكاشطات المخصصة الفعّالة"))).catch(() => {});
  if (pid === "cpi") dashCpi(seq, fail); else if (pid === "te") dashTe(seq, fail); else dashSppi(seq, fail);
}

// ---------------- CPI
async function dashCpi(seq, fail) {
  let L0;
  try { L0 = await cpiLatest(); } catch (e) { return ["db-latest-body", "db-activity-body", "db-trend-body"].forEach((b) => fail(b, e)); }
  if (!alive(seq)) return;
  const { list, days, last, rows } = L0;
  const outs = await outletRows("cpi"); if (!alive(seq)) return;
  setKpi("db-kpi-outlets", fmtN(outs.length), L("Outlets page rows", "صفوف صفحة المنافذ"));
  const b = await ensureBasket("cpi"); if (!alive(seq)) return;
  const priced = new Set(rows.filter((x) => x.accepted === "yes" && x.obs_state === "seen").map((x) => x.item_code)).size;
  setKpi("db-kpi-commodities", fmtN(b.length), L(`${fmtN(priced)} priced in latest run`, `${fmtN(priced)} مسعّرة في آخر تشغيل`));
  const total = list.reduce((n, x) => n + cpiSeen(x), 0);
  setKpi("db-kpi-records", fmtN(total), L(`seen in all ${list.length} runs`, `مرئية في كل التشغيلات (${list.length})`), last ? cpiSeen(last) : null, L("latest run", "آخر تشغيل"));
  // trend: the internal monitor, built on request (it reads the rows of every run)
  const tb = $("#db-trend-body");
  $("#db-trend-chip").innerHTML = days.length ? chip(`${fmtDay(days[0].day)} – ${fmtDay(days[days.length - 1].day)}`, "blue") : "";
  if (st("cpi").monitor) drawCpiMonitor(st("cpi").monitor);
  else tb.innerHTML = `<p class="muted" style="margin:0">${esc(L(`Chained Jevons over item–shop pairs seen on both consecutive run days (exact matches only, regular price, carried rows and blocked outlets excluded). It reads the saved rows of ${days.length} runs, so it loads on request and stays for this session.`, `جيفونز متسلسل لأزواج البند والمتجر المرئية في يومي تشغيل متتاليين (مطابقات دقيقة فقط، السعر العادي، دون الصفوف المنقولة والمنافذ المحجوبة). يقرأ صفوف ${days.length} تشغيلاً، لذلك يُحمَّل عند الطلب ويبقى لهذه الجلسة.`))}</p><div class="row"><button class="primary" type="button" id="db-monitor-load">${ico("chart")}${esc(L("Build the monitor", "ابنِ المؤشر"))}</button><span class="muted" id="db-monitor-prog" role="status" aria-live="polite"></span></div>`;
  $("#db-monitor-load")?.addEventListener("click", async (e) => {
    e.currentTarget.disabled = true;
    try { const m = await cpiMonitor((i, n) => { const pr = $("#db-monitor-prog"); if (pr) pr.textContent = L(`Reading run ${i} of ${n}…`, `يُقرأ التشغيل ${i} من ${n}…`); }); if (alive(seq)) drawCpiMonitor(m); }
    catch (x) { fail("db-trend-body", x); }
  });
  // latest collection: outlet x source
  const cat = await catalogueLatest(); if (!alive(seq)) return;
  if (!last) { $("#db-latest-body").innerHTML = emptyHtml("file", L("No runs yet", "لا تشغيلات بعد"), ""); }
  else {
    const ls = cpiLogStates(last), sm = last.summary || {};
    const line = (label, pages, acc, stHtml) => `<tr><th scope="row">${esc(label)}</th><td class="num">${pages}</td><td class="num">${acc}</td><td>${stHtml}</td></tr>`;
    const tr = [];
    for (const k of ["carrefour", "lulu"]) {
      const x = ls[k], nm = outletEn(k).split(" ")[0], bc = sm[`${k}_barcode`], ct = sm[`${k}_category`], cats = (x?.cats || []).reduce((a, c) => [a[0] + c.products, a[1] + c.pages], [0, 0]);
      tr.push(line(`${nm} ${L("barcode", "باركود")}`, x ? `${fmtN(x.read)} / ${fmtN(x.failed)}` : "—", bc ? `${fmtN(bc.accepted)} / ${fmtN(bc.lines)}` : "—", stateChip(x?.state || "notread", cpiReason(x, k))));
      tr.push(line(`${nm} ${L("category", "أقسام")}`, x?.cats?.length ? L(`${fmtN(cats[0])} products / ${fmtN(cats[1])} pages`, `${fmtN(cats[0])} منتج / ${fmtN(cats[1])} صفحة`) : "—", ct ? `${fmtN(ct.accepted)} / ${fmtN(ct.lines)}` : "—",
        x?.state === "blocked" ? `${chip(L("Blocked (carried)", "محجوب (منقول)"), "bad")} <span class="muted">${esc(L(`${fmtN(ct?.accepted)} rows carried forward, not prices`, `${fmtN(ct?.accepted)} صفاً منقولاً، ليست أسعاراً`))}</span>` : stateChip(x?.state || "notread")));
    }
    const catRows = rows.filter((x) => x.source === "catalogue"), ns = rows.filter((x) => x.source === "name_search");
    tr.push(line(L("Catalogue stores", "متاجر الكتالوج"), cat ? L(`${fmtN(cat.rows)} products (${fmtDay(cat.date)})`, `${fmtN(cat.rows)} منتج (${fmtDay(cat.date)})`) : "—", `${fmtN(catRows.filter((x) => x.accepted === "yes").length)} / ${fmtN(catRows.length)}`, stateChip(cat ? "ok" : "notread")));
    tr.push(line(L("Name search", "البحث بالاسم"), "—", `${fmtN(ns.filter((x) => x.accepted === "yes").length)} / ${fmtN(ns.length)}`, stateChip(ns.length ? "ok" : "notread")));
    $("#db-latest-chip").innerHTML = runChip(runStatus("cpi", last)) + " " + chip(L(`${fmtDay(runDay(last))} ${fmtTimeDubai(last.startedAt)} Dubai`, `${fmtDay(runDay(last))} ${fmtTimeDubai(last.startedAt)} دبي`), "grey");
    $("#db-latest-body").innerHTML = `<div class="tw"><table><thead><tr><th scope="col">${esc(L("Outlet · source", "المنفذ · المصدر"))}</th><th scope="col" class="num">${esc(L("Pages read / failed", "صفحات مقروءة / فاشلة"))}</th><th scope="col" class="num">${esc(L("Accepted / lines", "مقبول / بنود"))}</th><th scope="col">${esc(L("State", "الحالة"))}</th></tr></thead><tbody>${tr.join("")}</tbody></table></div>
      <p class="muted" style="margin:0">${esc(L(`Seen prices ${fmtN(cpiSeen(last))} of ${fmtN(last.count)} rows; ${fmtN(cpiCarried(last))} carried rows of blocked outlets are not prices.`, `أسعار مرئية ${fmtN(cpiSeen(last))} من ${fmtN(last.count)} صفاً؛ ${fmtN(cpiCarried(last))} صفاً منقولاً لمنافذ محجوبة ليست أسعاراً.`))}</p>`;
  }
  // donut: basket by COICOP division, or by collection method
  const drawDonut = (mode) => {
    let items;
    if (mode === "method") { const ml = MODE_LABEL(); items = ["barcode", "spec", "name", "service", "market"].map((m) => ({ label: ml[m], value: b.filter((i) => i.match_mode === m).length })); }
    else {
      const c = {}; for (const i of b) { const k = i.division_code || "??"; c[k] = (c[k] || 0) + 1; }
      const all = Object.entries(c).sort((a, b) => b[1] - a[1]).map(([k, v]) => ({ label: `${k} ${LANG === "ar" ? (b.find((i) => i.division_code === k)?.division_name || k) : DIV_EN[k] || k}`, value: v }));
      items = all.slice(0, 6); const rest = all.slice(6).reduce((n, x) => n + x.value, 0); if (rest) items.push({ label: L(`Other (${all.length - 6} divisions)`, `أخرى (${all.length - 6} أقسام)`), value: rest });
    }
    $("#db-donut-body").innerHTML = donutChart(items, L("Basket lines", "بنود السلة"));
  };
  $("#db-donut-tools").innerHTML = segToggle("db-donut-mode", [["group", L("Group", "المجموعة")], ["method", L("Method", "الطريقة")]], "group", L("Group the basket by", "جمّع السلة حسب"));
  bindSeg("db-donut-mode", drawDonut); drawDonut("group");
  // recent activity
  const act = [];
  for (const { run } of [...days].reverse().slice(0, 4)) {
    const ls = cpiLogStates(run);
    for (const k of ["carrefour", "lulu"]) { const x = ls[k]; if (!x) continue;
      act.push({ at: run.startedAt, tone: x.state === "ok" ? "ok" : x.state === "failed" ? "bad" : "warn", text: L(`${outletEn(k)}: ${stateText(x.state)} · ${cpiReason(x, k)} · ${fmtN(run.summary?.[`${k}_barcode`]?.accepted)} barcode prices`, `${outletEn(k)}: ${stateText(x.state)} · ${cpiReason(x, k)} · ${fmtN(run.summary?.[`${k}_barcode`]?.accepted)} سعر بالباركود`) }); }
  }
  for (const s of Object.values(scrapers).filter((s) => s.project === "cpi" && s.last_run)) act.push({ at: s.last_run.at, tone: s.last_run.status === "done" ? "ok" : "bad", text: L(`Scraper ${s.name}: ${scStatus(s.last_run.status)} · ${fmtN(s.last_run.items)} items`, `الكاشطة ${s.name}: ${scStatus(s.last_run.status)} · ${fmtN(s.last_run.items)} عنصر`) });
  drawActivity(act);
  // the internal COICOP category browser (no weights), loaded when opened
  const det = $("#db-internal");
  det.addEventListener("toggle", () => {
    if (!det.open || $("#ct-rows")) return;
    $("#db-internal-body").innerHTML = `<p class="muted" style="margin:0">${esc(L("A category browser over the daily catalogue crawl: codes, names, product counts and an internal price monitor (every product counts the same). Prices only: no official figures.", "متصفح تصنيفات فوق المسح اليومي للكتالوج: الرموز والأسماء وعدد المنتجات ومؤشر أسعار داخلي (لكل منتج القدر نفسه). أسعار فقط: لا أرقام رسمية."))}</p>
      <div class="kpis four"><div class="kpi"><span class="kb"><span class="kv" id="ov-n-prod">—</span><span class="kl">${esc(L("Products in the catalogue", "منتج في الكتالوج"))}</span></span></div><div class="kpi"><span class="kb"><span class="kv" id="ov-n-store">—</span><span class="kl">${esc(L("Stores", "متجر"))}</span></span></div><div class="kpi"><span class="kb"><span class="kv" id="ov-n-days">—</span><span class="kl">${esc(L("Days of prices", "يوماً من الأسعار"))}</span></span></div></div>
      <div class="row"><select id="ct-store" style="flex:1 1 220px;max-width:320px" aria-label="${esc(L("Store", "المتجر"))}"><option value="">${esc(L("All stores", "كل المتاجر"))}</option></select><button id="ov-xlsx" type="button">${ico("download")}${esc(L("Download the tree (Excel)", "تنزيل الشجرة (Excel)"))}</button></div>
      <div class="tw tall"><table><thead><tr><th scope="col" style="min-width:280px">${esc(L("Category", "البند"))}</th><th scope="col" class="num">${esc(L("Products", "المنتجات"))}</th><th scope="col" class="num">${esc(L("Monitor", "المؤشر"))}</th><th scope="col" class="num" id="ct-head-chg">${esc(L("Change", "التغير"))}</th><th scope="col" class="num">${esc(L("Last day", "آخر يوم"))}</th><th scope="col" style="min-width:160px">${esc(L("Trend", "الاتجاه"))}</th></tr></thead>
        <tbody id="ct-rows"><tr><td colspan="6">${loadingHtml(L("Loading the prices…", "تُحمَّل الأسعار…"))}</td></tr></tbody></table></div>
      <p class="muted" id="ct-note" style="margin:0"></p>`;
    loadCoicop();
  });
}
function drawActivity(act) {
  const box = $("#db-activity-body"); if (!box) return;
  act.sort((a, b) => String(b.at).localeCompare(String(a.at)));
  box.innerHTML = act.length ? `<ul class="activity">${act.slice(0, 6).map((a) => `<li><span class="ad ${a.tone}" aria-hidden="true"></span><span><span class="sr-only">${esc(a.tone === "ok" ? L("OK", "سليم") : a.tone === "bad" ? L("Failed", "فشل") : L("Warning", "تحذير"))}: </span>${esc(a.text)}<small>${esc(a.at ? (a.at.length > 10 ? fmtWhen(a.at) : fmtDay(a.at)) : "")}</small></span></li>`).join("")}</ul>` : emptyHtml("file", L("No activity yet", "لا نشاط بعد"), "");
}
// the CPI internal monitor: chained Jevons over exact-match item–shop pairs seen on both consecutive run days
async function cpiMonitor(onProgress) {
  const s = st("cpi"); if (s.monitor) return s.monitor;
  const { days } = dayRunsOf(await ensureRuns("cpi"));
  const pts = []; let I = 100, prev = null;
  for (let i = 0; i < days.length; i++) {
    onProgress?.(i + 1, days.length);
    const run = days[i].run, blocked = cpiBlockedSet(run), m = new Map();
    for (const r of await runRows("cpi", run)) {
      if (r.status !== "found" || r.accepted !== "yes" || !isExact(r) || blocked.has(r.retailer)) continue;
      const p = regPrice(r); if (p > 0) m.set(r.item_code + "|" + r.retailer, p);
    }
    if (prev) { let sl = 0, n = 0; for (const [k, p] of m) { const q = prev.get(k); if (q > 0) { const l = Math.log(p / q); if (Math.abs(l) <= Math.log(3)) { sl += l; n++; } } } if (n) I *= Math.exp(sl / n); pts.push({ x: days[i].day, y: I, n }); }
    else pts.push({ x: days[i].day, y: 100, n: m.size });
    prev = m;
  }
  s.monitor = pts; return pts;
}
function drawCpiMonitor(pts) {
  const tb = $("#db-trend-body"); if (!tb) return;
  tb.innerHTML = lineChart({ id: "db-trend", title: L(TREND_TITLE.cpi[0], TREND_TITLE.cpi[1]), series: [{ label: L("Monitor", "المؤشر"), points: pts }], xFmt: (x) => fmtDay(x), yFmt: (v) => v.toFixed(2) })
    + `<p class="chart-note">${esc(L(`Base ${fmtDay(pts[0]?.x)} = 100 · n = item–shop pairs per day: `, `الأساس ${fmtDay(pts[0]?.x)} = 100 · n = أزواج البند والمتجر لكل يوم: `))}<span class="ltr">${pts.slice(1).map((p) => `${fmtDay(p.x)} n=${p.n}`).join(" · ")}</span>. ${esc(L("Manual prices are not in this series. Not the CPI.", "الأسعار اليدوية ليست في هذه السلسلة. ليس الرقم القياسي لأسعار المستهلك."))}</p>`;
}

// ---------------- TrendX
async function dashTe(seq, fail) {
  let days; try { days = await teDays(); } catch (e) { return ["db-latest-body", "db-activity-body", "db-trend-body", "db-donut-body"].forEach((b) => fail(b, e)); }
  if (!alive(seq)) return;
  const last = days[days.length - 1], prev = days[days.length - 2];
  const outs = await outletRows("te"); if (!alive(seq)) return;
  setKpi("db-kpi-outlets", fmtN(outs.length), "Trading Economics");
  if (!last) { ["db-latest-body", "db-trend-body", "db-donut-body", "db-activity-body"].forEach((b) => ($("#" + b).innerHTML = emptyHtml("file", L("No runs yet", "لا تشغيلات بعد"), ""))); return; }
  const inIdx = last.rows.filter((x) => !TE_EXCL.includes(x.category)).length;
  setKpi("db-kpi-commodities", fmtN(last.rows.length), L(`${inIdx} in index`, `${inIdx} في المؤشر`));
  setKpi("db-kpi-records", fmtN(days.reduce((n, d) => n + d.rows.length, 0)), L(`in all ${days.length} runs`, `في كل التشغيلات (${days.length})`), last.rows.length, L("latest run", "آخر تشغيل"));
  // trend with a category toggle; each category is its own chain
  $("#db-trend-chip").innerHTML = chip(`${fmtDay(days[0].day)} – ${fmtDay(last.day)}`, "blue");
  const drawT = (cat) => {
    const s = teIndex(days, cat);
    $("#db-trend-plot").innerHTML = lineChart({ id: "db-trend", title: L(TREND_TITLE.te[0], TREND_TITLE.te[1]) + " · " + teCatName(cat), series: [{ label: teCatName(cat), points: s }], xFmt: (x) => fmtDay(x), yFmt: (v) => v.toFixed(2) })
      + `<p class="chart-note">${esc(L(`Base ${teBaseLabel()} · chained Jevons on the run date · ${teCatName(cat)} · latest ${s[s.length - 1].y.toFixed(2)} · n = ${s[s.length - 1].n} commodities on the last day · Electricity and Index excluded.`, `الأساس ${teBaseLabel()} · جيفونز متسلسل حسب تاريخ التشغيل · ${teCatName(cat)} · الأخير ${s[s.length - 1].y.toFixed(2)} · n = ${s[s.length - 1].n} سلعة في آخر يوم · الكهرباء والمؤشرات مستبعدة.`))}</p>`;
  };
  $("#db-trend-body").innerHTML = segToggle("db-te-cat", ["All", ...TE_CATS].map((c) => [c, teCatName(c)]), "All", L("Category", "الفئة")) + `<div id="db-trend-plot"></div>`;
  bindSeg("db-te-cat", drawT); drawT("All");
  // latest collection
  const missing = prev ? prev.rows.filter((x) => !last.rows.some((y) => teKey(y) === teKey(x))).map((x) => x.commodity) : [];
  const rs = runStatus("te", last.run);
  $("#db-latest-chip").innerHTML = runChip(rs) + " " + chip(L(`${fmtDay(last.day)} ${fmtTimeDubai(last.run.startedAt)} Dubai`, `${fmtDay(last.day)} ${fmtTimeDubai(last.run.startedAt)} دبي`), "grey");
  $("#db-latest-body").innerHTML = `<div class="tw"><table><thead><tr><th scope="col">${esc(L("Outlet", "المنفذ"))}</th><th scope="col" class="num">${esc(L("Rows / basket", "الصفوف / السلة"))}</th><th scope="col">${esc(L("Method", "الطريقة"))}</th><th scope="col">${esc(L("Missing items", "البنود الناقصة"))}</th><th scope="col">${esc(L("State", "الحالة"))}</th></tr></thead>
    <tbody><tr><th scope="row">Trading Economics</th><td class="num">${fmtN(last.rows.length)} / ${TE_BASKET_N}</td><td>${esc(last.run.method || L("direct fetch (apify/web-fetch fallback)", "جلب مباشر (البديل apify/web-fetch)"))}</td><td>${missing.length ? esc(missing.join(", ")) : esc(L("none", "لا شيء"))}</td><td>${stateChip(outs[0].state, outs[0].reason)}</td></tr></tbody></table></div>`;
  // donut: 7 categories, Electricity and Index greyed
  const c = {}; for (const x of last.rows) c[x.category] = (c[x.category] || 0) + 1;
  $("#db-donut-body").innerHTML = donutChart(Object.entries(c).sort((a, b) => b[1] - a[1]).map(([k, v]) => ({ label: teCatName(k), value: v, muted: TE_EXCL.includes(k), note: TE_EXCL.includes(k) ? L("not in index", "خارج المؤشر") : "" })), L("Commodities", "السلع"));
  // activity: runs, missing days, stale quotes
  const act = days.slice(-4).map((d) => ({ at: d.run.startedAt, tone: runStatus("te", d.run).code === "completed" ? "ok" : "warn", text: L(`Run done: ${d.rows.length}/${TE_BASKET_N} rows (${fmtDay(d.day)})`, `انتهى التشغيل: ${d.rows.length}/${TE_BASKET_N} صفاً (${fmtDay(d.day)})`) }));
  const have = new Set(days.map((d) => d.day));
  for (let d = days[0].day; d <= last.day; d = dayAdd(d, 1)) if (!have.has(d)) act.push({ at: d + "T12:00:00Z", tone: "warn", text: L(`No run on ${fmtDay(d)} (missing day)`, `لا تشغيل في ${fmtDay(d)} (يوم ناقص)`) });
  const stale = last.rows.filter((x) => x.price_date && daySpan(x.price_date, last.day) > 7);
  if (stale.length) act.push({ at: last.run.startedAt, tone: "warn", text: L(`${stale.length} stale quotes older than 7 days: ${stale.map((x) => `${x.commodity} (${fmtDay(x.price_date)})`).join(", ")}`, `${stale.length} تسعيرات قديمة أقدم من 7 أيام: ${stale.map((x) => `${x.commodity} (${fmtDay(x.price_date)})`).join("، ")}`) });
  drawActivity(act);
}

// ---------------- SPPI (prices only in v1: no SPPI index)
async function dashSppi(seq, fail) {
  let d; try { d = await sppiLoad(); } catch (e) { return ["db-latest-body", "db-activity-body", "db-trend-body", "db-donut-body"].forEach((b) => fail(b, e)); }
  if (!alive(seq)) return;
  if (!d.meta) {
    for (const k of ["outlets", "commodities", "records"]) setKpi("db-kpi-" + k, "—", L("No data yet", "لا بيانات بعد"));
    for (const b of ["db-latest-body", "db-trend-body", "db-donut-body", "db-activity-body"]) $("#" + b).innerHTML = emptyHtml("plane", L("No data yet", "لا بيانات بعد"), L("SPPI has no basket or collection in the database yet. Start the basket under Price History › Commodities.", "لا توجد سلة أو جمع لـ SPPI في قاعدة البيانات بعد. ابدأ السلة من سجل الأسعار التاريخي › السلع."), `<a class="btn primary" href="#sppi-price-history/commodities">${esc(L("Open Commodities", "افتح السلع"))}</a>`);
    return;
  }
  const outs = await outletRows("sppi"); if (!alive(seq)) return;
  setKpi("db-kpi-outlets", fmtN(outs.length), L("Outlets page rows", "صفوف صفحة المنافذ"));
  const items = d.items.filter((i) => i.status !== "retired"), routes = items.filter((i) => i.kind === "route").length;
  setKpi("db-kpi-commodities", fmtN(items.length), L(`${routes} routes · ${items.length - routes} hotels`, `${routes} مسار · ${items.length - routes} فندق`));
  const lastW = d.weeks[d.weeks.length - 1];
  setKpi("db-kpi-records", fmtN(d.weeks.reduce((n, w) => n + sppiPriced(w.id), 0)), L(`priced cells in ${d.weeks.length} collections`, `خلايا مسعّرة في ${d.weeks.length} مرات جمع`), lastW ? sppiPriced(lastW.id) : null, L("latest collection", "آخر جمع"));
  const exT = sppiExpected("tickets"), exP = sppiExpected("packages");
  const pr = (w, sv) => sppiActiveRows(w.id).filter((x) => x.survey === sv && (x.status === "ok" || x.source === "manual") && hasPrice(x)).length;
  $("#db-trend-chip").innerHTML = chip(L("Prices only; no SPPI index in v1", "أسعار فقط؛ لا مؤشر SPPI في هذه النسخة"), "grey");
  $("#db-trend-body").innerHTML = d.weeks.length ? `<div class="tw"><table><thead><tr><th scope="col">${esc(L("Collection", "الجمع"))}</th><th scope="col">${esc(L("Collected on", "تاريخ الجمع"))}</th><th scope="col">${esc(L("Tickets priced / expected", "التذاكر المسعّرة / المتوقعة"))}</th><th scope="col">${esc(L("Packages priced / expected", "الباقات المسعّرة / المتوقعة"))}</th></tr></thead><tbody>${d.weeks.map((w) => `<tr><th scope="row">${esc(sppiWeekLabel(w))} · ${esc(fmtMonth(w.month))}</th><td>${esc(fmtDay(w.collected_on))}</td><td>${stackBar([{ n: pr(w, "tickets"), label: L("priced", "مسعّر"), color: "#16a34a" }, { n: Math.max(0, exT - pr(w, "tickets")), label: L("not priced", "غير مسعّر"), color: "#cbd5e1" }])}</td><td>${stackBar([{ n: pr(w, "packages"), label: L("priced", "مسعّر"), color: "#16a34a" }, { n: Math.max(0, exP - pr(w, "packages")), label: L("not priced", "غير مسعّر"), color: "#cbd5e1" }])}</td></tr>`).join("")}</tbody></table></div>` : emptyHtml("calendar", L("No collection yet", "لا جمع بعد"), "");
  // latest collection: outlet x survey with a stacked status bar
  if (lastW) {
    $("#db-latest-chip").innerHTML = chip(`${sppiWeekLabel(lastW)} · ${fmtMonth(lastW.month)} · ${L("collected", "جُمع")} ${fmtDay(lastW.collected_on)}`, "blue");
    const rowsW = sppiActiveRows(lastW.id), pairs = [...new Set(rowsW.map((x) => x.outlet + "|" + x.survey))];
    const C = { ok: ["#16a34a", L("ok", "سليم")], blocked: ["#dc2626", L("blocked", "محجوب")], not_available: ["#94a3b8", L("not available", "غير متاح")], to_review: ["#d97706", L("to review", "للمراجعة")], partial: ["#f59e0b", L("partial", "جزئي")], manual: ["#7c3aed", L("manual", "يدوي")] };
    $("#db-latest-body").innerHTML = pairs.length ? `<div class="tw"><table><thead><tr><th scope="col">${esc(L("Outlet", "المنفذ"))}</th><th scope="col">${esc(L("Survey", "المسح"))}</th><th scope="col" style="min-width:260px">${esc(L("Cells by status", "الخلايا حسب الحالة"))}</th><th scope="col">${esc(L("State", "الحالة"))}</th></tr></thead><tbody>${pairs.map((k) => { const [o, sv] = k.split("|"), rs = rowsW.filter((x) => x.outlet === o && x.survey === sv), s = sppiOutletState(lastW.id, o);
      return `<tr><th scope="row" dir="auto">${esc(sppiName(sppiOutlet(o)) || o)}</th><td>${esc(sv === "packages" ? L("Packages", "الباقات") : L("Tickets", "التذاكر"))}</td><td>${stackBar(Object.entries(C).map(([st2, [col, lbl]]) => ({ n: rs.filter((x) => (st2 === "manual" ? x.source === "manual" : x.source !== "manual" && x.status === st2)).length, label: lbl, color: col })))}</td><td>${stateChip(s.state)}</td></tr>`; }).join("")}</tbody></table></div>` : emptyHtml("file", L("No prices in this collection yet", "لا أسعار في هذا الجمع بعد"), "");
  } else $("#db-latest-body").innerHTML = emptyHtml("file", L("No collection yet", "لا جمع بعد"), "");
  // donut: domestic routes, foreign routes, hotels by city
  const c = {}; for (const i of items) { const k = i.kind === "route" ? (i.market === "foreign" ? L("Foreign routes", "مسارات خارجية") : L("Domestic routes", "مسارات داخلية")) : L(`Hotels · ${i.city || "?"}`, `فنادق · ${i.city || "?"}`); c[k] = (c[k] || 0) + 1; }
  $("#db-donut-body").innerHTML = donutChart(Object.entries(c).sort((a, b) => b[1] - a[1]).map(([k, v]) => ({ label: k, value: v })), L("Items", "البنود"));
  // activity: per collection x survey
  const act = [];
  for (const w of d.weeks.slice(-3)) for (const sv of ["tickets", "packages"]) {
    const rs = sppiActiveRows(w.id).filter((x) => x.survey === sv), bl = [...new Set(rs.filter((x) => x.status === "blocked").map((x) => sppiName(sppiOutlet(x.outlet)) || x.outlet))];
    if (!rs.length) continue;
    act.push({ at: w.collected_on, tone: bl.length ? "warn" : "ok", text: L(`${sppiWeekLabel(w)} ${fmtMonth(w.month)} · ${sv}: ${pr(w, sv)}/${sv === "tickets" ? exT : exP} priced${bl.length ? ` · blocked: ${bl.join(", ")}` : ""}`, `${sppiWeekLabel(w)} ${fmtMonth(w.month)} · ${sv === "tickets" ? "التذاكر" : "الباقات"}: ${pr(w, sv)}/${sv === "tickets" ? exT : exP} مسعّرة${bl.length ? ` · محجوب: ${bl.join("، ")}` : ""}`) });
  }
  drawActivity(act);
}
