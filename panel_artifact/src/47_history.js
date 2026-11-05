
// ============================================================ Price History (34.png, 20.png): filter row, PriceGrid, manual entry
const MAX_SPAN = 15;
function pgHistory(r, seq) {
  const pid = r.pid, p = routeOf(pid);
  const right = `<a class="link-btn" id="ph-commodities" href="#${p}-price-history/commodities">${esc(L("Commodities", "السلع"))} ${ico("listico")}</a>`;
  const lbl = (id, t, icon) => `<label class="fl" for="${id}">${esc(t)}${icon ? ico(icon) : ""}</label>`;
  let filters;
  if (pid === "sppi") filters = `<div class="form-grid" style="align-items:end">
      <div class="fld">${lbl("ph-survey", L("Survey", "المسح"))}<select id="ph-survey"><option value="tickets-domestic">${esc(L("Tickets · domestic carriers", "التذاكر · الناقلات المحلية"))}</option><option value="tickets-foreign">${esc(L("Tickets · foreign carriers", "التذاكر · الناقلات الأجنبية"))}</option><option value="packages">${esc(L("Packages", "الباقات"))}</option></select></div>
      <div class="fld">${lbl("ph-month", L("Month", "الشهر"), "calendar")}<select id="ph-month"></select></div>
      <div class="fld">${lbl("ph-outlet", L("Outlet", "المنفذ"))}<select id="ph-outlet"><option value="">${esc(L("All outlets", "كل المنافذ"))}</option></select></div>
      <div class="row" style="flex-wrap:nowrap"><button class="sq" type="button" id="ph-reset" aria-label="${esc(L("Reset filters", "إعادة الضبط"))}" title="${esc(L("Reset filters", "إعادة الضبط"))}">${ico("reset")}</button><button class="primary" type="button" id="ph-apply" aria-describedby="ph-hint">${esc(L("Apply Filter", "تطبيق التصفية"))}${ico("funnel")}</button></div></div>
    <fieldset style="border:0;padding:0;margin:0"><legend class="fl">${esc(L("Collections", "مرات الجمع"))}</legend><div class="picks" id="ph-weeks"></div></fieldset>
    <p class="muted" id="ph-hint" style="text-align:center;margin:0">${ico("info")} ${esc(L("Collections of the selected month", "مرات جمع الشهر المختار"))}</p>`;
  else filters = `<div class="form-grid" style="align-items:end;grid-template-columns:repeat(auto-fit,minmax(min(100%,190px),1fr))">
      <div class="fld">${lbl("ph-outlet", L("Outlet", "المنفذ"))}<select id="ph-outlet"></select></div>
      <div class="fld">${lbl("ph-from", L("Date From", "من تاريخ"), "calendar")}<input type="date" id="ph-from" dir="ltr"></div>
      <div class="fld">${lbl("ph-to", L("Date To", "إلى تاريخ"), "calendar")}<input type="date" id="ph-to" dir="ltr"></div>
      <div class="row" style="flex-wrap:nowrap"><button class="sq" type="button" id="ph-reset" aria-label="${esc(L("Reset filters", "إعادة الضبط"))}" title="${esc(L("Reset filters", "إعادة الضبط"))}">${ico("reset")}</button><button class="primary" type="button" id="ph-apply" aria-describedby="ph-hint">${esc(L("Apply Filter", "تطبيق التصفية"))}${ico("funnel")}</button></div></div>
    <p class="muted" id="ph-hint" style="text-align:center;margin:0">${ico("info")} <span id="ph-hint-t">${esc(L(`Maximum date range is ${MAX_SPAN} days`, `أقصى مدى ${MAX_SPAN} يوماً`))}</span></p>`;
  $("#page").innerHTML = headCard(L("Price History", "سجل الأسعار التاريخي"), `#${p}-dashboard`, right, filters)
    + (pid === "sppi" ? `<div class="row" style="justify-content:flex-end"><button type="button" id="ph-manual">${ico("hand")}${esc(L("Add price manually", "إضافة سعر يدوياً"))}</button></div>` : "")
    + `<section class="card" id="ph-result" aria-live="polite">${emptyHtml("pulse", L("Select an outlet to begin", "اختر منفذاً للبدء"), L("Choose a retail outlet from the dropdown above to view the price history grid.", "اختر منفذاً من القائمة أعلاه لعرض جدول سجل الأسعار."))}</section>`;
  if (pid === "sppi") return historySppi(seq);
  historyDays(pid, seq);
}
function setApply(ok, why) {
  const b = $("#ph-apply"); if (!b) return;
  b.setAttribute("aria-disabled", String(!ok));
  const h = $("#ph-hint"); if (h) h.style.color = why ? "var(--bad)" : "";
  if ($("#ph-hint-t")) $("#ph-hint-t").textContent = why || L(`Maximum date range is ${MAX_SPAN} days`, `أقصى مدى ${MAX_SPAN} يوماً`);
}
// ---------------- CPI and TrendX: days, 15-day maximum
async function historyDays(pid, seq) {
  const sel = $("#ph-outlet");
  sel.innerHTML = (pid === "cpi" ? `<option value="">${esc(L("Select an outlet…", "اختر منفذاً…"))}</option>` : "") + outletOptions(pid).map(([c, n]) => `<option value="${esc(c)}">${esc(n)}</option>`).join("");
  let dayList = [];
  try {
    if (pid === "cpi") dayList = dayRunsOf(await ensureRuns("cpi")).days.map((d) => d.day);
    else dayList = (await teDays()).map((d) => d.day);
  } catch (e) { if (alive(seq)) $("#ph-result").innerHTML = errBox(L("Unable to load price history data right now. ", "تعذّر تحميل بيانات سجل الأسعار الآن. ") + dbErr(e), "ph-retry"); bindRetry(); return; }
  if (!alive(seq)) return;
  const defaults = () => { const last7 = dayList.slice(-7); $("#ph-from").value = last7[0] || todayDubai(); $("#ph-to").value = last7[last7.length - 1] || todayDubai(); if (pid === "cpi") sel.value = ""; };
  defaults();
  const check = () => {
    const f = $("#ph-from").value, t = $("#ph-to").value;
    if (!sel.value) return setApply(false, "");
    if (!f || !t) return setApply(false, L("Choose both dates", "اختر التاريخين"));
    if (t < f) return setApply(false, L("Date To is before Date From", "تاريخ النهاية قبل البداية"));
    if (daySpan(f, t) + 1 > MAX_SPAN) return setApply(false, L(`Maximum date range is ${MAX_SPAN} days (now ${daySpan(f, t) + 1})`, `أقصى مدى ${MAX_SPAN} يوماً (الآن ${daySpan(f, t) + 1})`));
    setApply(true, "");
  };
  ["ph-outlet", "ph-from", "ph-to"].forEach((id) => $("#" + id).addEventListener("change", check));
  $("#ph-from").addEventListener("input", check); $("#ph-to").addEventListener("input", check);
  check();
  $("#ph-reset").onclick = () => { defaults(); check(); $("#ph-result").innerHTML = emptyHtml("pulse", L("Select an outlet to begin", "اختر منفذاً للبدء"), L("Choose a retail outlet from the dropdown above to view the price history grid.", "اختر منفذاً من القائمة أعلاه لعرض جدول سجل الأسعار.")); };
  $("#ph-apply").onclick = () => {
    if ($("#ph-apply").getAttribute("aria-disabled") === "true") { toast(sel.value ? $("#ph-hint").textContent.trim() : L("Choose an outlet first", "اختر منفذاً أولاً"), true); (sel.value ? $("#ph-from") : sel).focus(); return; }
    const o = sel.value, f = $("#ph-from").value, t = $("#ph-to").value;
    if (matchMedia("(min-width: 900px) and (max-width: 1366px)").matches) setSideCollapsed(true, false);
    (pid === "cpi" ? gridCpi : gridTe)(o, f, t, seq);
  };
  if (pid === "te") $("#ph-apply").click();
}
const calDays = (f, t) => { const out = []; for (let d = f; d <= t; d = dayAdd(d, 1)) out.push(d); return out; };
const colHead = (d) => `<th scope="col" class="num">${esc(fmtDay(d))}<br><span class="muted" style="font-weight:600">${esc(new Date(d + "T12:00:00Z").toLocaleDateString(locale(), { timeZone: "UTC", weekday: "short" }))}</span></th>`;
// ---------------- CPI grid
const cpiGridState = { page: 0, q: "", open: new Set() };
async function gridCpi(outlet, f, t, seq) {
  const box = $("#ph-result");
  const { days } = dayRunsOf(await ensureRuns("cpi")), b = await ensureBasket("cpi");
  const inRange = days.filter((d) => d.day >= f && d.day <= t), cols = calDays(f, t);
  const data = {};               // day -> { run, blocked, rows: Map(item -> row) }
  for (let i = 0; i < inRange.length; i++) {
    if (!alive(seq)) return;
    box.innerHTML = loadingHtml(L(`Reading ${i + 1} of ${inRange.length} days…`, `يُقرأ اليوم ${i + 1} من ${inRange.length}…`));
    const { day, run } = inRange[i];
    let rows; try { rows = await runRows("cpi", run); } catch (e) { box.innerHTML = errBox(L("Unable to load price history data right now. ", "تعذّر تحميل بيانات سجل الأسعار الآن. ") + dbErr(e), "ph-retry"); $("#ph-retry").onclick = () => gridCpi(outlet, f, t, seq); return; }
    const blocked = cpiBlockedSet(run).has(outlet), m = new Map();
    for (const x of rows) { if (x.retailer !== outlet) continue; const cur = m.get(x.item_code); if (!cur || (x.accepted === "yes" && cur.accepted !== "yes")) m.set(x.item_code, x); }
    data[day] = { run, blocked, rows: m };
  }
  const manual = {};
  try { for (const d of cols) { const doc = await getDocStrict(`projects/cpi/manual/${d}`); manual[d] = { raw: doc ? JSON.stringify(doc) : null, doc, rows: (doc?.rows || []).filter((x) => x.outlet === outlet && x.status !== "withdrawn") }; } }
  catch (e) { if (alive(seq)) { box.innerHTML = errBox(L("Unable to load the manual prices right now. ", "تعذّر تحميل الأسعار اليدوية الآن. ") + dbErr(e), "ph-retry"); $("#ph-retry").onclick = () => gridCpi(outlet, f, t, seq); } return; }
  if (!alive(seq)) return;
  const bByCode = new Map(b.map((i) => [i.item_code, i]));
  const codes = [...new Set([...Object.values(data).flatMap((d) => [...d.rows.keys()]), ...Object.values(manual).flatMap((m) => m.rows.map((x) => x.line_code))])].filter(Boolean);
  const lines = codes.map((c) => bByCode.get(c) || { item_code: c, name_ar: c, group_code: "?", group_name: "?" }).sort((a, b2) => String(a.item_code).localeCompare(String(b2.item_code)));
  cpiGridState.page = 0; cpiGridState.q = "";
  const ctx = { outlet, f, t, cols, data, manual, lines, seq };
  drawCpiGrid(ctx);
}
function cpiCell(ctx, line, d) {
  const dd = ctx.data[d], man = ctx.manual[d]?.rows.find((x) => x.line_code === line.item_code);
  if (man) return { kind: "manual", price: man.regular_price ?? man.price, offer: man.price, row: man };
  if (!dd) return { kind: "norun" };
  const x = dd.rows.get(line.item_code);
  if (dd.blocked && (!x || x.accepted !== "yes" || x.source === "category")) return { kind: "blocked", carried: x?.source === "category" && x?.accepted === "yes" };
  if (!x) return { kind: "notfound" };
  if (x.in_stock === "no" || x.in_stock === false || x.in_stock === "false") return { kind: "oos", row: x };
  if (x.accepted !== "yes") return { kind: "notfound", row: x };
  const reg = regPrice(x), pr = num(x.price);
  return { kind: "price", price: reg, offer: pr != null && reg != null && Math.abs(pr - reg) > 1e-9 ? pr : null, row: x, mark: line.match_mode && ({ barcode: "barcode", spec: "category", name: "catalogue" }[line.match_mode] || line.match_mode) !== x.source && !(line.match_mode === "name" && x.source === "name_search") ? x.source : "" };
}
function drawCpiGrid(ctx) {
  const box = $("#ph-result"); if (!box) return;
  const q = cpiGridState.q.toLowerCase();
  const lines = ctx.lines.filter((l) => !q || [l.item_code, l.name_ar, l.group_name, l.brand_ar].join(" ").toLowerCase().includes(q));
  const PER = 50, pages = Math.max(1, Math.ceil(lines.length / PER)); cpiGridState.page = Math.min(cpiGridState.page, pages - 1);
  const pageLines = lines.slice(cpiGridState.page * PER, (cpiGridState.page + 1) * PER);
  const ml = MODE_LABEL();
  const groups = []; for (const l of pageLines) { const g = l.group_name || l.group_code; let G = groups.find((x) => x.g === g); if (!G) groups.push(G = { g, lines: [] }); G.lines.push(l); }
  const cellHtml = (l, d) => {
    const c = cpiCell(ctx, l, d), key = `${l.item_code}|${d}`;
    if (c.kind === "norun") return `<td class="nr">${esc(L("No run", "لا تشغيل"))}</td>`;
    if (c.kind === "blocked") return `<td class="blk"><button type="button" data-man="${esc(key)}" title="${esc(L("Blocked: the site refused our pages. Add the price manually.", "محجوب: رفض الموقع صفحاتنا. أضف السعر يدوياً."))}">${esc(c.carried ? L("Blocked (carried)", "محجوب (منقول)") : L("Blocked", "محجوب"))}</button></td>`;
    if (c.kind === "manual") return `<td class="cell cellbtn"><button type="button" data-man="${esc(key)}" title="${esc(L("Manual price; select to edit or withdraw", "سعر يدوي؛ اختر للتعديل أو السحب"))}"><span class="p">${fmtN(c.price, 2)}</span><span class="chip manual">${esc(L("Manual", "يدوي"))}</span></button></td>`;
    if (c.kind === "oos") return `<td class="na">${esc(L("Out of stock", "غير متوفر"))}</td>`;
    if (c.kind === "notfound") return `<td class="na" title="${esc(L("Not found", "غير موجود"))}">—<span class="sr-only">${esc(L("Not found", "غير موجود"))}</span></td>`;
    return `<td class="cell" title="${esc([c.row?.title, c.row?.detail, c.row?.url].filter(Boolean).join(" · "))}"><span class="p">${fmtN(c.price, 2)}</span>${c.offer != null ? `<span class="o">${esc(L("Offer", "عرض"))} ${fmtN(c.offer, 2)}</span>` : ""}${c.mark ? `<span class="tag">${esc(c.mark)}</span>` : ""}</td>`;
  };
  const rowHtml = (l) => {
    const cells = ctx.cols.map((d) => cpiCell(ctx, l, d)), vals = cells.map((c) => (c.kind === "price" ? c.price : null));
    const tierB = ctx.cols.some((d) => isTierB(ctx.data[d]?.rows.get(l.item_code) || {})) && !ctx.cols.some((d) => isExact(ctx.data[d]?.rows.get(l.item_code) || {}));
    return `<tr class="${tierB ? "muted-row" : ""}"><th scope="row" class="stick"><span class="mono">${esc(l.item_code)}</span> <span class="nm" dir="auto">${esc(l.name_ar || "")}</span><br><span class="sub-l" dir="auto">${esc(l.qty_raw || "")}</span> <span class="tag">${esc(ml[l.match_mode] || l.match_mode || "—")}</span>${tierB ? ` <span class="chip grey">${esc(L("Not index-grade", "ليس بدرجة المؤشر"))}</span>` : ""}</th>
      ${ctx.cols.map((d) => cellHtml(l, d)).join("")}<td class="ltr">${sparkline(vals)}</td></tr>`;
  };
  const body = groups.map((G) => { const open = !cpiGridState.open.has("x" + G.g);
    return `<tr class="grp" data-grp="${esc(G.g)}"><td class="stick" colspan="1"><button type="button" class="link-btn" style="font-size:14px;min-height:0;padding:0" aria-expanded="${open}" data-grp="${esc(G.g)}">${open ? ico("chevd") : ico("chevr", "flip")} <span dir="auto">${esc(G.g)}</span> (${G.lines.length})</button></td><td colspan="${ctx.cols.length + 1}"></td></tr>${open ? G.lines.map(rowHtml).join("") : ""}`; }).join("");
  box.innerHTML = `<div class="card-h"><h2>${esc(outletEn(ctx.outlet))} · ${esc(fmtDay(ctx.f))} – ${esc(fmtDay(ctx.t))}</h2><span class="spacer"></span>
      <button type="button" id="ph-xlsx">${ico("download")}Excel</button><button type="button" id="ph-csv">${ico("download")}CSV</button></div>
    <div class="row"><label class="search" style="position:relative;flex:1 1 280px"><span class="sr-only">${esc(L("Search lines", "ابحث في البنود"))}</span><input id="ph-search" type="search" value="${esc(cpiGridState.q)}" placeholder="${esc(L("Search by code, name or group", "ابحث بالرمز أو الاسم أو المجموعة"))}"></label><span class="muted">${esc(L(`${fmtN(lines.length)} lines with rows for this outlet`, `${fmtN(lines.length)} بنداً لها صفوف لهذا المنفذ`))}</span></div>
    <div class="tw tall"><table class="pgrid" id="ph-grid"><caption class="sr-only">${esc(L("Price history grid", "جدول سجل الأسعار"))}</caption><thead><tr><th scope="col" class="stick">${esc(L("Line (code, name, unit, method)", "البند (الرمز، الاسم، الوحدة، الطريقة)"))}</th>${ctx.cols.map(colHead).join("")}<th scope="col">${esc(L("Trend", "الاتجاه"))}</th></tr></thead><tbody>${body || `<tr><td colspan="${ctx.cols.length + 2}">${emptyHtml("pulse", L("No prices for this outlet in this range", "لا أسعار لهذا المنفذ في هذا المدى"), "")}</td></tr>`}</tbody></table></div>
    <div class="pager"><button type="button" id="ph-prev">${esc(L("Previous", "السابق"))}</button><span class="muted">${cpiGridState.page + 1} / ${pages}</span><button type="button" id="ph-next">${esc(L("Next", "التالي"))}</button></div>
    <p class="muted" style="margin:0">${esc(L("Regular price large, offer price small. Blocked: the site refused our pages that day (carried rows are not prices). No run: no collection that day. —: not found. Select a Blocked cell to add the price by hand; manual prices are not used by the CPI monitor.", "السعر العادي كبير، وسعر العرض صغير. محجوب: رفض الموقع صفحاتنا ذلك اليوم (الصفوف المنقولة ليست أسعاراً). لا تشغيل: لا جمع ذلك اليوم. —: غير موجود. اختر خلية محجوبة لإضافة السعر يدوياً؛ الأسعار اليدوية لا تدخل في المؤشر الداخلي."))}</p>`;
  $("#ph-search").oninput = (e) => { cpiGridState.q = e.target.value; cpiGridState.page = 0; const pos = e.target.selectionStart; drawCpiGrid(ctx); const s = $("#ph-search"); s.focus(); try { s.setSelectionRange(pos, pos); } catch (x) {} };
  $("#ph-prev").onclick = () => { cpiGridState.page = Math.max(0, cpiGridState.page - 1); drawCpiGrid(ctx); };
  $("#ph-next").onclick = () => { cpiGridState.page++; drawCpiGrid(ctx); };
  $("#ph-grid").onclick = (e) => {
    const g = e.target.closest("button[data-grp]"); if (g) { const k = "x" + g.dataset.grp; cpiGridState.open.has(k) ? cpiGridState.open.delete(k) : cpiGridState.open.add(k); return drawCpiGrid(ctx); }
    const m = e.target.closest("[data-man]"); if (m) { const [code, d] = m.dataset.man.split("|"); cpiManualCard(ctx, ctx.lines.find((l) => l.item_code === code), d); }
  };
  const sheet = () => {
    const txt = (c) => c.kind === "price" ? c.price : c.kind === "manual" ? c.price : { norun: "No run", blocked: c.carried ? "Blocked (carried)" : "Blocked", oos: "Out of stock", notfound: "Not found" }[c.kind];
    return { title: `CPI price history · ${outletEn(ctx.outlet)}`, subtitle: `${ctx.f} to ${ctx.t} • regular price • manual prices marked`, headers: ["Code", "Name", "Unit", "Method", ...ctx.cols, "Manual days"],
      widths: [12, 40, 12, 14, ...ctx.cols.map(() => 12), 16], priceCols: ctx.cols.map((_, i) => i + 5),
      rows: lines.map((l) => { const cs = ctx.cols.map((d) => cpiCell(ctx, l, d)); return [l.item_code, l.name_ar || "", l.qty_raw || "", l.match_mode || "", ...cs.map(txt), ctx.cols.filter((d, i) => cs[i].kind === "manual").join(" ")]; }) };
  };
  $("#ph-xlsx").onclick = () => offerXlsx(`CPI ${ctx.outlet} ${ctx.f}_${ctx.t}.xlsx`, sheet());
  $("#ph-csv").onclick = () => { const s = sheet(); offerFile(`CPI ${ctx.outlet} ${ctx.f}_${ctx.t}.csv`, toCsv(s.rows.map((r) => Object.fromEntries(s.headers.map((h, i) => [h, r[i]]))), s.headers)); };
}
// manual entry for a CPI cell: projects/cpi/manual/<YYYY-MM-DD> {rows:[...]}, read-modify-write with a version check
function cpiManualCard(ctx, line, d) {
  if (!line) return;
  const cur = ctx.manual[d]?.rows.find((x) => x.line_code === line.item_code);
  openSidePanel(L("Add price manually", "إضافة سعر يدوياً"), `<form id="mc-form" class="stack" novalidate>
    <dl class="kv"><dt>${esc(L("Line", "البند"))}</dt><dd><span class="mono">${esc(line.item_code)}</span> <span dir="auto">${esc(line.name_ar || "")}</span></dd><dt>${esc(L("Outlet", "المنفذ"))}</dt><dd>${esc(outletEn(ctx.outlet))}</dd><dt>${esc(L("Date", "التاريخ"))}</dt><dd>${esc(fmtDay(d, { year: true }))}</dd></dl>
    <p class="muted" style="margin:0">${esc(L("Saved with source “manual”. Nothing is prefilled from another day. Manual prices are not used by the CPI monitor.", "يُحفظ بالمصدر «يدوي». لا يُملأ شيء من يوم آخر. الأسعار اليدوية لا تدخل في المؤشر الداخلي."))}</p>
    <div class="form-grid"><label class="f"><span>${esc(L("Price (AED)", "السعر (درهم)"))} *</span><input id="mc-price" inputmode="decimal" dir="ltr" value="${esc(cur?.price ?? "")}" aria-describedby="mc-err"></label>
    <label class="f"><span>${esc(L("Regular price (AED)", "السعر العادي (درهم)"))}</span><input id="mc-reg" inputmode="decimal" dir="ltr" value="${esc(cur?.regular_price ?? "")}"></label>
    <label class="f"><span>${esc(L("Unit", "الوحدة"))}</span><input id="mc-unit" dir="auto" value="${esc(cur?.unit ?? "")}" placeholder="${esc(line.qty_raw || "")}"></label></div>
    <label class="f"><span>${esc(L("Product URL", "رابط المنتج"))}</span><input id="mc-url" dir="ltr" value="${esc(cur?.url ?? "")}"></label>
    <label class="f"><span>${esc(L("Note (or screenshot ref / URL)", "ملاحظة (أو مرجع لقطة الشاشة / رابط)"))}</span><textarea id="mc-note" rows="3">${esc(cur?.note ?? "")}</textarea></label>
    <div id="mc-box"></div><p class="f-err" id="mc-err" hidden></p>
    <div class="row"><button class="primary" type="submit" id="mc-save">${esc(L("Save", "حفظ"))}</button>${cur ? `<button type="button" class="danger" id="mc-withdraw">${esc(L("Withdraw", "سحب"))}</button>` : ""}<button type="button" id="mc-cancel">${esc(L("Cancel", "إلغاء"))}</button></div></form>`, () => {
    $("#mc-cancel").onclick = closeSidePanel;
    const write = async (mutate) => {
      const path = `projects/cpi/manual/${d}`;
      if (!ctx.manual[d]) { $("#mc-box").innerHTML = errBox(L("The manual prices of this day were not read, so nothing was written. Reload and retry.", "لم تُقرأ الأسعار اليدوية لهذا اليوم، لذلك لم يُكتب شيء. أعد التحميل وحاول."), "mc-reload"); $("#mc-reload").onclick = () => { closeSidePanel(); $("#ph-apply").click(); }; return false; }
      const now = await getDocStrict(path);   // a failed read throws: no write
      if ((now ? JSON.stringify(now) : null) !== ctx.manual[d].raw) { $("#mc-box").innerHTML = errBox(L("These manual prices changed since you opened the grid. Reload and retry; nothing was overwritten.", "تغيّرت هذه الأسعار اليدوية منذ فتح الجدول. أعد التحميل وحاول؛ لم يُستبدل شيء."), "mc-reload"); $("#mc-reload").onclick = () => { closeSidePanel(); $("#ph-apply").click(); }; return false; }
      const doc = now || { rows: [] }, rows = [...(doc.rows || [])];
      mutate(rows);
      const next = { ...doc, rows, version: (doc.version || 0) + 1 };
      await db.doc(path).set(next);
      ctx.manual[d] = { raw: JSON.stringify(next), doc: next, rows: rows.filter((x) => x.outlet === ctx.outlet && x.status !== "withdrawn") };
      return true;
    };
    const mcFail = (x, again) => { $("#mc-err").hidden = true; $("#mc-box").innerHTML = errBox(L("Not saved: nothing was written. ", "لم يُحفظ: لم يُكتب شيء. ") + dbErr(x), "mc-retry"); $("#mc-retry").onclick = again; };
    $("#mc-form").onsubmit = async (e) => {
      e.preventDefault();
      const pr = $("#mc-price").value.trim(), rg = $("#mc-reg").value.trim(), err = $("#mc-err");
      const bad = !/^\d+(\.\d+)?$/.test(pr) || !(+pr > 0) ? L("Price: a number above 0 (AED).", "السعر: رقم أكبر من 0 (درهم).") : rg && (!/^\d+(\.\d+)?$/.test(rg) || !(+rg > 0)) ? L("Regular price: a number above 0, or leave it empty.", "السعر العادي: رقم أكبر من 0، أو اتركه فارغاً.") : "";
      err.hidden = !bad; err.textContent = bad; if (bad) return $("#mc-price").focus();
      const row = { line_code: line.item_code, outlet: ctx.outlet, price: +pr, regular_price: rg ? +rg : +pr, unit: $("#mc-unit").value.trim(), url: $("#mc-url").value.trim(), note: $("#mc-note").value.trim(),
        entered_by: viewerName(), entered_at: new Date().toISOString(), source: "manual", currency: "AED", status: "ok" };
      try { if (await write((rows) => { const i = rows.findIndex((x) => x.line_code === row.line_code && x.outlet === row.outlet && x.status !== "withdrawn"); if (i >= 0) rows[i] = { ...rows[i], ...row }; else rows.push(row); })) { closeSidePanel(); toast(L("Manual price saved", "حُفظ السعر اليدوي")); drawCpiGrid(ctx); } }
      catch (x) { mcFail(x, () => $("#mc-form").requestSubmit()); }
    };
    $("#mc-withdraw")?.addEventListener("click", async () => {
      try { if (await write((rows) => { const i = rows.findIndex((x) => x.line_code === line.item_code && x.outlet === ctx.outlet && x.status !== "withdrawn"); if (i >= 0) rows[i] = { ...rows[i], status: "withdrawn", withdrawn_at: new Date().toISOString() }; })) { closeSidePanel(); toast(L("Manual price withdrawn", "سُحب السعر اليدوي")); drawCpiGrid(ctx); } }
      catch (x) { mcFail(x, () => $("#mc-withdraw").click()); }
    });
  });
}
function viewerName() { return viewerCache || "manual"; }
let viewerCache = "";
// ---------------- TrendX grid (+ Index tab)
async function gridTe(outlet, f, t, seq) {
  const box = $("#ph-result"); box.innerHTML = loadingHtml(L("Reading the days…", "تُقرأ الأيام…"));
  const all = await teDays(); if (!alive(seq)) return;
  const days = all.filter((d) => d.day >= f && d.day <= t), cols = calDays(f, t), byDay = Object.fromEntries(days.map((d) => [d.day, new Map(d.rows.map((x) => [teKey(x), x]))]));
  const keys = [...new Map(days.flatMap((d) => d.rows).map((x) => [teKey(x), x])).values()].sort((a, b) => a.category.localeCompare(b.category) || a.commodity.localeCompare(b.commodity));
  const state = { tab: "prices", cat: "", q: "" };
  const draw = () => {
    if (state.tab === "index") return drawTeIndex(all, f, t);
    const list = keys.filter((k) => (!state.cat || k.category === state.cat) && (!state.q || [k.commodity, k.category].join(" ").toLowerCase().includes(state.q.toLowerCase())));
    const cats = [...new Set(list.map((k) => k.category))];
    $("#ph-te-body").innerHTML = `<div class="tw tall"><table class="pgrid" id="ph-grid"><caption class="sr-only">${esc(L("TrendX price grid", "جدول أسعار TrendX"))}</caption><thead><tr><th scope="col" class="stick">${esc(L("Commodity (category, unit)", "السلعة (الفئة، الوحدة)"))}</th>${cols.map(colHead).join("")}<th scope="col" class="num">${esc(L("Change over range", "التغير خلال المدى"))}</th><th scope="col">${esc(L("Trend", "الاتجاه"))}</th></tr></thead><tbody>
      ${cats.map((c) => `<tr class="grp"><td class="stick">${esc(teCatName(c))}${TE_EXCL.includes(c) ? ` <span class="chip grey">${esc(L("not in index", "خارج المؤشر"))}</span>` : ""}</td><td colspan="${cols.length + 2}"></td></tr>` + list.filter((k) => k.category === c).map((k) => {
        const vals = cols.map((d) => byDay[d]?.get(teKey(k)) || null), ps = vals.map((x) => (x ? Number(x.price) : null)), nn = ps.filter((v) => v != null);
        const chg = nn.length > 1 ? (nn[nn.length - 1] / nn[0] - 1) * 100 : null;
        return `<tr><th scope="row" class="stick"><span class="nm">${esc(k.commodity)}</span><br><span class="sub-l ltr">${esc(k.unit)}</span></th>${cols.map((d, i) => {
          const x = vals[i]; if (!byDay[d]) return `<td class="nr">${esc(L("No run", "لا تشغيل"))}</td>`; if (!x) return `<td class="na">—<span class="sr-only">${esc(L("Not found", "غير موجود"))}</span></td>`;
          const stale = x.price_date && x.price_date < d, old = x.price_date && daySpan(x.price_date, d) > 7;
          return `<td class="cell${stale ? " stale" : ""}" title="${esc(stale ? L(`Stale quote: the source's price date is ${x.price_date}`, `تسعيرة قديمة: تاريخ سعر المصدر ${x.price_date}`) : L(`Quote date ${x.price_date || "—"}`, `تاريخ التسعيرة ${x.price_date || "—"}`))}"><span class="p">${stale ? ico("clock") + " " : ""}${esc(String(x.price))}</span>${old ? `<span class="chip warn">${esc(L("Stale", "قديم"))} ${esc(fmtDay(x.price_date))}</span>` : ""}</td>`; }).join("")}
          <td class="num ${chg > 0 ? "chg-up" : chg < 0 ? "chg-down" : ""}">${chg == null ? "—" : (chg > 0 ? "+" : "") + chg.toFixed(2) + "%"}</td><td class="ltr">${sparkline(ps)}</td></tr>`; }).join("")).join("")}</tbody></table></div>
      <p class="muted" style="margin:0">${esc(L("The close as published by the source. Grey italic with a clock: the quote date is before the run date (hover for it); “Stale”: older than 7 days.", "سعر الإغلاق كما نشره المصدر. رمادي مائل مع ساعة: تاريخ التسعيرة قبل تاريخ التشغيل (مرّر المؤشر لرؤيته)؛ «قديم»: أقدم من 7 أيام."))}</p>`;
  };
  box.innerHTML = `<div class="card-h"><h2>Trading Economics · ${esc(fmtDay(f))} – ${esc(fmtDay(t))}</h2><span class="spacer"></span>${segToggle("ph-tab", [["prices", L("Prices", "الأسعار")], ["index", L("Index", "المؤشر")]], "prices", L("View", "العرض"))}
      <button type="button" id="ph-xlsx">${ico("download")}Excel</button><button type="button" id="ph-csv">${ico("download")}CSV</button></div>
    <div class="filter-card" id="ph-te-filters"><select id="ph-cat" aria-label="${esc(L("Category", "الفئة"))}"><option value="">${esc(L("All categories", "كل الفئات"))}</option>${[...new Set(keys.map((k) => k.category))].map((c) => `<option value="${esc(c)}">${esc(teCatName(c))}</option>`).join("")}</select>
      <label class="search"><span class="sr-only">${esc(L("Search commodities", "ابحث في السلع"))}</span>${ico("search")}<input id="ph-search" type="search" placeholder="${esc(L("Search commodities", "ابحث في السلع"))}"></label></div>
    <div id="ph-te-body"></div>`;
  bindSeg("ph-tab", (v) => { state.tab = v; $("#ph-te-filters").hidden = v === "index"; draw(); });
  $("#ph-cat").onchange = (e) => { state.cat = e.target.value; draw(); };
  $("#ph-search").oninput = (e) => { state.q = e.target.value; draw(); };
  const sheet = () => state.tab === "index" ? teIndexSheet(all, f, t) : { title: "TrendX prices", subtitle: `${f} to ${t} • close as published; stale quotes keep their price_date`, headers: ["Category", "Commodity", "Unit", ...cols.flatMap((d) => [d, `${d} price_date`])],
    widths: [16, 30, 16, ...cols.flatMap(() => [12, 12])], priceCols: cols.map((_, i) => 4 + i * 2),
    rows: keys.map((k) => [k.category, k.commodity, k.unit, ...cols.flatMap((d) => { const x = byDay[d]?.get(teKey(k)); return [x ? Number(x.price) : byDay[d] ? "Not found" : "No run", x?.price_date || ""]; })]) };
  $("#ph-xlsx").onclick = () => offerXlsx(`TrendX ${state.tab} ${f}_${t}.xlsx`, sheet());
  $("#ph-csv").onclick = () => { const s = sheet(); offerFile(`TrendX ${state.tab} ${f}_${t}.csv`, toCsv(s.rows.map((r) => Object.fromEntries(s.headers.map((h, i) => [h, r[i]]))), s.headers)); };
  draw();
}
function teIndexSheet(all, f, t) {
  const sers = ["All", ...TE_CATS].map((c) => [c, teIndex(all, c)]);
  const days = all.map((d) => d.day).filter((d) => d >= f && d <= t);
  return { title: "TrendX Index (2 Oct 2026 = 100)", subtitle: `${f} to ${t} • chained Jevons • Electricity and Index excluded`, headers: ["Date", ...sers.flatMap(([c]) => [`${c} level`, `${c} % change`])], widths: [12, ...sers.flatMap(() => [12, 12])], priceCols: [],
    rows: days.map((d) => [d, ...sers.flatMap(([, s]) => { const i = s.findIndex((p) => p.x === d); return [i >= 0 ? +s[i].y.toFixed(3) : null, i > 0 ? +((s[i].y / s[i - 1].y - 1) * 100).toFixed(3) : null]; })]) };
}
function drawTeIndex(all, f, t) {
  const s = teIndexSheet(all, f, t);
  $("#ph-te-body").innerHTML = `<div class="tw"><table><caption class="sr-only">${esc(L("TrendX Index by day", "مؤشر TrendX حسب اليوم"))}</caption><thead><tr>${s.headers.map((h, i) => `<th scope="col"${i ? ' class="num"' : ""}>${esc(i ? h.replace(/^(\w+)/, (m) => teCatName(m)).replace("level", L("level", "المستوى")).replace("% change", L("% change", "% التغير")) : L("Date", "التاريخ"))}</th>`).join("")}</tr></thead><tbody>${s.rows.map((r) => `<tr><th scope="row">${esc(fmtDay(r[0]))}</th>${r.slice(1).map((v, i) => `<td class="num${i % 2 && v > 0 ? " chg-up" : i % 2 && v < 0 ? " chg-down" : ""}">${v == null ? "—" : i % 2 ? (v > 0 ? "+" : "") + v.toFixed(2) + "%" : v.toFixed(2)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
