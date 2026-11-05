
// ============================================================ Scrapers (list as PIP's Scraper Management; workspace 30.png, 21-23.png)
/* The list frame (KPIs, filter card, table) is drawn here; 35_scrapers.js fills it (scRenderList) and owns the workspace block
   #blk-sc-ws (mounted into the page for #<p>-scrapers/new and #<p>-scrapers/<map name>). A SegmentedToggle switches the list
   between the scrapers and the project's Apify actors (the former Actors tab: #blk-actors, a-list / a-add / a-save). */
let scView = "scrapers";
function scListFrame(pid) {
  const opts = [["scrapers", L("Scrapers", "الكاشطات"), "scraper"], ["actors", L("Apify actors", "Actors على Apify"), "chip"]];
  $("#page").innerHTML = titleRow(L("Scraper Management", "إدارة الكاشطات"), `<button class="primary" type="button" id="sc-new">${ico("plus")}${esc(L("Create scraper", "إنشاء كاشطة"))}</button>`,
      segToggle("sc-view", opts, scView, L("Scrapers or Apify actors", "الكاشطات أو Actors")))
    + `<div id="sc-list-view" class="stack"${scView === "scrapers" ? "" : " hidden"}>
      <div class="kpis four">
        ${kpiHtml({ id: "sc-k-total-card", icon: "chip", label: L("Total scrapers", "إجمالي الكاشطات") })}
        ${kpiHtml({ id: "sc-k-active-card", icon: "check", tint: "green", label: L("Active", "مفعّلة") })}
        ${kpiHtml({ id: "sc-k-inactive-card", icon: "ban", tint: "red", label: L("Inactive", "متوقفة") })}
        ${kpiHtml({ id: "sc-k-target-card", icon: "hex", tint: "amber", label: L("Target items", "العناصر المستهدفة") })}</div>
      <section class="card"><div class="filter-card">
        <label class="search"><span class="sr-only">${esc(L("Search scrapers", "ابحث في الكاشطات"))}</span>${ico("search")}<input id="sc-q" type="search" placeholder="${esc(L("Search by label, outlet name, or actor ID", "ابحث بالاسم أو المنفذ أو معرّف الـ Actor"))}"></label>
        <select id="sc-filter" aria-label="${esc(L("Scraper type", "نوع الكاشطة"))}"><option value="">${esc(L("All scraper types", "كل أنواع الكاشطات"))}</option><option value="routine">${esc(L("Routine", "مهمة مجدولة"))}</option><option value="scrapling">Scrapling</option><option value="apify">Apify</option></select>
        <select id="sc-state" aria-label="${esc(L("State", "الحالة"))}"><option value="">${esc(L("All states", "كل الحالات"))}</option><option value="active">${esc(L("Active", "مفعّلة"))}</option><option value="inactive">${esc(L("Inactive", "متوقفة"))}</option></select>
        <button class="sq" type="button" id="sc-refresh" aria-label="${esc(L("Refresh", "تحديث"))}" title="${esc(L("Refresh", "تحديث"))}">${ico("refresh")}</button></div>
        <p class="muted" id="sc-count" role="status" style="margin:12px 0 0"></p>
        <div class="tw"><table id="sc-table"><caption class="sr-only">${esc(L("Scrapers", "الكاشطات"))}</caption><thead><tr><th scope="col">${esc(L("Label", "الاسم"))}</th><th scope="col">${esc(L("Outlet", "المنفذ"))}</th><th scope="col">${esc(L("Type", "النوع"))}</th><th scope="col">${esc(L("Status", "الحالة"))}</th><th scope="col">${esc(L("Last run", "آخر تشغيل"))}</th><th scope="col">${esc(L("Actions", "إجراءات"))}</th></tr></thead>
          <tbody id="sc-list"></tbody></table></div>
        ${pid === "sppi" ? `<p class="muted" id="sc-sppi-rules" style="margin:12px 0 0">${esc(L("Collection rules: economy, 1 adult, direct on the own carrier, cheapest fare, the next day if none; packages bed and breakfast, else the cheapest, 4 nights.", "قواعد الجمع: سياحية، بالغ واحد، رحلة مباشرة على الناقل نفسه، أرخص سعر، واليوم التالي إن لم يوجد؛ الباقات مع الإفطار وإلا الأرخص، 4 ليالٍ."))}</p>` : ""}
      </section></div>
      <div id="sc-actors-view" class="stack"${scView === "actors" ? "" : " hidden"}>
        <section class="card"><h2 style="margin-top:0">${esc(L("Apify actors of this project", "Actors المشروع على Apify"))}</h2>
        <p class="muted">${esc(L("The Actors used by the legacy Apify run (Schedules › Legacy). They are not part of the daily method.", "الـ Actors التي يستخدمها تشغيل Apify القديم (الجداول › قديم). ليست جزءاً من الطريقة اليومية."))}</p>
        <div data-slot="actors"></div></section></div>`;
}
// ids the scraper code writes into: keep sc-k-* as the value spans of the KPI cards
function scKpiIds() {
  for (const k of ["total", "active", "inactive", "target"]) { const v = $(`#sc-k-${k}-card [data-v]`); if (v) v.id = `sc-k-${k}`; }
}
function showScraperFrame(route) {
  const r = curRoute; if (!r || r.kind !== "page" || r.page !== "scrapers") return;
  if (route === "list") { if (!$("#sc-list")) { scListFrame(r.pid); scBindList(r.pid); } }
  else { unmountAll(); if (!$('[data-slot="sc-ws"]')) $("#page").innerHTML = `<div data-slot="sc-ws"></div>`; mount("sc-ws", "blk-sc-ws"); }
}
function scBindList(pid) {
  scKpiIds();
  ["sc-q"].forEach((id) => $("#" + id).addEventListener("input", scRenderList));
  ["sc-filter", "sc-state"].forEach((id) => $("#" + id).addEventListener("change", scRenderList));
  $("#sc-list").addEventListener("click", scListClick);
  $("#sc-refresh").onclick = async () => { await Promise.all([scLoad(), scRoutineData(pid, true)]); if (scRoute === "list") scRenderList(); };
  $("#sc-new").onclick = () => go("#" + scHash("new"));
  bindSeg("sc-view", (v) => { scView = v; $("#sc-list-view").hidden = v !== "scrapers"; $("#sc-actors-view").hidden = v !== "actors"; if (v === "actors") scActors(pid); });
  if (scView === "actors") scActors(pid);
  $("#sc-list").addEventListener("click", (e) => { if (e.target.closest("#sc-retry")) { scLoaded = false; scLoad().then(() => scRoute === "list" && scRenderList()); } });
}
function scActors(pid) {
  const slot = $('[data-slot="actors"]'); if (!slot) return;
  if (!projects[pid]) { slot.innerHTML = emptyHtml("chip", L("No project document yet", "لا يوجد مستند للمشروع بعد"), L("Actors are kept on the project document, which does not exist for this project yet.", "تُحفظ الـ Actors في مستند المشروع، وهو غير موجود لهذا المشروع بعد.")); return; }
  mount("actors", "blk-actors"); renderActors();
}
// the data the routine rows need (latest run log, basket, catalogue; TrendX days; SPPI meta)
let scRoutineErr = null;      // { pid, e } when the routine data of a project could not be read (SPPI meta)
async function scRoutineData(pid, fresh) {
  if (scRoutineErr?.pid === pid) scRoutineErr = null;
  try {
    if (pid === "cpi") await Promise.allSettled([ensureRuns("cpi", fresh), ensureBasket("cpi"), catalogueLatest()]);   // one failed read must not cut the others short
    else if (pid === "te") await teDays();
    else if (pid === "sppi") await sppiLoad(fresh);
  } catch (e) { scRoutineErr = { pid, e }; /* the routine rows show "—"; the list shows the pink box */ }
}
async function pgScrapers(r, seq) {
  const pid = r.pid; scProj = pid;
  const route = r.sub ? (r.sub === "new" ? "new" : r.sub) : "list";
  if (route === "list") {
    scListFrame(pid); scBindList(pid);
    scRoute = null; await scGo("list", { force: true });
    await scRoutineData(pid);
    if (alive(seq) && scRoute === "list") scRenderList();
    return;
  }
  // the workspace needs the outlet list of the project (SPPI from meta)
  if (pid === "sppi") await scRoutineData(pid);
  if (!alive(seq)) return;
  const draft = pendingDraft; pendingDraft = null;
  scRoute = null;
  await scGo(route, { force: true, draft });
}

// ============================================================ Project settings (sidebar footer, #<p>-settings)
function pgSettings(r, seq) {
  const pid = r.pid;
  $("#page").innerHTML = titleRow(L("Project settings", "إعدادات المشروع")) + `<section class="card" id="set-card"><div data-slot="settings"></div></section>`;
  if (!projects[pid]) {
    $("#set-card").innerHTML = emptyHtml("settings", L("No data yet", "لا بيانات بعد"), pid === "sppi" ? L("SPPI has no project document yet. Its basket is kept in Price History › Commodities.", "لا يوجد مستند لمشروع SPPI بعد. تُحفظ سلته في سجل الأسعار › السلع.") : L("This project has no document yet.", "لا يوجد مستند لهذا المشروع بعد."));
    return;
  }
  mount("settings", "blk-settings"); renderSettings();
}
