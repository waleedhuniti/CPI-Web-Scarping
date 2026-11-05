
// ============================================================ Price Logs: runs latest first, log viewer, the run rows viewer, Dataiku download
function pgLogs(r, seq) {
  const pid = r.pid;
  $("#page").innerHTML = titleRow(L("Price Logs", "سجل التشغيلات"), pid === "sppi" ? "" : `<span data-slot="rexport"></span>`)
    + `<section class="card"><div class="row" style="justify-content:space-between"><span class="count-pill" id="pl-count">${esc(L("— runs", "— تشغيلات"))}</span><button class="sq" type="button" id="pl-refresh" aria-label="${esc(L("Refresh", "تحديث"))}" title="${esc(L("Refresh", "تحديث"))}">${ico("refresh")}</button></div>
      <div id="pl-list">${loadingHtml(L("Loading price logs…", "يُحمَّل سجل التشغيلات…"))}</div></section><div data-slot="rview"></div>`;
  if (pid !== "sppi") { mount("rexport", "r-export-all"); mount("rview", "r-view"); $("#r-view").hidden = true; loadRuns(); }
  $("#pl-refresh").onclick = () => { if (S[pid]) { S[pid].runs = null; S[pid].teDays = null; } if (pid === "sppi") sppiCache = null; drawLogs(pid, seq); };
  drawLogs(pid, seq);
}
const logFail = (seq) => { if (!alive(seq)) return; $("#pl-list").innerHTML = errBox(L("Unable to load price log data right now.", "تعذّر تحميل بيانات سجل التشغيلات الآن."), "pl-retry"); $("#pl-retry").onclick = () => rerender(); };
function logViewer(id, lines) {
  return `<div class="row" style="justify-content:space-between"><b>${esc(L("Run log", "سجل التشغيل"))}</b><button type="button" data-copy="${esc(id)}">${ico("copy")}${esc(L("Copy log", "نسخ السجل"))}</button></div><pre class="log" id="${esc(id)}">${esc((lines || []).join("\n") || L("No log for this run.", "لا يوجد سجل لهذا التشغيل."))}</pre>`;
}
function bindLogList(pid) {
  $("#pl-list").onclick = async (e) => {
    const c = e.target.closest("[data-copy]"); if (c) { try { await navigator.clipboard.writeText($("#" + c.dataset.copy).textContent); toast(L("Log copied", "نُسخ السجل")); } catch (x) { toast(L("Select the log text and copy it", "حدّد نص السجل وانسخه")); } return; }
    const o = e.target.closest("[data-open-rows]"); if (o) { runs = st(pid).runs || runs; await showRun(o.dataset.openRows); }
  };
}
async function drawLogs(pid, seq) {
  if (pid === "sppi") return drawLogsSppi(seq);
  let list, days, dup;
  try { list = await ensureRuns(pid); ({ days, dup } = dayRunsOf(list)); } catch (e) { return logFail(seq); }
  if (!alive(seq)) return;
  runs = list;
  $("#pl-count").textContent = L(`${list.length} runs`, `${list.length} تشغيلاً`);
  if (!list.length) { $("#pl-list").innerHTML = emptyHtml("file", L("No runs yet", "لا تشغيلات بعد"), "", `<a class="btn" href="#${routeOf(pid)}-schedules">${esc(L("Open Schedules", "افتح الجداول"))}</a>`); return; }
  let teByRun = {};
  if (pid === "te") { try { for (const d of await teDays()) teByRun[d.run.id] = d; } catch (e) {} if (!alive(seq)) return; }
  const kept = days.map((d) => d.run.id);
  const html = list.map((run, i) => {
    const rs = runStatus(pid, run), dur = scDur(run), tags = [];
    if (!isAutoRun(run)) tags.push(chip(L("Browser / Apify (legacy)", "المتصفح / Apify (قديم)"), "grey"));
    if (dup.has(run.id)) tags.push(chip(L("duplicate (another run that day counts)", "مكرر (يُحتسب تشغيل آخر في اليوم)"), "grey"));
    let srcChips = "", note = "", checks = "";
    if (pid === "cpi") {
      const ls = cpiLogStates(run);
      srcChips = Object.entries(run.summary || {}).map(([k, v]) => { const ret = k.split("_")[0], kind = k.split("_").slice(1).join("_"), bl = ls[ret]?.state === "blocked" && kind === "category";
        return chip(`${outletEn(ret).split(" ")[0]} ${kind}: ${bl ? L("blocked (carried)", "محجوب (منقول)") : `${fmtN(v.accepted)}/${fmtN(v.lines)}`}`, bl ? "bad" : ls[ret]?.state === "ok" || !ls[ret] ? "blue" : "warn"); }).join(" ");
      if (cpiCarried(run)) note = `<p class="notice" style="margin:0">${esc(L(`Data note: ${[...cpiBlockedSet(run)].map((k) => outletEn(k).split(" ")[0]).join(", ")} category rows carried forward (${fmtN(cpiCarried(run))}), shown as Blocked, excluded from all figures. They stay in the downloads with obs_state = blocked_carried.`, `ملاحظة: صفوف أقسام ${[...cpiBlockedSet(run)].map((k) => outletEn(k).split(" ")[0]).join("، ")} منقولة من يوم سابق (${fmtN(cpiCarried(run))})، تظهر محجوبة ومستبعدة من كل الأرقام. تبقى في التنزيلات مع obs_state = blocked_carried.`))}</p>`;
    } else {
      const d = teByRun[run.id], prev = d ? teByRun[kept[kept.indexOf(run.id) - 1]] : null;
      const n = run.count ?? d?.rows.length ?? 0, miss = d && prev ? prev.rows.filter((x) => !d.rows.some((y) => teKey(y) === teKey(x))).map((x) => x.commodity) : [];
      const stale = d ? d.rows.filter((x) => x.price_date && daySpan(x.price_date, d.day) > 7) : [];
      srcChips = chip(`Trading Economics: ${n}/${TE_BASKET_N}`, n >= TE_BASKET_N ? "blue" : "warn") + " " + chip(run.method || L("direct fetch", "جلب مباشر"), "grey");
      checks = `<ul style="margin:0;padding-inline-start:20px">${n < TE_BASKET_N ? `<li>${esc(L(`${TE_BASKET_N - n} rows short of the basket`, `ينقص ${TE_BASKET_N - n} صفاً عن السلة`))}</li>` : ""}${miss.length ? `<li>${esc(L("Missing vs the previous run: ", "ناقص مقارنة بالتشغيل السابق: ") + miss.join(", "))}</li>` : ""}${stale.length ? `<li>${esc(L(`${stale.length} quotes older than 7 days: `, `${stale.length} تسعيرات أقدم من 7 أيام: `) + stale.map((x) => `${x.commodity} (${x.price_date})`).join(", "))}</li>` : ""}${!miss.length && !stale.length && n >= TE_BASKET_N ? `<li>${esc(L("All checks passed", "كل الفحوص سليمة"))}</li>` : ""}</ul>`;
    }
    const seen = pid === "cpi" ? L(`${fmtN(cpiSeen(run))} seen / ${fmtN(run.count)} lines`, `${fmtN(cpiSeen(run))} مرئي / ${fmtN(run.count)} بنداً`) : L(`${fmtN(run.count)} rows`, `${fmtN(run.count)} صفاً`);
    return `<details class="acc" id="pl-run-${esc(run.id)}"><summary>${ico("chevr", "chev flip")}<span>${esc(fmtWhen(run.startedAt))}</span><span class="muted">${esc(dur)}</span>${runChip(rs)}<span class="muted">${esc(seen)}</span>${tags.join(" ")}<span class="src-chips">${srcChips}</span></summary>
      <div class="acc-body">${note}${checks}${logViewer("pl-log-" + i, run.log)}
        <div class="row"><button type="button" class="primary" data-open-rows="${esc(run.id)}">${ico("listico")}${esc(L("Open rows", "افتح الصفوف"))}</button><span class="muted">${esc(L("Search, filter, Excel, delete run", "بحث وتصفية وExcel وحذف التشغيل"))}</span></div></div></details>`;
  }).join("");
  $("#pl-list").innerHTML = html;
  bindLogList(pid);
}
// §5.1 run chip text for one SPPI collection × survey: names each outlet that is not Read OK, with its counts
function sppiRunIssues(sv, rs) {
  const cells = (n) => L(n === 1 ? "1 cell" : `${fmtN(n)} cells`, `${fmtN(n)} خلية`);
  const exp = {}; for (const x of sppiCache?.sample || []) if (x.status !== "retired" && x.survey === sv) exp[x.outlet] = (exp[x.outlet] || 0) + (x.legs || ["package"]).length;
  const g = { blocked: [], failed: [], notread: [], partial: [] };
  for (const o of Object.keys(exp)) {
    const r = rs.filter((x) => x.outlet === o), nm = sppiName(sppiOutlet(o)) || o;
    const pr = r.filter((x) => (x.status === "ok" || x.source === "manual") && hasPrice(x)).length;
    if (!r.length) g.notread.push([nm, exp[o]]);
    else if (r.every((x) => x.status === "blocked")) g.blocked.push([nm, r.length]);
    else if (r.every((x) => x.status === "failed")) g.failed.push([nm, r.length]);
    else if (pr < exp[o]) g.partial.push([nm, pr, exp[o]]);
  }
  const names = (l) => l.map((x) => x[0]).join(L(", ", "، ")), sum = (l) => l.reduce((n, x) => n + x[1], 0), out = [];
  if (g.blocked.length) out.push(L(`${names(g.blocked)} blocked (${cells(sum(g.blocked))})`, `${names(g.blocked)} محجوب (${cells(sum(g.blocked))})`));
  if (g.failed.length) out.push(L(`${names(g.failed)} failed (${cells(sum(g.failed))})`, `${names(g.failed)} فشل (${cells(sum(g.failed))})`));
  if (g.notread.length) out.push(L(`${names(g.notread)} not read (0 of ${cells(sum(g.notread))})`, `${names(g.notread)} لم يُقرأ (0 من ${cells(sum(g.notread))})`));
  for (const [nm, pr, e] of g.partial) out.push(L(`${nm} ${fmtN(pr)} of ${fmtN(e)} priced`, `${nm} ${fmtN(pr)} من ${fmtN(e)} مسعّر`));
  return out.join(L("; ", "؛ "));
}
async function drawLogsSppi(seq) {
  let d; try { d = await sppiLoad(); } catch (e) { return logFail(seq); }
  if (!alive(seq)) return;
  if (!d.meta) { $("#pl-count").textContent = L("— runs", "— تشغيلات"); $("#pl-list").innerHTML = emptyHtml("file", L("No data yet", "لا بيانات بعد"), L("No SPPI collection is saved yet.", "لا يوجد جمع SPPI محفوظ بعد."), `<a class="btn" href="#sppi-schedules">${esc(L("Open Schedules", "افتح الجداول"))}</a>`); return; }
  const entries = [];
  for (const w of [...d.weeks].reverse()) for (const sv of ["tickets", "packages"]) { const rs = sppiActiveRows(w.id).filter((x) => x.survey === sv); if (rs.length) entries.push({ w, sv, rs }); }
  $("#pl-count").textContent = L(`${entries.length} runs`, `${entries.length} تشغيلاً`);
  if (!entries.length) { $("#pl-list").innerHTML = emptyHtml("file", L("No runs yet", "لا تشغيلات بعد"), "", `<a class="btn" href="#sppi-schedules">${esc(L("Open Schedules", "افتح الجداول"))}</a>`); return; }
  $("#pl-list").innerHTML = entries.map(({ w, sv, rs }, i) => {
    const priced = rs.filter((x) => (x.status === "ok" || x.source === "manual") && hasPrice(x)).length, exp = sppiExpected(sv), man = rs.filter((x) => x.source === "manual").length;
    const bl = [...new Set(rs.filter((x) => x.status === "blocked").map((x) => x.outlet))];
    const code = !priced ? "failed" : bl.length || priced < exp ? "partial" : "completed";
    const why = code === "completed" ? "" : sppiRunIssues(sv, rs);
    return `<details class="acc" id="pl-run-${i}"><summary>${ico("chevr", "chev flip")}<span>${esc(sppiWeekLabel(w))} · ${esc(fmtMonth(w.month))} · ${esc(sv === "tickets" ? L("Tickets", "التذاكر") : L("Packages", "الباقات"))}</span><span class="muted">${esc(L("collected", "جُمع"))} ${esc(fmtDay(w.collected_on))}</span>${runChip({ code, text: why })}<span class="muted">${esc(L(`${priced} / ${exp} priced`, `${priced} / ${exp} مسعّر`))}</span>${chip(L(`scraped ${rs.length - man}`, `مسحوب ${rs.length - man}`), "blue")}${man ? chip(L(`manual ${man}`, `يدوي ${man}`), "manual") : ""}</summary>
      <div class="acc-body">${bl.length ? `<div class="tw"><table><thead><tr><th scope="col">${esc(L("Blocked outlet", "منفذ محجوب"))}</th><th scope="col">${esc(L("Reason", "السبب"))}</th></tr></thead><tbody>${bl.map((o) => `<tr><th scope="row">${esc(sppiName(sppiOutlet(o)) || o)}</th><td dir="auto">${esc(rs.find((x) => x.outlet === o && x.note)?.note || "—")}</td></tr>`).join("")}</tbody></table></div>` : `<p class="muted" style="margin:0">${esc(L("No outlet blocked.", "لا منفذ محجوب."))}</p>`}
        <p style="margin:0"><a href="#sppi-price-history">${esc(L("Open these prices in Price History", "افتح هذه الأسعار في سجل الأسعار التاريخي"))}</a></p></div></details>`;
  }).join("");
}
