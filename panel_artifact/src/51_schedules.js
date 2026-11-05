
// ============================================================ Schedules (35.png)
const CPI_CATALOGUE_TRIGGER = "trig_01BKPxvQYZr2sCFEWDEJ9LGk";
let schedView = "schedule";
function schedRefresh() { if (curRoute?.kind === "page" && curRoute.page === "schedules") rerender(); }
function pgSchedules(r, seq) {
  const pid = r.pid, p = routeOf(pid);
  $("#page").innerHTML = titleRow(L("Schedules", "الجداول"),
      `<button class="secondary" type="button" id="sch-sync">${ico("refresh")}${esc(L("Sync schedules", "مزامنة الجداول"))}</button><button class="primary" type="button" id="sch-create" aria-expanded="false" aria-controls="sch-create-panel">${ico("plus")}${esc(L("Create Schedule", "إنشاء جدول"))}</button>`,
      segToggle("sch-toggle", [["schedule", L("By Schedule", "حسب الجدول"), "listico"], ["outlet", L("By Outlet", "حسب المنفذ"), "grid4"]], schedView, L("Group schedules", "تجميع الجداول")))
    + `<section class="card" id="sch-create-panel" hidden aria-labelledby="sch-create-h"><h2 id="sch-create-h">${esc(L("New schedule", "جدول جديد"))}</h2>
        <p class="notice info" style="margin:0">${esc(L("Schedules are created by asking Claude: fill in what you need, copy the request and send it to Claude. This page reads, pauses, retimes and runs existing schedules; it never creates or deletes them.", "تُنشأ الجداول بطلب من Claude: املأ ما تحتاجه وانسخ الطلب وأرسله إلى Claude. هذه الصفحة تقرأ الجداول الموجودة وتوقفها وتغيّر موعدها وتشغّلها؛ لا تنشئها ولا تحذفها."))}</p>
        <div class="form-grid"><label class="f"><span>${esc(L("Name", "الاسم"))}</span><input id="sch-new-name" value="${esc(projLabel(pid))} "></label>
        <label class="f"><span>${esc(L("Time (Dubai)", "الوقت (دبي)"))}</span><input id="sch-new-time" type="time" value="06:30" dir="ltr"></label>
        <label class="f"><span>${esc(L("Days", "الأيام"))}</span><select id="sch-new-days"><option value="daily">${esc(L("Every day", "كل يوم"))}</option><option value="weekdays">${esc(L("Monday to Friday", "الاثنين إلى الجمعة"))}</option><option value="weekly">${esc(L("Once a week", "مرة في الأسبوع"))}</option><option value="monthly">${esc(L("Once a month", "مرة في الشهر"))}</option></select></label>
        <label class="f"><span>${esc(L("Outlet", "المنفذ"))}</span><select id="sch-new-outlet"><option value="">${esc(L("All outlets", "كل المنافذ"))}</option>${outletOptions(pid).map(([c, n]) => `<option value="${esc(c)}">${esc(n)}</option>`).join("")}</select></label></div>
        <label class="f"><span>${esc(L("Request for Claude", "الطلب لـ Claude"))}</span><textarea id="sch-new-text" rows="3" readonly></textarea></label>
        <div class="row"><button class="primary" type="button" id="sch-new-copy">${ico("copy")}${esc(L("Copy the request", "انسخ الطلب"))}</button><button type="button" id="sch-new-close">${esc(L("Close", "إغلاق"))}</button></div></section>
    <div id="sch-body">${loadingHtml(L("Reading schedules…", "تُقرأ الجداول…"))}</div>`;
  bindSeg("sch-toggle", (v) => { schedView = v; drawSched(pid, seq); });
  $("#sch-sync").onclick = () => { for (const k of Object.keys(trigCache)) delete trigCache[k]; if (S[pid]) { S[pid].runs = null; S[pid].teDays = null; } toast(L("Schedules read again", "أُعيدت قراءة الجداول")); drawSched(pid, seq, true); };
  const panel = $("#sch-create-panel"), txt = () => { const days = $("#sch-new-days"); $("#sch-new-text").value = L(`Please create a scheduled task “${$("#sch-new-name").value.trim()}” for ${projLabel(pid)}${$("#sch-new-outlet").value ? ` (outlet ${outletName(pid, $("#sch-new-outlet").value)})` : ""}: ${days.options[days.selectedIndex].text.toLowerCase()} at ${$("#sch-new-time").value} Dubai time.`, `أرجو إنشاء مهمة مجدولة «${$("#sch-new-name").value.trim()}» لمشروع ${projLabel(pid)}${$("#sch-new-outlet").value ? ` (المنفذ ${outletName(pid, $("#sch-new-outlet").value)})` : ""}: ${days.options[days.selectedIndex].text} الساعة ${$("#sch-new-time").value} بتوقيت دبي.`); };
  $("#sch-create").onclick = () => { panel.hidden = !panel.hidden; $("#sch-create").setAttribute("aria-expanded", String(!panel.hidden)); if (!panel.hidden) { txt(); $("#sch-new-name").focus(); } };
  for (const id of ["sch-new-name", "sch-new-time", "sch-new-days", "sch-new-outlet"]) $("#" + id).addEventListener("input", txt), $("#" + id).addEventListener("change", txt);
  $("#sch-new-close").onclick = () => { panel.hidden = true; $("#sch-create").setAttribute("aria-expanded", "false"); $("#sch-create").focus(); };
  $("#sch-new-copy").onclick = async () => { const t = $("#sch-new-text"); try { await navigator.clipboard.writeText(t.value); toast(L("Copied: paste it to Claude", "نُسخ: الصقه لـ Claude")); } catch (e) { t.focus(); t.select(); toast(L("Select the text and copy it", "حدّد النص وانسخه")); } };
  drawSched(pid, seq);
}
function schedCard(key, title, chipHtml, body, linked) {
  return `<section class="card" id="sch-card-${key}" aria-labelledby="sch-h-${key}"><div class="card-h"><h2 id="sch-h-${key}">${esc(title)}</h2><span class="spacer"></span><span id="sch-chip-${key}">${chipHtml}</span></div>${body}${linked ? `<p class="muted" style="margin:0">${esc(L("Linked outlets: ", "المنافذ المرتبطة: "))}${esc(linked)}</p>` : ""}</section>`;
}
async function drawSched(pid, seq, fresh) {
  const body = $("#sch-body"); if (!body) return;
  if (pid === "sppi") {
    let d; try { d = await sppiLoad(fresh); } catch (e) { unmountAll(); body.innerHTML = errBox(schedFail(e), "sch-retry"); bindRetry(); return; }
    if (!alive(seq)) return;
    const rows = (d.outlets || []).map((o) => { const c = d.collectors.filter((x) => x.outlet === o.code);
      const mode = c.length ? c.map((x) => x.run_location === "cloud" ? `${L("Cloud script", "سكربت سحابي")} (${x.script})` : x.run_location === "pc" ? `${L("PC run", "تشغيل على الحاسوب")}: ${x.script}` : L("Manual", "يدوي")).join(" · ") : o.access === "manual" ? L("Manual", "يدوي") : o.access === "pc_only" ? L("PC run", "تشغيل على الحاسوب") : L("Not set", "غير محدد");
      return { o, mode, loc: c[0]?.run_location || (o.access === "pc_only" ? "pc" : o.access === "manual" ? "manual" : "cloud") }; });
    const table = (list) => `<div class="tw"><table><thead><tr><th scope="col">${esc(L("Outlet", "المنفذ"))}</th><th scope="col">${esc(L("Run mode", "طريقة التشغيل"))}</th>${d.weeks.map((w) => `<th scope="col">${esc(sppiWeekLabel(w))} · ${esc(fmtMonth(w.month))}</th>`).join("")}</tr></thead><tbody>${list.map(({ o, mode }) => `<tr><th scope="row" dir="auto">${esc(sppiName(o))}</th><td><span class="mono" style="white-space:normal">${esc(mode)}</span></td>${d.weeks.map((w) => { const s = sppiOutletState(w.id, o.code); return `<td>${esc(L("collected ", "جُمع "))}${esc(fmtDay(w.collected_on))} ${stateChip(s.state)}</td>`; }).join("")}</tr>`).join("")}</tbody></table></div>`;
    unmountAll(); body.innerHTML = `<section class="card">${emptyHtml("alarm", L("No automated SPPI schedule yet", "لا جدول آلي لـ SPPI بعد"), L("Collected monthly; timing per item to be determined. Each outlet is collected by a cloud script, a run on a PC, or by hand.", "الجمع شهري؛ توقيت كل بند يُحدد لاحقاً. كل منفذ يُجمع بسكربت سحابي أو بتشغيل على حاسوب أو يدوياً."))}</section>`
      + (d.meta ? (schedView === "outlet" ? ["cloud", "pc", "manual"].map((loc) => { const l = rows.filter((x) => x.loc === loc); return l.length ? `<section class="card"><h2>${esc({ cloud: L("Cloud script", "سكربت سحابي"), pc: L("PC run", "تشغيل على الحاسوب"), manual: L("Manual", "يدوي") }[loc])}</h2>${table(l)}</section>` : ""; }).join("") : `<section class="card"><h2>${esc(L("Outlets and their run mode", "المنافذ وطريقة تشغيلها"))}</h2>${table(rows)}</section>`) : "");
    return;
  }
  const P0 = projects[pid] || {};
  let lastRunHtml = "", list = [];
  try {
    list = await ensureRuns(pid, fresh);
    const last = pid === "cpi" ? dayRunsOf(list).days.slice(-1)[0]?.run : list[0];
    if (last) lastRunHtml = `${runChip(runStatus(pid, last))} <span class="muted">${esc(fmtWhen(last.startedAt))} · ${esc(pid === "cpi" ? L(`${fmtN(cpiSeen(last))} seen / ${fmtN(last.count)} lines`, `${fmtN(cpiSeen(last))} مرئي / ${fmtN(last.count)} بنداً`) : L(`${fmtN(last.count)} rows`, `${fmtN(last.count)} صفاً`))}</span>`;
  } catch (e) { lastRunHtml = `<span title="${esc(dbErr(e))}">—</span> <span class="muted">${esc(L("runs could not be read", "تعذّرت قراءة التشغيلات"))}</span>`; }
  if (!alive(seq)) return;
  if (pid === "cpi") {
    const [sr, cat] = await Promise.all([getDoc("system/scrapers_routine"), catalogueLatest().catch(() => null)]); if (!alive(seq)) return;
    // catalogue crawl: its last run is catalogue/latest (date + store count > 0), 5.1
    const nStores = cat ? Object.values(cat.stores || {}).filter((v) => +v > 0).length : 0;
    const catRunHtml = cat ? `${runChip({ code: nStores > 0 ? "completed" : "failed", text: nStores > 0 ? "" : L("0 stores", "0 متاجر") })} <span class="muted">${esc(fmtDay(cat.date))} · ${esc(L(`${fmtN(nStores)} stores · ${fmtN(cat.rows)} products`, `${fmtN(nStores)} متاجر · ${fmtN(cat.rows)} منتج`))}</span>` : `<span>—</span> <span class="muted">${esc(L("no catalogue yet", "لا كتالوج بعد"))}</span>`;
    const custom = Object.values(scrapers).filter((s) => s.project === "cpi");
    const cards = [
      ["daily", L("CPI daily scrape", "سحب CPI اليومي"), P0.schedule?.trigger_id, "sched", "Carrefour, Lulu"],
      ["catalogue", L("Catalogue crawl", "مسح الكتالوج"), CPI_CATALOGUE_TRIGGER, "sched-cat", "Carrefour, Lulu, Sharaf DG, Zara, Max, Centrepoint"],
    ];
    if (schedView === "outlet") {
      unmountAll(); body.innerHTML = `<section class="card"><h2>${esc(L("By outlet", "حسب المنفذ"))}</h2><div class="tw"><table><thead><tr><th scope="col">${esc(L("Outlet", "المنفذ"))}</th><th scope="col">${esc(L("Schedules", "الجداول"))}</th></tr></thead><tbody>
        ${CPI_OUTLETS.map((o) => `<tr><th scope="row">${esc(o.en)}</th><td>${o.daily ? chip(L("CPI daily scrape", "سحب CPI اليومي"), "blue") + " " : ""}${chip(L("Catalogue crawl", "مسح الكتالوج"), "blue")}</td></tr>`).join("")}
        <tr><th scope="row">${esc(L("Custom scrapers", "الكاشطات المخصصة"))}</th><td>${chip(L("On demand", "عند الطلب"), "grey")} ${esc(custom.map((s) => s.name).join(", "))}</td></tr></tbody></table></div></section>`;
      return;
    }
    unmountAll(); body.innerHTML = `<div class="sched-grid">${cards.map(([k, t, tid, key, linked]) => schedCard(k, t, chip(L("Reading…", "يُقرأ…"), "grey"), `<div id="sch-live-${k}"></div>`, linked)).join("")}
      ${schedCard("custom", L("Custom scrapers", "الكاشطات المخصصة"), chip(L("On demand", "عند الطلب"), "grey"), `<dl class="kv"><dt>${esc(L("Mode", "النمط"))}</dt><dd>${esc(sr?.mode === "on_demand" || !sr?.cron ? L("on demand: no time", "عند الطلب: بلا موعد") : sr.mode)}</dd><dt>${esc(L("Routine", "المهمة"))}</dt><dd class="mono">${esc(sr?.trigger_id || "—")}</dd><dt>${esc(L("Scrapers", "الكاشطات"))}</dt><dd>${fmtN(custom.length)}</dd></dl><p class="muted" style="margin:0">${esc(L("Runs from Scrapers › Run now.", "يعمل من الكاشطات › شغّل الآن."))} <a class="tap" href="#cpi-scrapers">${esc(L("Open Scrapers", "افتح الكاشطات"))}</a></p>`, custom.map((s) => s.name).join(", ") || "—")}</div>
      <div data-slot="quick"></div><div data-slot="apify"></div>`;
    for (const [k, , tid, key] of cards) { const box = $("#sch-live-" + k); if (!tid) { box.innerHTML = `<p class="muted">${esc(L("No routine for this project. Ask Claude to create one.", "لا مهمة مجدولة لهذا المشروع. اطلب من Claude إنشاءها."))}</p>`; continue; } renderSchedule(box, tid, key, { chip: $("#sch-chip-" + k).firstElementChild || $("#sch-chip-" + k), lastRunHtml: k === "daily" ? lastRunHtml : catRunHtml, fresh }); }
    mount("quick", "quick"); mount("apify", "apify-run"); const ar = $("#apify-run"); if (ar) ar.open = false;
    renderQuick(); renderRunPicks(); renderJob();
    ensureBasket("cpi").then((b) => { if (!alive(seq)) return; basket = b; renderRunPicks(); }).catch(() => {});
    return;
  }
  // TrendX
  const tid = P0.schedule?.trigger_id;
  if (schedView === "outlet") { unmountAll(); body.innerHTML = `<section class="card"><h2>${esc(L("By outlet", "حسب المنفذ"))}</h2><div class="tw"><table><tbody><tr><th scope="row">Trading Economics</th><td>${chip(L("TrendX daily close capture · daily", "التقاط إغلاق TrendX اليومي · يومياً"), "blue")}</td></tr></tbody></table></div></section>`; return; }
  unmountAll(); body.innerHTML = `<div class="sched-grid">${schedCard("daily", L("TrendX daily close capture", "التقاط إغلاق TrendX اليومي"), chip(L("Reading…", "يُقرأ…"), "grey"), `<div id="sch-live-daily"></div>
    <ol class="sc-steps" style="flex-direction:column">${(LANG === "ar" ? ["collect_te.py: جلب صفحة السلع وقراءة 107 صفوف", "Commodity Price Log: حفظ اليوم", "projects/te: حفظ التشغيل وصفوفه", "إرسال ملف Excel بالبريد"] : ["collect_te.py: fetch the commodities page, read 107 rows", "Commodity Price Log: save the day", "projects/te: save the run and its rows", "Excel email"]).map((s) => `<li>${esc(s)}</li>`).join("")}</ol>`, "Trading Economics")}</div>`;
  if (tid) renderSchedule($("#sch-live-daily"), tid, "sched", { chip: $("#sch-chip-daily").firstElementChild, lastRunHtml, fresh });
  else $("#sch-live-daily").innerHTML = `<p class="muted">${esc(L("No routine for this project. Ask Claude to create one.", "لا مهمة مجدولة لهذا المشروع. اطلب من Claude إنشاءها."))}</p>`;
}
