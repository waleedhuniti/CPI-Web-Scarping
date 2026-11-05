
// ============================================================ SPPI Price History: survey + month + collections, legs and totals, manual entry
const SPPI_FLAGS = ["next_day", "other_hotel", "no_bb", "plus_one_day", "transfer_incl"];
const flagLabel = (f) => ({ next_day: L("next day", "اليوم التالي"), other_hotel: L("other hotel", "فندق بديل"), no_bb: L("no B&B", "بدون إفطار"), plus_one_day: L("+1 day", "+يوم"), transfer_incl: L("transfer incl.", "شامل النقل") }[f] || f);
const isSubst = (r) => (r.flags || []).some((f) => f === "other_hotel" || f === "next_day");
let sppiGrid = null;                      // { survey, month, weeks:[ids], outlet }
async function historySppi(seq) {
  let d;
  try { d = await sppiLoad(); } catch (e) { if (alive(seq)) $("#ph-result").innerHTML = errBox(L("Unable to load price history data right now. ", "تعذّر تحميل بيانات سجل الأسعار الآن. ") + dbErr(e), "ph-retry"); bindRetry(); return; }
  if (!alive(seq)) return;
  if (!d.meta) {
    $("#ph-result").innerHTML = emptyHtml("plane", L("No data yet", "لا بيانات بعد"), L("SPPI has no basket or collection in the database yet.", "لا توجد سلة أو جمع لـ SPPI في قاعدة البيانات بعد."), `<a class="btn primary" href="#sppi-price-history/commodities">${esc(L("Open Commodities", "افتح السلع"))}</a>`);
    for (const id of ["ph-apply", "ph-reset", "ph-manual"]) $("#" + id)?.setAttribute("aria-disabled", "true");
    $("#ph-manual").onclick = () => toast(L("Start the SPPI basket first (Commodities)", "ابدأ سلة SPPI أولاً (السلع)"), true);
    return;
  }
  const months = [...new Set(d.weeks.map((w) => w.month))];
  $("#ph-month").innerHTML = months.map((m) => `<option value="${esc(m)}">${esc(fmtMonthLong(m))}</option>`).join("");
  $("#ph-outlet").innerHTML = `<option value="">${esc(L("All outlets", "كل المنافذ"))}</option>` + d.outlets.map((o) => `<option value="${esc(o.code)}">${esc(sppiName(o))}</option>`).join("");
  const fillWeeks = () => { const m = $("#ph-month").value; $("#ph-weeks").innerHTML = d.weeks.filter((w) => w.month === m).map((w) => `<label><input type="checkbox" value="${esc(w.id)}" checked> ${esc(sppiWeekLabel(w))}</label>`).join("") || `<span class="muted">${esc(L("No collection in this month", "لا جمع في هذا الشهر"))}</span>`; };
  const reset = () => { $("#ph-survey").value = "tickets-domestic"; $("#ph-month").value = sppiCurrentMonth(d); $("#ph-outlet").value = ""; fillWeeks(); };
  reset(); setApply(true, "");
  $("#ph-month").onchange = fillWeeks;
  $("#ph-reset").onclick = () => { reset(); $("#ph-apply").click(); };
  $("#ph-apply").onclick = () => {
    const weeks = $$("#ph-weeks input:checked").map((i) => i.value);
    if (!weeks.length) return toast(L("Choose at least one collection", "اختر مرة جمع واحدة على الأقل"), true);
    sppiGrid = { survey: $("#ph-survey").value, month: $("#ph-month").value, weeks, outlet: $("#ph-outlet").value };
    if (matchMedia("(min-width: 900px) and (max-width: 1366px)").matches) setSideCollapsed(true, false);
    drawSppiGrid();
  };
  $("#ph-manual").onclick = () => sppiManualCard({ wid: sppiGrid?.weeks?.[sppiGrid.weeks.length - 1] || d.weeks[d.weeks.length - 1]?.id, survey: sppiGrid?.survey?.startsWith("packages") ? "packages" : "tickets", outlet: sppiGrid?.outlet || "" });
  $("#ph-apply").click();
}
function sppiCellHtml(x, wid, outlet, item, leg) {
  const key = esc(`${wid}|${outlet}|${item}|${leg}`);
  if (!x) return `<td class="blk"><button type="button" data-sman="${key}" title="${esc(L("No row: add the price manually", "لا صف: أضف السعر يدوياً"))}">${esc(stateText("notread"))}</button></td>`;
  const tip = [x.note, x.matched_name, x.date_used ? L(`date used ${x.date_used}`, `التاريخ المستخدم ${x.date_used}`) : "", (x.flights || []).map((f) => `${f.no} ${f.dep || ""} ${f.fare ?? ""}`).join(", "), x.source === "manual" ? L(`manual · ${x.entered_by || ""} · ${x.entered_at || ""}`, `يدوي · ${x.entered_by || ""} · ${x.entered_at || ""}`) : ""].filter(Boolean).join(" · ");
  if (x.source !== "manual" && x.status === "blocked") return `<td class="blk"><button type="button" data-sman="${key}" title="${esc(tip || L("Blocked: add the price manually", "محجوب: أضف السعر يدوياً"))}">${esc(L("Blocked", "محجوب"))}</button></td>`;
  if (x.source !== "manual" && x.status === "not_available") return `<td class="na" title="${esc(tip)}">${esc(L("Not available", "غير متاح"))}</td>`;
  if (x.lowest == null && x.price == null) return `<td class="blk"><button type="button" data-sman="${key}" title="${esc(tip)}">${esc(x.status === "failed" ? stateText("failed") : stateText(x.status === "partial" ? "partial" : "notread"))}</button></td>`;
  const v = `<span class="p">${fmtN(x.lowest ?? x.price)}</span>${x.highest != null ? `<span class="lh">${esc(L("high", "أعلى"))} ${fmtN(x.highest)}</span>` : ""}${x.price != null && x.lowest != null ? `<span class="lh">${esc(L("price", "السعر"))} ${fmtN(x.price)}</span>` : ""}`;
  const chips = (x.source === "manual" ? `<span class="chip manual">${esc(L("Manual", "يدوي"))}</span>` : "") + (x.status === "to_review" ? `<span class="chip warn">${esc(L("To review", "للمراجعة"))}</span>` : "") + (isSubst(x) ? `<span class="chip yellow" title="${esc((x.flags || []).map(flagLabel).join(", "))}">${esc(L("Substituted", "بديل"))}: ${esc((x.flags || []).filter((f) => f === "other_hotel" || f === "next_day").map(flagLabel).join(", "))}</span>` : (x.flags || []).length ? `<span class="tag">${esc(x.flags.map(flagLabel).join(", "))}</span>` : "");
  return x.source === "manual" ? `<td class="cell cellbtn"><button type="button" data-sman="${key}" title="${esc(tip)}">${v}${chips}</button></td>` : `<td class="cell" title="${esc(tip)}">${v}${chips}</td>`;
}
function drawSppiGrid() {
  const g = sppiGrid, box = $("#ph-result"); if (!g || !box || !sppiCache?.meta) return;
  const d = sppiCache, weeks = d.weeks.filter((w) => g.weeks.includes(w.id));
  const survey = g.survey.startsWith("packages") ? "packages" : "tickets", market = g.survey === "tickets-foreign" ? "foreign" : g.survey === "tickets-domestic" ? "domestic" : null;
  const items = d.items.filter((i) => i.status !== "retired" && (survey === "packages" ? i.kind === "hotel" : i.kind === "route" && (!market || i.market === market))).sort((a, b) => (a.sort ?? 0) - (b.sort ?? 0));
  const samp = d.sample.filter((s) => s.survey === survey && s.status !== "retired" && (!g.outlet || s.outlet === g.outlet));
  const head = weeks.map((w) => `<th scope="col" class="num" style="white-space:normal;min-width:150px">${esc(sppiWeekLabel(w))}<br><span class="muted" style="font-weight:600">${esc(L("Tickets", "التذاكر"))} ${esc(fmtDay(w.tickets?.out))} → ${esc(fmtDay(w.tickets?.back))}<br>${esc(L("Packages", "الباقات"))} ${esc(fmtDay(w.packages?.checkin))}–${esc(fmtDay(w.packages?.checkout))}${w.packages?.nights ? ` (${w.packages.nights} ${esc(L("nights", "ليالٍ"))})` : ""}<br>${esc(L("Collected", "جُمع"))} ${esc(fmtDay(w.collected_on))}</span></th>`).join("");
  const rowsOut = [];
  const groups = survey === "packages" ? [...new Set(items.map((i) => i.city || "?"))].map((c) => ({ title: `${c}${items.find((i) => i.city === c && i.country) ? " · " + items.find((i) => i.city === c).country : ""}`, items: items.filter((i) => (i.city || "?") === c) })) : items.map((i) => ({ title: null, items: [i] }));
  for (const G of groups) {
    const gItems = G.items.filter((i) => samp.some((s) => s.item === i.code));
    if (!gItems.length) continue;
    if (G.title) rowsOut.push(`<tr class="grp"><td class="stick">${esc(G.title)}</td><td colspan="${weeks.length}"></td></tr>`);
    for (const it of gItems) {
      const outs = samp.filter((s) => s.item === it.code);
      if (survey === "tickets") rowsOut.push(`<tr class="grp"><td class="stick"><span class="mono">${esc(it.code)}</span> ${esc(it.name_en || "")} <span dir="auto" class="sub-l">${esc(it.name_ar || "")}</span>${it.collection?.lead_days == null ? ` <span class="tag">${esc(L("Timing: to be determined", "التوقيت: يُحدد لاحقاً"))}</span>` : ""}</td><td colspan="${weeks.length}"></td></tr>`);
      for (const s of outs) {
        const oname = sppiName(sppiOutlet(s.outlet)) || s.outlet;
        if (survey === "tickets") {
          for (const leg of ["out", "back"]) rowsOut.push(`<tr><th scope="row" class="stick"><span class="sub-l">${esc(oname)} ›</span> ${esc(leg === "out" ? L("out", "ذهاب") : L("back", "عودة"))}</th>${weeks.map((w) => sppiCellHtml(sppiCell(w.id, s.outlet, it.code, leg), w.id, s.outlet, it.code, leg)).join("")}</tr>`);
          rowsOut.push(`<tr><th scope="row" class="stick"><span class="sub-l">${esc(oname)} ›</span> <b>${esc(L("total", "المجموع"))}</b></th>${weeks.map((w) => {
            const o = sppiCell(w.id, s.outlet, it.code, "out"), b = sppiCell(w.id, s.outlet, it.code, "back"), t = sppiTotal(o, b);
            if (t) return `<td class="cell"${t.status === "to_review" ? ` title="${esc(L("Built from a leg marked To review: not a validated price", "مبني من اتجاه للمراجعة: ليس سعراً معتمداً"))}"` : ""}><span class="p">${fmtN(t.lowest)}</span><span class="lh">${esc(L("high", "أعلى"))} ${fmtN(t.highest)}</span><span class="lh">${esc(L("price", "السعر"))} ${fmtN(t.price)}</span>${t.status === "to_review" ? `<span class="chip warn">${esc(L("To review", "للمراجعة"))}</span>` : ""}</td>`;
            if ((o?.lowest != null && o?.status !== "blocked") || (b?.lowest != null && b?.status !== "blocked")) return `<td class="na"><span class="chip warn" title="${esc(L("A leg is missing: never one leg as the total", "ينقص اتجاه: لا يُعرض اتجاه واحد كمجموع"))}">${esc(L("Incomplete", "غير مكتمل"))}</span></td>`;
            if (o?.status === "blocked" || b?.status === "blocked") return `<td class="blk">${esc(L("Blocked", "محجوب"))}</td>`;
            return `<td class="na">—</td>`; }).join("")}</tr>`);
        } else rowsOut.push(`<tr><th scope="row" class="stick"><span class="nm" dir="auto">${esc(sppiName(it))}</span>${it.stars ? ` <span class="tag">${it.stars}★</span>` : ""}<br><span class="sub-l">${esc(oname)}${it.board_rule ? " · " + esc(it.board_rule) : ""}${it.collection?.lead_days == null ? " · " + esc(L("Timing: to be determined", "التوقيت: يُحدد لاحقاً")) : ""}</span></th>${weeks.map((w) => sppiCellHtml(sppiCell(w.id, s.outlet, it.code, "package"), w.id, s.outlet, it.code, "package")).join("")}</tr>`);
      }
    }
  }
  box.innerHTML = `<div class="card-h"><h2>${esc({ "tickets-domestic": L("Tickets · domestic carriers", "التذاكر · الناقلات المحلية"), "tickets-foreign": L("Tickets · foreign carriers", "التذاكر · الناقلات الأجنبية"), packages: L("Packages", "الباقات") }[g.survey])} · ${esc(fmtMonthLong(g.month))}</h2><span class="spacer"></span>
      <button type="button" id="ph-xlsx">${ico("download")}Excel</button><button type="button" id="ph-csv">${ico("download")}CSV</button></div>
    <div class="tw tall"><table class="pgrid" id="ph-grid"><caption class="sr-only">${esc(L("SPPI price grid", "جدول أسعار SPPI"))}</caption><thead><tr><th scope="col" class="stick">${esc(survey === "packages" ? L("Hotel › outlet", "الفندق › المنفذ") : L("Route › outlet › leg", "المسار › المنفذ › الاتجاه"))}</th>${head}</tr></thead><tbody>${rowsOut.join("") || `<tr><td colspan="${weeks.length + 1}">${emptyHtml("plane", L("Nothing sampled for this choice", "لا عينة لهذا الاختيار"), "")}</td></tr>`}</tbody></table></div>
    <p class="muted" style="margin:0">${esc(L("Lowest large; highest and price below. Totals: low = out + back, high falls back to low per leg, price = mean of the totals; a missing leg gives “Incomplete”. Select a Blocked or Not read cell to add the price by hand.", "الأدنى كبير؛ والأعلى والسعر تحته. المجموع: الأدنى = ذهاب + عودة، والأعلى يعود إلى الأدنى لكل اتجاه، والسعر = متوسط المجموعين؛ نقص اتجاه يعطي «غير مكتمل». اختر خلية محجوبة أو لم تُقرأ لإضافة السعر يدوياً."))}</p>`;
  $("#ph-grid").onclick = (e) => { const b = e.target.closest("[data-sman]"); if (!b) return; const [wid, outlet, item, leg] = b.dataset.sman.split("|"); const x = sppiCell(wid, outlet, item, leg); sppiManualCard({ wid, outlet, item, leg, survey: sppiSurveyOf(sppiItem(item)), row: x?.source === "manual" ? x : null }); };
  const sheet = () => {
    const H = ["Item", "Item (Arabic)", "Outlet", "Leg", ...weeks.flatMap((w) => [`${w.id} lowest`, `${w.id} highest`, `${w.id} price`, `${w.id} status`, `${w.id} source`])];
    const rows = [];
    for (const it of items) for (const s of samp.filter((x) => x.item === it.code)) for (const leg of [...(survey === "tickets" ? ["out", "back", "total"] : ["package"])]) rows.push([it.name_en || it.code, it.name_ar || "", s.outlet, leg, ...weeks.flatMap((w) => {
      if (leg === "total") { const t = sppiTotal(sppiCell(w.id, s.outlet, it.code, "out"), sppiCell(w.id, s.outlet, it.code, "back")); return t ? [t.lowest, t.highest, t.price, t.status, "computed"] : ["", "", "", "Incomplete", "computed"]; }
      const x = sppiCell(w.id, s.outlet, it.code, leg); return [x?.lowest ?? "", x?.highest ?? "", x?.price ?? "", x?.status || "not read", x?.source || ""]; })]);
    return { title: `SPPI ${g.survey} ${g.month}`, subtitle: weeks.map((w) => `${w.id}: tickets ${w.tickets?.out}→${w.tickets?.back}, packages ${w.packages?.checkin}–${w.packages?.checkout}, collected ${w.collected_on}`).join(" • "), headers: H, widths: H.map((h, i) => (i < 2 ? 30 : 12)), priceCols: [], rows };
  };
  $("#ph-xlsx").onclick = () => offerXlsx(`SPPI ${g.survey} ${g.month}.xlsx`, sheet());
  $("#ph-csv").onclick = () => { const s = sheet(); offerFile(`SPPI ${g.survey} ${g.month}.csv`, toCsv(s.rows.map((r) => Object.fromEntries(s.headers.map((h, i) => [h, r[i]]))), s.headers)); };
}
// the "Add price manually" card: one row with source "manual" into projects/sppi/observations/<collection id>
function sppiManualCard(pre = {}) {
  const d = sppiCache; if (!d?.meta) return;
  const cur = pre.row || null;
  const opt = (list, val) => list.map(([v, t]) => `<option value="${esc(v)}"${v === val ? " selected" : ""}>${esc(t)}</option>`).join("");
  openSidePanel(cur ? L("Edit manual price", "تعديل سعر يدوي") : L("Add price manually", "إضافة سعر يدوياً"), `<form id="sm-form" class="stack" novalidate>
    <p class="muted" style="margin:0">${esc(L("For outlets the scrapers cannot read (blocked, PC only, manual). Saved with source “manual”; nothing is prefilled from another collection.", "للمنافذ التي لا تقرؤها الكاشطات (محجوبة، على الحاسوب فقط، يدوية). يُحفظ بالمصدر «يدوي»؛ لا يُملأ شيء من جمع آخر."))}</p>
    <div class="form-grid">
      <label class="f"><span>${esc(L("Period / collection", "الفترة / الجمع"))} *</span><select id="sm-week">${opt(d.weeks.map((w) => [w.id, `${fmtMonth(w.month)} · ${sppiWeekLabel(w)}`]), cur?.week || pre.wid)}</select></label>
      <label class="f"><span>${esc(L("Survey", "المسح"))} *</span><select id="sm-survey">${opt([["tickets", L("Tickets", "التذاكر")], ["packages", L("Packages", "الباقات")]], cur?.survey || pre.survey || "tickets")}</select></label>
      <label class="f"><span>${esc(L("Outlet", "المنفذ"))} *</span><select id="sm-outlet"><option value="">${esc(L("Choose…", "اختر…"))}</option>${opt(d.outlets.map((o) => [o.code, sppiName(o)]), cur?.outlet || pre.outlet)}</select></label>
      <label class="f"><span>${esc(L("Item", "البند"))} *</span><select id="sm-item"></select></label>
      <label class="f"><span>${esc(L("Leg", "الاتجاه"))} *</span><select id="sm-leg"></select></label>
      <label class="f"><span>${esc(L("Date seen", "تاريخ الرؤية"))}</span><input type="date" id="sm-date" dir="ltr" value="${esc(cur?.date_used || "")}"></label>
      <label class="f"><span>${esc(L("Lowest (AED)", "الأدنى (درهم)"))}</span><input id="sm-low" inputmode="decimal" dir="ltr" value="${esc(cur?.lowest ?? "")}"></label>
      <label class="f"><span>${esc(L("Highest (AED, optional)", "الأعلى (درهم، اختياري)"))}</span><input id="sm-high" inputmode="decimal" dir="ltr" value="${esc(cur?.highest ?? "")}"></label>
      <label class="f"><span>${esc(L("Price (AED, optional)", "السعر (درهم، اختياري)"))}</span><input id="sm-price" inputmode="decimal" dir="ltr" value="${esc(cur?.price ?? "")}"></label></div>
    <fieldset style="border:0;padding:0;margin:0"><legend class="fl">${esc(L("Flags", "علامات"))}</legend><div class="flags">${SPPI_FLAGS.map((f) => `<label><input type="checkbox" value="${f}"${(cur?.flags || []).includes(f) ? " checked" : ""}> ${esc(flagLabel(f))}</label>`).join("")}</div></fieldset>
    <label class="f"><span>${esc(L("Note", "ملاحظة"))}</span><textarea id="sm-note" rows="2">${esc(cur?.note || "")}</textarea></label>
    <label class="f"><span>${esc(L("Screenshot ref / URL (optional)", "مرجع لقطة الشاشة / رابط (اختياري)"))}</span><input id="sm-shot" dir="ltr" value="${esc(cur?.screenshot_ref || "")}"></label>
    <div id="sm-box"></div><p class="f-err" id="sm-err" hidden></p>
    <div class="row"><button class="primary" type="submit" id="sm-save">${esc(L("Save", "حفظ"))}</button>${cur ? `<button type="button" class="danger" id="sm-withdraw">${esc(L("Withdraw", "سحب"))}</button>` : ""}<button type="button" id="sm-cancel">${esc(L("Cancel", "إلغاء"))}</button></div></form>`, () => {
    const fillItems = () => {
      const sv = $("#sm-survey").value, o = $("#sm-outlet").value;
      const codes = new Set(d.sample.filter((s) => s.survey === sv && (!o || s.outlet === o)).map((s) => s.item));
      const its = d.items.filter((i) => (sv === "packages" ? i.kind === "hotel" : i.kind === "route") && (!o || codes.has(i.code) || i.code === (cur?.item || pre.item)));
      const keep = $("#sm-item").value || cur?.item || pre.item;
      $("#sm-item").innerHTML = `<option value="">${esc(L("Choose…", "اختر…"))}</option>` + its.map((i) => `<option value="${esc(i.code)}">${esc(i.code + " · " + sppiName(i))}</option>`).join("");
      if (its.some((i) => i.code === keep)) $("#sm-item").value = keep;
      const legs = sv === "packages" ? [["package", L("package", "باقة")]] : [["out", L("out", "ذهاب")], ["back", L("back", "عودة")]];
      const kl = $("#sm-leg").value || cur?.leg || pre.leg;
      $("#sm-leg").innerHTML = legs.map(([v, t]) => `<option value="${v}">${esc(t)}</option>`).join("");
      if (legs.some(([v]) => v === kl)) $("#sm-leg").value = kl;
    };
    fillItems(); $("#sm-survey").onchange = fillItems; $("#sm-outlet").onchange = fillItems;
    $("#sm-cancel").onclick = closeSidePanel;
    const write = async (wid, mutate) => {
      if (!d.obs.has(wid)) { $("#sm-box").innerHTML = errBox(L("This collection was not read, so nothing was written. Reload and retry.", "لم يُقرأ هذا الجمع، لذلك لم يُكتب شيء. أعد التحميل وحاول."), "sm-reload"); $("#sm-reload").onclick = async () => { closeSidePanel(); sppiCache = null; rerender(); }; return false; }
      const path = `projects/sppi/observations/${wid}`, now = await getDocStrict(path), had = d.obs.get(wid).raw ?? null;   // a failed read throws: no write
      if ((now ? JSON.stringify(now) : null) !== had) { $("#sm-box").innerHTML = errBox(L("This collection changed since you opened it. Reload and retry; nothing was overwritten.", "تغيّر هذا الجمع منذ فتحه. أعد التحميل وحاول؛ لم يُستبدل شيء."), "sm-reload"); $("#sm-reload").onclick = async () => { closeSidePanel(); await sppiLoad(true); drawSppiGrid(); }; return false; }
      const doc = now || { rows: [] }, rows = [...(doc.rows || [])];
      mutate(rows);
      const next = { ...doc, rows, version: (doc.version || 0) + 1 };
      await db.doc(path).set(next);
      d.obs.set(wid, { raw: JSON.stringify(next), version: next.version, rows: rows.map((x) => sppiNormRow(x, wid)) });
      return true;
    };
    const numOk = (v) => v === "" || (/^\d+(\.\d+)?$/.test(v) && +v > 0);
const smFail = (x, again) => { $("#sm-err").hidden = true; $("#sm-box").innerHTML = errBox(L("Not saved: nothing was written. ", "لم يُحفظ: لم يُكتب شيء. ") + dbErr(x), "sm-retry"); $("#sm-retry").onclick = again; };
    $("#sm-form").onsubmit = async (e) => {
      e.preventDefault();
      const v = (id) => $("#" + id).value.trim(), err = $("#sm-err");
      const low = v("sm-low"), high = v("sm-high"), price = v("sm-price");
      const bad = !v("sm-week") || !v("sm-outlet") || !v("sm-item") || !v("sm-leg") ? L("Choose the collection, outlet, item and leg.", "اختر الجمع والمنفذ والبند والاتجاه.")
        : !low && !price ? L("Enter the lowest (tickets) or the price (packages), above 0 AED.", "أدخل الأدنى (التذاكر) أو السعر (الباقات)، أكبر من 0 درهم.") : !numOk(low) || !numOk(high) || !numOk(price) ? L("Prices must be numbers above 0 (AED).", "الأسعار أرقام أكبر من 0 (درهم).")
        : high && low && +high < +low ? L("Highest is below lowest.", "الأعلى أقل من الأدنى.") : "";
      err.hidden = !bad; err.textContent = bad; if (bad) return;
      const wid = v("sm-week");
      const row = { week: wid, survey: v("sm-survey"), outlet: v("sm-outlet"), item: v("sm-item"), leg: v("sm-leg"), lowest: low ? +low : null, highest: high ? +high : null, price: price ? +price : null, currency: "AED", status: "ok",
        flags: $$("#sm-form .flags input:checked").map((i) => i.value), date_used: v("sm-date") || null, note: v("sm-note"), screenshot_ref: v("sm-shot") || null, source: "manual", entered_by: viewerName(), entered_at: new Date().toISOString(), id: cur?.id || "m" + Date.now().toString(36) };
      try {
        const ok = await write(wid, (rows) => { const i = cur ? rows.findIndex((x) => x.id === cur.id && x.source === "manual") : -1; if (i >= 0) rows[i] = { ...rows[i], ...row }; else rows.push(row); });
        if (ok) { closeSidePanel(); toast(L("Manual price saved", "حُفظ السعر اليدوي")); drawSppiGrid(); }
      } catch (x) { smFail(x, () => $("#sm-form").requestSubmit()); }
    };
    $("#sm-withdraw")?.addEventListener("click", async () => {
      try { if (await write(cur.week, (rows) => { const i = rows.findIndex((x) => x.id === cur.id && x.source === "manual"); if (i >= 0) rows[i] = { ...rows[i], status: "withdrawn", withdrawn_at: new Date().toISOString() }; })) { closeSidePanel(); toast(L("Manual price withdrawn", "سُحب السعر اليدوي")); drawSppiGrid(); } }
      catch (x) { smFail(x, () => $("#sm-withdraw").click()); }
    });
  });
}
