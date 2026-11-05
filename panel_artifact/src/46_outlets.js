
// ============================================================ Outlets (33.png)
function pgOutlets(r, seq, opts = {}) {
  const pid = r.pid;
  const weekSel = pid === "sppi" ? `<select id="ol-week" aria-label="${esc(L("Collection for the working state", "الجمع لحالة العمل"))}"></select>` : "";
  $("#page").innerHTML = titleRow(L("Outlet Management", "إدارة المنافذ"), `<button class="primary" type="button" id="ol-create">${ico("plus")}${esc(L("Create outlet", "إنشاء منفذ"))}</button>`)
    + `<div class="kpis four">
      ${kpiHtml({ id: "ol-kpi-total", icon: "bag", label: L("Total outlets", "إجمالي المنافذ") })}
      ${kpiHtml({ id: "ol-kpi-working", icon: "check", tint: "green", label: L("Working outlets", "منافذ تعمل") })}
      ${kpiHtml({ id: "ol-kpi-failed", icon: "warn", tint: "red", label: L("Failed outlets", "منافذ متعثرة") })}
      ${kpiHtml({ id: "ol-kpi-required", icon: "hex", tint: "amber", label: L("Required items", "البنود المطلوبة") })}</div>
    <section class="card"><div class="filter-card">
      <label class="search"><span class="sr-only">${esc(L("Search outlets", "ابحث في المنافذ"))}</span>${ico("search")}<input id="ol-search" type="search" placeholder="${esc(L("Search by code, English name, or Arabic name", "ابحث بالرمز أو الاسم الإنجليزي أو العربي"))}"></label>
      <select id="ol-status" aria-label="${esc(L("Status", "الحالة"))}"><option value="">${esc(L("All statuses", "كل الحالات"))}</option><option value="active">${esc(L("Active", "فعّال"))}</option><option value="inactive">${esc(L("Inactive", "غير فعّال"))}</option></select>
      <select id="ol-state" aria-label="${esc(L("Working state", "حالة العمل"))}"><option value="">${esc(L("All working states", "كل حالات العمل"))}</option>${Object.keys(STATE).map((k) => `<option value="${k}">${esc(stateText(k))}</option>`).join("")}</select>
      ${weekSel}
      <button class="sq" type="button" id="ol-refresh" aria-label="${esc(L("Refresh", "تحديث"))}" title="${esc(L("Refresh", "تحديث"))}">${ico("refresh")}</button></div>
      <div id="ol-body">${loadingHtml(L("Loading outlets…", "تُحمَّل المنافذ…"))}</div></section>`;
  let rows = [];
  const draw = () => {
    const q = $("#ol-search").value.trim().toLowerCase(), sf = $("#ol-status").value, wf = $("#ol-state").value;
    const list = rows.filter((o) => (!sf || (sf === "active") === (o.status !== "inactive")) && (!wf || o.state === wf) && (!q || [o.code, o.en, o.ar].join(" ").toLowerCase().includes(q)));
    const extraH = pid === "cpi" ? `<th scope="col">${esc(L("Sources", "المصادر"))}</th>` : pid === "sppi" ? `<th scope="col">${esc(L("Kind", "النوع"))}</th><th scope="col">${esc(L("Market", "السوق"))}</th><th scope="col">${esc(L("Access", "الوصول"))}</th>` : `<th scope="col">${esc(L("Fetch method", "طريقة الجلب"))}</th><th scope="col">${esc(L("Missing basket items", "بنود ناقصة"))}</th>`;
    const extra = (o) => pid === "cpi" ? `<td>${esc(o.sources || "—")}</td>` : pid === "sppi" ? `<td>${esc(o.kind || "—")}</td><td>${esc(o.market || "—")}</td><td>${o.access ? chip(o.access === "auto" ? "Auto" : o.access === "pc_only" ? "PC run" : "Manual", o.access === "auto" ? "blue" : o.access === "pc_only" ? "warn" : "manual") : "—"}</td>` : `<td>${esc(o.method || "—")}</td><td>${o.missing?.length ? esc(o.missing.join(", ")) : esc(L("none", "لا شيء"))}</td>`;
    const ncol = pid === "cpi" ? 10 : pid === "sppi" ? 12 : 11;
    $("#ol-body").innerHTML = `<div class="tw"><table id="ol-table"><caption class="sr-only">${esc(L("Outlets", "المنافذ"))}</caption><thead><tr><th scope="col">${esc(L("Code", "الرمز"))}</th><th scope="col">${esc(L("English name", "الاسم الإنجليزي"))}</th><th scope="col">${esc(L("Arabic name", "الاسم العربي"))}</th><th scope="col">${esc(L("Status", "الحالة"))}</th><th scope="col">${esc(L("Working state", "حالة العمل"))}</th><th scope="col" class="num">${esc(L("Prices in latest run", "أسعار آخر تشغيل"))}</th><th scope="col">${esc(L("Last price seen", "آخر سعر مرئي"))}</th><th scope="col">${esc(L("Last read", "آخر قراءة"))}</th><th scope="col" class="num">${esc(L("Required items", "البنود المطلوبة"))}</th>${extraH}</tr></thead><tbody>
      ${list.map((o) => `<tr class="click" tabindex="0" data-code="${esc(o.code)}"><td class="mono">${esc(o.code)}</td><th scope="row" style="font-weight:700">${esc(o.en)}</th><td dir="auto">${esc(o.ar || "—")}</td>
        <td>${o.status === "inactive" ? chip(L("Inactive", "غير فعّال"), "grey") : chip(L("Active", "فعّال"), "ok")}</td><td>${stateChip(o.state, o.reason, o.since)}</td>
        <td class="num">${fmtN(o.prices)}</td><td>${esc(o.lastSeen ? fmtDay(o.lastSeen) : "—")}</td><td>${esc(o.lastRead ? fmtDay(o.lastRead) : "—")}</td><td class="num">${fmtN(o.required)}</td>${extra(o)}</tr>
        ${(o.children || []).map((c) => `<tr class="child"><td></td><td>↳ ${esc(c.en)}</td><td dir="auto">${esc(c.ar)}</td><td colspan="${ncol - 3}">${esc(L(`catalogue: ${fmtN(c.n)} products (part of ${o.en}, not counted again)`, `الكتالوج: ${fmtN(c.n)} منتج (ضمن ${o.en}، لا يُحسب مرة أخرى)`))}</td></tr>`).join("")}`).join("")
      || `<tr><td colspan="${ncol}">${emptyHtml("store", rows.length ? L("No outlet matches the filters", "لا منفذ يطابق التصفية") : L("No outlets yet", "لا منافذ بعد"), rows.length ? "" : pid === "sppi" ? L("SPPI has no outlets in the database yet.", "لا منافذ لـ SPPI في قاعدة البيانات بعد.") : "")}</td></tr>`}</tbody></table></div>`;
  };
  const load = async (fresh) => {
    if (fresh) { delete st(pid).saved; if (pid === "sppi") sppiCache = null; }
    $("#ol-body").innerHTML = loadingHtml(L("Loading outlets…", "تُحمَّل المنافذ…"));
    try {
      if (pid === "sppi" && $("#ol-week") && !$("#ol-week").options.length) {
        const d = await sppiLoad();
        $("#ol-week").innerHTML = (d.weeks || []).map((w) => `<option value="${esc(w.id)}">${esc(`${sppiWeekLabel(w)} · ${fmtMonth(w.month)}`)}</option>`).join("") || `<option value="">${esc(L("No collection", "لا جمع"))}</option>`;
        $("#ol-week").value = d.weeks?.[d.weeks.length - 1]?.id || "";
      }
      rows = await outletRows(pid, { week: $("#ol-week")?.value });
    } catch (e) { if (alive(seq)) { $("#ol-body").innerHTML = errBox(L("Unable to load outlets right now. ", "تعذّر تحميل المنافذ الآن. ") + dbErr(e), "ol-retry"); $("#ol-retry").onclick = () => load(true); } return; }
    if (!alive(seq)) return;
    const none = pid === "sppi" && !sppiCache?.meta && !rows.length;
    setKpi("ol-kpi-total", none ? "—" : fmtN(rows.length));
    setKpi("ol-kpi-working", none ? "—" : fmtN(rows.filter((o) => o.state === "ok").length), L("Read OK", "قُرئ بالكامل"));
    setKpi("ol-kpi-failed", none ? "—" : fmtN(rows.filter((o) => o.state === "blocked" || o.state === "failed").length), L("Blocked or Failed", "محجوب أو فاشل"));
    setKpi("ol-kpi-required", none ? "—" : fmtN(rows.reduce((n, o) => n + (o.required || 0), 0)));
    draw();
  };
  ["ol-search", "ol-status", "ol-state"].forEach((id) => $("#" + id).addEventListener(id === "ol-search" ? "input" : "change", draw));
  $("#ol-week")?.addEventListener("change", () => load(false));
  $("#ol-refresh").onclick = () => load(true);
  const openRow = (code) => { const o = rows.find((x) => x.code === code); if (!o) return;
    openSidePanel(`${o.en} · ${L("latest log", "آخر سجل")}`, `<dl class="kv"><dt>${esc(L("Working state", "حالة العمل"))}</dt><dd>${stateChip(o.state, o.reason, o.since)}</dd><dt>${esc(L("Last read", "آخر قراءة"))}</dt><dd>${esc(o.lastRead ? fmtDay(o.lastRead) : "—")}</dd></dl>
      ${o.log?.length ? `<pre class="log">${esc(o.log.join("\n"))}</pre>` : `<p class="muted">${esc(L("No log lines for this outlet in the latest run.", "لا أسطر لهذا المنفذ في سجل آخر تشغيل."))}</p>`}`); };
  $("#ol-body").addEventListener("click", (e) => { const tr = e.target.closest("tr[data-code]"); if (tr) openRow(tr.dataset.code); });
  $("#ol-body").addEventListener("keydown", (e) => { const tr = e.target.closest("tr[data-code]"); if (tr && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); openRow(tr.dataset.code); } });
  $("#ol-create").onclick = () => openSidePanel(L("Create outlet", "إنشاء منفذ"), `<form id="ol-form" class="stack" novalidate>
      <p class="notice info" style="margin:0">${esc(L("Adds the outlet to this list; it does not start scraping.", "يضيف المنفذ إلى هذه القائمة؛ لا يبدأ السحب."))}</p>
      <label class="f"><span>${esc(L("Code", "الرمز"))} *</span><input id="olf-code" class="mono" dir="ltr" required maxlength="40" aria-describedby="olf-err"></label>
      <label class="f"><span>${esc(L("English name", "الاسم الإنجليزي"))} *</span><input id="olf-en" required maxlength="80"></label>
      <label class="f"><span>${esc(L("Arabic name", "الاسم العربي"))}</span><input id="olf-ar" dir="rtl" maxlength="80"></label>
      <label class="f"><span>${esc(L("Kind", "النوع"))}</span><select id="olf-kind"><option value="retailer">${esc(L("Retailer", "متجر"))}</option><option value="airline">${esc(L("Airline", "طيران"))}</option><option value="travel_agent">${esc(L("Travel agent", "وكيل سفر"))}</option><option value="tour_operator">${esc(L("Tour operator", "منظم رحلات"))}</option><option value="source">${esc(L("Data source", "مصدر بيانات"))}</option></select></label>
      <label class="f"><span>${esc(L("Status", "الحالة"))}</span><select id="olf-status"><option value="active">${esc(L("Active", "فعّال"))}</option><option value="inactive">${esc(L("Inactive", "غير فعّال"))}</option></select></label>
      <p class="f-err" id="olf-err" hidden></p>
      <div class="row"><button class="primary" type="submit" id="olf-save">${esc(L("Save outlet", "حفظ المنفذ"))}</button><button type="button" id="olf-cancel">${esc(L("Cancel", "إلغاء"))}</button></div></form>`, () => {
    $("#olf-cancel").onclick = closeSidePanel;
    $("#ol-form").onsubmit = async (e) => {
      e.preventDefault();
      const code = $("#olf-code").value.trim().toLowerCase(), en = $("#olf-en").value.trim(), err = $("#olf-err");
      const bad = !/^[a-z0-9_-]{2,40}$/.test(code) ? L("Code: 2-40 lowercase letters, digits, _ or -.", "الرمز: 2-40 حرفاً صغيراً أو رقماً أو _ أو -.") : !en ? L("Write the English name.", "اكتب الاسم الإنجليزي.") : rows.some((o) => o.code === code) ? L(`The code “${code}” is already used.`, `الرمز «${code}» مستخدم.`) : "";
      err.hidden = !bad; err.textContent = bad; if (bad) return;
      try {
        await db.doc(`projects/${pid}/outlets/${code}`).set({ code, name_en: en, name_ar: $("#olf-ar").value.trim(), kind: $("#olf-kind").value, status: $("#olf-status").value, created_at: new Date().toISOString() });
        closeSidePanel(); toast(L(`Outlet “${en}” added`, `أُضيف المنفذ «${en}»`)); load(true);
      } catch (x) { err.hidden = false; err.textContent = dbErr(x); }
    };
  });
  load(false);
}
