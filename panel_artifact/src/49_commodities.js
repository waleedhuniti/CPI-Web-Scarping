
// ============================================================ Price History › Commodities ☰ (basket editors, catalogue, pins, TrendX list)
function pgCommodities(r, seq) {
  const pid = r.pid, p = routeOf(pid);
  const head = headCard(L("Commodities", "السلع"), `#${p}-price-history`, `<a class="link-btn" href="#${p}-price-history">${esc(L("Price History", "سجل الأسعار التاريخي"))} ${ico("pulse")}</a>`);
  if (pid === "sppi") { $("#page").innerHTML = head + `<div id="sp-editor">${loadingHtml(L("Loading the SPPI basket…", "تُحمَّل سلة SPPI…"))}</div>`; return sppiEditor(seq); }
  $("#page").innerHTML = head + `<div data-slot="basket"></div>`
    + (pid === "cpi" ? `<section class="card" id="cm-cat"><div class="card-h"><h2>${esc(L("Catalogue browser", "متصفح الكتالوج"))}</h2><span class="spacer"></span><span id="cm-cat-chip"></span></div><div id="cm-cat-body"><p class="muted" style="margin:0">${esc(L("Every product of the latest catalogue crawl, with photos. It reads one large file, so it opens on request.", "كل منتجات آخر مسح للكتالوج مع صورها. يقرأ ملفاً كبيراً، لذلك يُفتح عند الطلب."))}</p><button type="button" class="primary" id="cm-cat-open">${ico("search")}${esc(L("Open the catalogue browser", "افتح متصفح الكتالوج"))}</button></div></section>
      <section class="card" id="cm-pins"><div class="card-h"><h2>${esc(L("Reference listings (pins), read-only", "القوائم المرجعية (المثبّتة)، للقراءة فقط"))}</h2><span class="spacer"></span><span id="cm-pins-n" class="count-pill">—</span></div><p class="notice info" style="margin:0">${esc(L("Pending registry: pins are kept by the daily routine; approving pins and substitutes is not part of this version.", "سجل قيد الإعداد: المهمة اليومية تحفظ المثبّتات؛ اعتماد المثبّتات والبدائل ليس ضمن هذه النسخة."))}</p><div id="cm-pins-body">${loadingHtml(L("Loading pins…", "تُحمَّل المثبّتات…"))}</div></section>` : "")
    + (pid === "te" ? `<section class="card" id="cm-te"><div class="card-h"><h2>${esc(L("Commodities and their prices", "السلع وأسعارها"))}</h2></div>
      <div class="filter-card"><label class="search"><span class="sr-only">${esc(L("Search commodities", "ابحث في السلع"))}</span>${ico("search")}<input id="ov-q" type="search" placeholder="${esc(L("Search by commodity or category", "ابحث باسم السلعة أو الفئة"))}"></label><select id="ov-date" aria-label="${esc(L("Up to day", "حتى يوم"))}"></select><button type="button" id="ov-dl">${ico("download")}${esc(L("Download all prices (Excel)", "تنزيل كل الأسعار (Excel)"))}</button></div>
      <div class="tw tall"><table><caption class="sr-only">${esc(L("TrendX commodities", "سلع TrendX"))}</caption><thead><tr><th scope="col">${esc(L("Commodity", "السلعة"))}</th><th scope="col">${esc(L("Category", "الفئة"))}</th><th scope="col">${esc(L("Unit", "الوحدة"))}</th><th scope="col" class="num">${esc(L("Price", "السعر"))}</th><th scope="col">${esc(L("Trend over the saved days", "الاتجاه عبر الأيام المحفوظة"))}</th><th scope="col">${esc(L("In index", "في المؤشر"))}</th></tr></thead><tbody id="ov-rows"><tr><td colspan="6">${loadingHtml(L("Loading prices…", "تُحمَّل الأسعار…"))}</td></tr></tbody></table></div><p class="muted" id="ov-count" style="margin:0"></p></section>` : "");
  mount("basket", "blk-basket");
  mountBasketLoad(pid, seq);
  if (pid === "cpi") { cmPins(seq); $("#cm-cat-open").onclick = () => cmCatalogue(seq); }
  if (pid === "te") {
    (async () => {
      try { const days = await teDays(); ovRows = days.flatMap((d) => d.rows.map((x) => ({ ...x, run_date: d.day, accepted: "yes" }))); }
      catch (e) { if (alive(seq)) $("#ov-rows").innerHTML = `<tr><td colspan="6">${errBox(L("Unable to load prices right now. ", "تعذّر تحميل الأسعار الآن. ") + dbErr(e))}</td></tr>`; return; }
      if (!alive(seq)) return;
      gcOpen = null; drawGlobalRows();
      $("#ov-q").oninput = drawGlobalRows; $("#ov-date").onchange = drawGlobalRows;
      $("#ov-dl").onclick = (e) => exportAllRuns(null, null, e.currentTarget);
    })();
  }
}
async function cmPins(seq) {
  const doc = await getDoc("projects/cpi/pins/current"); if (!alive(seq)) return;
  const list = Object.entries(doc?.pins || {}).map(([k, v]) => { const [item, shop] = k.split("|"); return { item, shop, ...v }; }).sort((a, b) => a.item.localeCompare(b.item) || a.shop.localeCompare(b.shop));
  $("#cm-pins-n").textContent = L(`${fmtN(list.length)} pins`, `${fmtN(list.length)} مثبّتة`);
  let page = 0, q = "";
  const draw = () => {
    const f = list.filter((x) => !q || [x.item, x.shop, x.title].join(" ").toLowerCase().includes(q.toLowerCase())), pages = Math.max(1, Math.ceil(f.length / 50)); page = Math.min(page, pages - 1);
    $("#cm-pins-tbl").innerHTML = f.slice(page * 50, page * 50 + 50).map((x) => `<tr><td class="mono">${esc(x.item)}|${esc(x.shop)}</td><td dir="auto">${x.url ? `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title || "")}</a>` : esc(x.title || "")}</td><td class="num">${fmtN(x.unit, 2)}</td><td>${esc(fmtDay(x.since))}</td><td>${esc(fmtDay(x.last))}</td><td class="num">${fmtN(x.miss)}</td></tr>`).join("") || `<tr><td colspan="6" class="empty">${esc(L("No pins.", "لا مثبّتات."))}</td></tr>`;
    $("#cm-pins-page").textContent = `${page + 1} / ${pages}`;
  };
  $("#cm-pins-body").innerHTML = list.length ? `<input id="cm-pins-q" type="search" placeholder="${esc(L("Search pins by line, shop or title", "ابحث بالبند أو المتجر أو العنوان"))}" aria-label="${esc(L("Search pins", "ابحث في المثبّتات"))}">
    <div class="tw tall"><table><thead><tr><th scope="col">${esc(L("Line | shop", "البند | المتجر"))}</th><th scope="col">${esc(L("Title", "العنوان"))}</th><th scope="col" class="num">${esc(L("Unit price", "سعر الوحدة"))}</th><th scope="col">${esc(L("Since", "منذ"))}</th><th scope="col">${esc(L("Last", "آخر"))}</th><th scope="col" class="num">${esc(L("Missed", "غياب"))}</th></tr></thead><tbody id="cm-pins-tbl"></tbody></table></div>
    <div class="pager"><button type="button" id="cm-pins-prev">${esc(L("Previous", "السابق"))}</button><span class="muted" id="cm-pins-page"></span><button type="button" id="cm-pins-next">${esc(L("Next", "التالي"))}</button></div>` : emptyHtml("listico", L("No pins yet", "لا مثبّتات بعد"), "");
  if (!list.length) return;
  $("#cm-pins-q").oninput = (e) => { q = e.target.value; page = 0; draw(); };
  $("#cm-pins-prev").onclick = () => { page = Math.max(0, page - 1); draw(); };
  $("#cm-pins-next").onclick = () => { page++; draw(); };
  draw();
}
async function cmCatalogue(seq) {
  const body = $("#cm-cat-body"); body.innerHTML = loadingHtml(L("Reading the catalogue…", "يُقرأ الكتالوج…"));
  try { catDoc = await catalogueLatest(); if (!catDoc?.rows_asset) { body.innerHTML = emptyHtml("search", L("No catalogue yet", "لا كتالوج بعد"), ""); return; } await ensureCat([]); }
  catch (e) { if (alive(seq)) { body.innerHTML = errBox(L("Unable to load the catalogue right now. ", "تعذّر تحميل الكتالوج الآن. ") + (e?.message || e), "cm-cat-retry"); $("#cm-cat-retry").onclick = () => cmCatalogue(seq); } return; }
  if (!alive(seq)) return;
  const ix = catIx, rows = catData.rows;
  $("#cm-cat-chip").innerHTML = chip(L(`${fmtN(rows.length)} products · ${fmtDay(catDoc.date)}`, `${fmtN(rows.length)} منتج · ${fmtDay(catDoc.date)}`), "blue");
  let page = 0, q = "", store = "";
  body.innerHTML = `<div class="filter-card"><label class="search"><span class="sr-only">${esc(L("Search the catalogue", "ابحث في الكتالوج"))}</span>${ico("search")}<input id="cm-cat-q" type="search" placeholder="${esc(L("Search by product, brand or category", "ابحث بالمنتج أو العلامة أو الفئة"))}"></label>
    <select id="cm-cat-store" aria-label="${esc(L("Store", "المتجر"))}"><option value="">${esc(L("All stores", "كل المتاجر"))}</option>${Object.entries(catDoc.stores || {}).map(([s, n]) => `<option value="${esc(s)}">${esc(s)} (${fmtN(n)})</option>`).join("")}</select></div>
    <div class="tw tall"><table><thead><tr><th scope="col">${esc(L("Photo", "صورة"))}</th><th scope="col">${esc(L("Product", "المنتج"))}</th><th scope="col">${esc(L("Store", "المتجر"))}</th><th scope="col">${esc(L("Category", "الفئة"))}</th><th scope="col" class="num">${esc(L("Price (AED)", "السعر (درهم)"))}</th><th scope="col">${esc(L("Size", "الحجم"))}</th></tr></thead><tbody id="cm-cat-tbl"></tbody></table></div>
    <div class="pager"><button type="button" id="cm-cat-prev">${esc(L("Previous", "السابق"))}</button><span class="muted" id="cm-cat-page"></span><button type="button" id="cm-cat-next">${esc(L("Next", "التالي"))}</button></div>`;
  const draw = async () => {
    const f = rows.filter((x) => (!store || x[ix.outlet] === store) && (!q || [x[ix.title], x[ix.brand], x[ix.category]].join(" ").toLowerCase().includes(q.toLowerCase())));
    const pages = Math.max(1, Math.ceil(f.length / 50)); page = Math.min(page, pages - 1);
    const pg = f.slice(page * 50, page * 50 + 50);
    const need = [...new Set(pg.map((x) => x[ix.group]))].filter((g) => catDoc.thumbs_assets?.[g] && !catGot[g]);
    const paint = () => { $("#cm-cat-tbl").innerHTML = pg.map((x) => { const u = x[ix.photo_url], b = u && catThumbs[u];
      return `<tr><td>${b ? `<img class="thumb" src="data:image/jpeg;base64,${b}" alt="">` : u ? `<img class="thumb" src="${esc(u)}" alt="" loading="lazy" onerror="this.remove()">` : ""}</td><td dir="auto"><a href="${esc(x[ix.url])}" target="_blank" rel="noopener">${esc(x[ix.title])}</a>${x[ix.brand] ? `<br><span class="muted">${esc(x[ix.brand])}</span>` : ""}</td><td>${esc(x[ix.outlet])}</td><td>${esc(x[ix.category])}</td><td class="num"><b>${esc(x[ix.price])}</b>${x[ix.regular_price] && x[ix.regular_price] !== x[ix.price] ? `<br><span class="muted">${esc(L("was", "كان"))} ${esc(x[ix.regular_price])}</span>` : ""}</td><td dir="auto">${esc(x[ix.size] || "")}</td></tr>`; }).join("") || `<tr><td colspan="6" class="empty">${esc(L("No products match.", "لا منتجات مطابقة."))}</td></tr>`;
      $("#cm-cat-page").textContent = L(`${page + 1} / ${pages} · ${fmtN(f.length)} products`, `${page + 1} / ${pages} · ${fmtN(f.length)} منتج`); };
    paint();
    if (need.length) { await ensureCat(need); if (alive(seq)) paint(); }
  };
  $("#cm-cat-q").oninput = (e) => { q = e.target.value; page = 0; draw(); };
  $("#cm-cat-store").onchange = (e) => { store = e.target.value; page = 0; draw(); };
  $("#cm-cat-prev").onclick = () => { page = Math.max(0, page - 1); draw(); };
  $("#cm-cat-next").onclick = () => { page++; draw(); };
  draw();
}

// ---------------- SPPI basket editor: items, outlets and the fixed sample, saved to projects/sppi/meta with a version check
let spEd = null;            // { tab, draft:{items,outlets,sample}, dirty, q, form:{kind, idx}|null }
async function sppiEditor(seq, fresh) {
  let d; try { d = await sppiLoad(fresh); } catch (e) { if (alive(seq)) $("#sp-editor").innerHTML = errBox(L("Unable to load the SPPI basket right now. ", "تعذّر تحميل سلة SPPI الآن. ") + dbErr(e), "sp-retry"); bindRetry(); return; }
  if (!alive(seq)) return;
  if (!d.meta) {
    $("#sp-editor").innerHTML = `<section class="card">${emptyHtml("plane", L("No SPPI basket yet", "لا سلة SPPI بعد"), L("Start an empty basket, then add the outlets, items (routes and hotels) and the fixed sample. Nothing is written until you click.", "ابدأ سلة فارغة، ثم أضف المنافذ والبنود (المسارات والفنادق) والعينة الثابتة. لا يُكتب شيء قبل النقر."), `<button type="button" class="primary" id="sp-start">${ico("plus")}${esc(L("Start SPPI basket", "ابدأ سلة SPPI"))}</button>`)}</section>`;
    $("#sp-start").onclick = async (e) => {
      const btn = e.currentTarget; btn.disabled = true;
      // re-check with a throwing read: a basket that cannot be read is never replaced by an empty one
      try {
        const [m, p] = [await getDocStrict(SPPI_META_PATH), await getDocStrict("projects/sppi")];
        if (m || p?.meta || (p && (p.weeks || p.items || p.outlets))) toast(L("A basket already exists; reloading", "توجد سلة بالفعل؛ يُعاد التحميل"), true);
        else await db.doc(SPPI_META_PATH).set({ name: "SPPI", currency: "AED", periods: [], weeks: [], outlets: [], items: [], sample: [], version: 1, created_at: new Date().toISOString() });
      }
      catch (x) { if (alive(seq)) { $("#sp-editor").innerHTML = errBox(L("Unable to check the SPPI basket right now, so nothing was written. ", "تعذّر التحقق من سلة SPPI الآن، لذلك لم يُكتب شيء. ") + dbErr(x), "sp-retry"); bindRetry(); } return; }
      spEd = null; sppiEditor(seq, true);
    };
    return;
  }
  if (!spEd || fresh) spEd = { tab: spEd?.tab || "items", draft: JSON.parse(JSON.stringify({ items: d.items, outlets: d.outlets, sample: d.sample })), dirty: false, q: "", form: null };
  drawSppiEditor();
}
const spUsed = (code) => [...(sppiCache?.obs?.values() || [])].some((o) => o.rows.some((r) => r.item === code || r.outlet === code));
function drawSppiEditor() {
  const box = $("#sp-editor"); if (!box || !spEd) return;
  const D = spEd.draft, tab = spEd.tab, q = spEd.q.toLowerCase();
  const stChip = (x) => (x.status === "retired" ? chip(L(`Retired${x.until ? " " + fmtDay(x.until) : ""}`, `متقاعد${x.until ? " " + fmtDay(x.until) : ""}`), "grey") : chip(L("Active", "فعّال"), "ok"));
  const act = (i, x) => `<div class="row" style="gap:6px;flex-wrap:nowrap"><button type="button" data-ed="${i}">${ico("edit")}${esc(L("Edit", "تعديل"))}</button>${x.status === "retired" ? `<button type="button" data-restore="${i}">${esc(L("Restore", "استعادة"))}</button>` : `<button type="button" class="danger" data-retire="${i}">${esc(L("Retire", "إيقاف"))}</button>`}</div>`;
  const match = (x) => !q || JSON.stringify(x).toLowerCase().includes(q);
  let head, body;
  if (tab === "items") {
    head = [L("Code", "الرمز"), L("Kind", "النوع"), L("Market", "السوق"), L("English name", "الاسم الإنجليزي"), L("Arabic name", "الاسم العربي"), L("City", "المدينة"), L("Country", "الدولة"), L("Timing", "التوقيت"), L("Status", "الحالة"), ""];
    body = D.items.map((x, i) => [x, i]).filter(([x]) => match(x)).map(([x, i]) => `<tr><td class="mono">${esc(x.code)}</td><td>${esc(x.kind)}</td><td>${esc(x.market || "—")}</td><td>${esc(x.name_en || "")}</td><td dir="auto">${esc(x.name_ar || "")}</td><td>${esc(x.city || "")}</td><td>${esc(x.country || "")}</td><td>${x.collection?.lead_days == null ? `<span class="muted">${esc(L("Timing: to be determined", "التوقيت: يُحدد لاحقاً"))}</span>` : esc(L(`${x.collection.lead_days} days ahead`, `قبل ${x.collection.lead_days} يوماً`))}</td><td>${stChip(x)}</td><td>${act(i, x)}</td></tr>`);
  } else if (tab === "outlets") {
    head = [L("Code", "الرمز"), L("English name", "الاسم الإنجليزي"), L("Arabic name", "الاسم العربي"), L("Kind", "النوع"), L("Market", "السوق"), L("Access", "الوصول"), L("Status", "الحالة"), ""];
    body = D.outlets.map((x, i) => [x, i]).filter(([x]) => match(x)).map(([x, i]) => `<tr><td class="mono">${esc(x.code)}</td><td>${esc(x.name_en || "")}</td><td dir="auto">${esc(x.name_ar || "")}</td><td>${esc(x.kind || "")}</td><td>${esc(x.market || "—")}</td><td>${chip(x.access === "auto" ? "Auto" : x.access === "pc_only" ? "PC run" : "Manual", x.access === "auto" ? "blue" : x.access === "pc_only" ? "warn" : "manual")}</td><td>${stChip(x)}</td><td>${act(i, x)}</td></tr>`);
  } else {
    head = [L("Survey", "المسح"), L("Outlet", "المنفذ"), L("Item", "البند"), L("Legs", "الاتجاهات"), L("Since", "منذ"), L("Status", "الحالة"), ""];
    body = D.sample.map((x, i) => [x, i]).filter(([x]) => match(x)).map(([x, i]) => `<tr><td>${esc(x.survey)}</td><td>${esc(x.outlet)}</td><td><span class="mono">${esc(x.item)}</span> ${esc(D.items.find((it) => it.code === x.item)?.name_en || "")}</td><td>${esc((x.legs || []).join(", "))}</td><td>${esc(fmtDay(x.since))}</td><td>${stChip(x)}</td><td>${act(i, x)}</td></tr>`);
  }
  const counts = { items: D.items.filter((x) => x.status !== "retired").length, outlets: D.outlets.filter((x) => x.status !== "retired").length, sample: D.sample.filter((x) => x.status !== "retired").length };
  box.innerHTML = `<section class="card" id="sp-card"><div class="card-h"><h2>${esc(L("SPPI basket", "سلة SPPI"))}</h2><span class="spacer"></span>
      ${segToggle("sp-tab", [["items", L(`Items (${counts.items})`, `البنود (${counts.items})`)], ["outlets", L(`Outlets (${counts.outlets})`, `المنافذ (${counts.outlets})`)], ["sample", L(`Sample (${counts.sample})`, `العينة (${counts.sample})`)]], tab, L("Basket part", "جزء السلة"))}</div>
    <p class="muted" style="margin:0">${esc(L(`${counts.items} items: ${D.items.filter((x) => x.status !== "retired" && x.kind === "route").length} routes (${D.items.filter((x) => x.status !== "retired" && x.kind === "route" && x.market === "domestic").length} domestic, ${D.items.filter((x) => x.status !== "retired" && x.kind === "route" && x.market === "foreign").length} foreign) and ${D.items.filter((x) => x.status !== "retired" && x.kind === "hotel").length} hotels. Retire instead of deleting: rows with prices stay. Collected monthly; timing per item to be determined.`, `${counts.items} بنداً: ${D.items.filter((x) => x.status !== "retired" && x.kind === "route").length} مساراً و${D.items.filter((x) => x.status !== "retired" && x.kind === "hotel").length} فندقاً. أوقف البند بدل حذفه: تبقى الصفوف المسعّرة. الجمع شهري؛ توقيت كل بند يُحدد لاحقاً.`))}</p>
    <div class="filter-card"><label class="search"><span class="sr-only">${esc(L("Search", "بحث"))}</span>${ico("search")}<input id="sp-search" type="search" value="${esc(spEd.q)}" placeholder="${esc(L("Search this list", "ابحث في هذه القائمة"))}"></label>
      <button type="button" id="sp-add">${ico("plus")}${esc(tab === "items" ? L("Add item", "إضافة بند") : tab === "outlets" ? L("Add outlet", "إضافة منفذ") : L("Add sample row", "إضافة صف عينة"))}</button>
      <button type="button" class="primary" id="sp-save" aria-disabled="${!spEd.dirty}">${esc(L("Save basket", "حفظ السلة"))}</button><span class="muted" id="sp-state" role="status">${esc(spEd.dirty ? L("Unsaved changes", "تعديلات غير محفوظة") : L("All changes saved", "كل التعديلات محفوظة"))}</span></div>
    <div id="sp-box"></div><div id="sp-form"></div>
    <div class="tw tall"><table id="sp-table"><caption class="sr-only">${esc(tab)}</caption><thead><tr>${head.map((h) => `<th scope="col">${esc(h)}</th>`).join("")}</tr></thead><tbody>${body.join("") || `<tr><td colspan="${head.length}" class="empty">${esc(L("Nothing here yet.", "لا شيء هنا بعد."))}</td></tr>`}</tbody></table></div></section>`;
  bindSeg("sp-tab", (v) => { spEd.tab = v; spEd.q = ""; spEd.form = null; drawSppiEditor(); });
  $("#sp-search").oninput = (e) => { spEd.q = e.target.value; const pos = e.target.selectionStart; drawSppiEditor(); const s = $("#sp-search"); s.focus(); try { s.setSelectionRange(pos, pos); } catch (x) {} };
  $("#sp-add").onclick = () => { spEd.form = { kind: tab, idx: null }; drawSppiForm(); };
  $("#sp-table").onclick = (e) => {
    const b = e.target.closest("button"); if (!b) return;
    const list = D[tab];
    if (b.dataset.ed != null) { spEd.form = { kind: tab, idx: +b.dataset.ed }; drawSppiForm(); }
    else if (b.dataset.retire != null) { const x = list[+b.dataset.retire]; x.status = "retired"; x.until = todayDubai(); spEd.dirty = true; drawSppiEditor(); toast(L("Retired; save the basket to keep it", "أُوقف؛ احفظ السلة لتثبيته")); }
    else if (b.dataset.restore != null) { const x = list[+b.dataset.restore]; x.status = "active"; delete x.until; spEd.dirty = true; drawSppiEditor(); }
  };
  $("#sp-save").onclick = sppiSaveMeta;
  if (spEd.form) drawSppiForm();
}
function drawSppiForm() {
  const f = spEd.form, D = spEd.draft, box = $("#sp-form"); if (!f || !box) return;
  const cur = f.idx == null ? {} : D[f.kind][f.idx];
  const inp = (id, label, val, req, attrs = "") => `<label class="f"><span>${esc(label)}${req ? " *" : ""}</span><input id="${id}" value="${esc(val ?? "")}" ${attrs} aria-describedby="${id}-err"><small class="f-err" id="${id}-err" hidden></small></label>`;
  const sel = (id, label, opts, val, req) => `<label class="f"><span>${esc(label)}${req ? " *" : ""}</span><select id="${id}" aria-describedby="${id}-err">${opts.map(([v, t]) => `<option value="${esc(v)}"${String(v) === String(val ?? "") ? " selected" : ""}>${esc(t)}</option>`).join("")}</select><small class="f-err" id="${id}-err" hidden></small></label>`;
  let fields;
  if (f.kind === "items") fields = inp("spf-code", L("Code", "الرمز"), cur.code, 1, `class="mono" dir="ltr"${f.idx != null && spUsed(cur.code) ? " readonly" : ""}`) + sel("spf-kind", L("Kind", "النوع"), [["route", L("route", "مسار")], ["hotel", L("hotel", "فندق")]], cur.kind || "route", 1)
    + sel("spf-market", L("Market", "السوق"), [["domestic", L("domestic", "محلي")], ["foreign", L("foreign", "أجنبي")], ["", L("none (hotels)", "لا شيء (فنادق)")]], cur.market ?? "domestic", 1) + inp("spf-en", L("English name", "الاسم الإنجليزي"), cur.name_en, 1) + inp("spf-ar", L("Arabic name", "الاسم العربي"), cur.name_ar, 1, 'dir="rtl"')
    + inp("spf-city", L("City", "المدينة"), cur.city, 1) + inp("spf-country", L("Country", "الدولة"), cur.country, 1) + inp("spf-lead", L("Lead days (empty = to be determined)", "أيام مسبقة (فارغ = يُحدد لاحقاً)"), cur.collection?.lead_days ?? "", 0, 'inputmode="numeric" dir="ltr"');
  else if (f.kind === "outlets") fields = inp("spf-code", L("Code", "الرمز"), cur.code, 1, `class="mono" dir="ltr"${f.idx != null && spUsed(cur.code) ? " readonly" : ""}`) + inp("spf-en", L("English name", "الاسم الإنجليزي"), cur.name_en, 1) + inp("spf-ar", L("Arabic name", "الاسم العربي"), cur.name_ar, 0, 'dir="rtl"')
    + sel("spf-kind", L("Kind", "النوع"), [["airline", L("airline", "طيران")], ["travel_agent", L("travel agent", "وكيل سفر")], ["tour_operator", L("tour operator", "منظم رحلات")]], cur.kind || "airline", 1)
    + sel("spf-market", L("Market", "السوق"), [["domestic", L("domestic", "محلي")], ["foreign", L("foreign", "أجنبي")], ["", L("none", "لا شيء")]], cur.market ?? "domestic", 1)
    + sel("spf-access", L("Access", "الوصول"), [["auto", "Auto"], ["pc_only", "PC run"], ["manual", "Manual"]], cur.access || "auto", 1) + inp("spf-url", "URL", cur.url, 0, 'dir="ltr"');
  else fields = sel("spf-survey", L("Survey", "المسح"), [["tickets", L("tickets", "تذاكر")], ["packages", L("packages", "باقات")]], cur.survey || "tickets", 1)
    + sel("spf-outlet", L("Outlet", "المنفذ"), [["", L("Choose…", "اختر…")], ...D.outlets.filter((o) => o.status !== "retired" || o.code === cur.outlet).map((o) => [o.code, `${o.code} · ${o.name_en || ""}`])], cur.outlet, 1)
    + sel("spf-item", L("Item", "البند"), [["", L("Choose…", "اختر…")], ...D.items.filter((i) => i.status !== "retired" || i.code === cur.item).map((i) => [i.code, `${i.code} · ${i.name_en || ""}`])], cur.item, 1)
    + inp("spf-since", L("Since", "منذ"), cur.since || todayDubai(), 0, 'type="date" dir="ltr"');
  box.innerHTML = `<form class="card" id="spf" novalidate style="background:#fbfcfe"><h3 style="margin:0">${esc(f.idx == null ? L("New", "جديد") : L("Edit", "تعديل"))} · ${esc({ items: L("item", "بند"), outlets: L("outlet", "منفذ"), sample: L("sample row", "صف عينة") }[f.kind])}</h3><div class="form-grid">${fields}</div>
    <div class="row"><button type="submit" class="primary" id="spf-ok">${esc(L("Apply", "تطبيق"))}</button><button type="button" id="spf-cancel">${esc(L("Cancel", "إلغاء"))}</button><span class="muted">${esc(L("Applied to the draft; Save basket writes it.", "يُطبَّق على المسودة؛ «حفظ السلة» يكتبه."))}</span></div></form>`;
  $("#spf-cancel").onclick = () => { spEd.form = null; box.innerHTML = ""; $("#sp-add").focus(); };
  (box.querySelector("input:not([readonly]), select") || box).focus();
  $("#spf").onsubmit = (e) => {
    e.preventDefault();
    const v = (id) => ($("#" + id)?.value ?? "").trim(), errs = {};
    const need = (id, ok = !!v(id)) => { if (!ok) errs[id] = L("Required.", "مطلوب."); };
    let row;
    if (f.kind === "items") {
      ["spf-code", "spf-en", "spf-ar", "spf-city", "spf-country"].forEach((id) => need(id));
      if (v("spf-code") && !/^[A-Za-z0-9_-]{2,30}$/.test(v("spf-code"))) errs["spf-code"] = L("2-30 letters, digits, _ or -.", "2-30 حرفاً أو رقماً أو _ أو -.");
      else if (v("spf-code") && D.items.some((x, i) => x.code === v("spf-code") && i !== f.idx)) errs["spf-code"] = L(`The code “${v("spf-code")}” is already used.`, `الرمز «${v("spf-code")}» مستخدم.`);
      if (v("spf-kind") === "route" && !v("spf-market")) errs["spf-market"] = L("A route needs a market.", "المسار يحتاج سوقاً.");
      if (v("spf-lead") && !/^\d{1,3}$/.test(v("spf-lead"))) errs["spf-lead"] = L("Whole days, or leave empty.", "أيام صحيحة، أو اتركه فارغاً.");
      row = { ...cur, code: v("spf-code"), kind: v("spf-kind"), market: v("spf-market") || null, name_en: v("spf-en"), name_ar: v("spf-ar"), city: v("spf-city"), country: v("spf-country"), status: cur.status || "active",
        collection: { frequency: "monthly", ...(cur.collection || {}), lead_days: v("spf-lead") ? +v("spf-lead") : null, note: v("spf-lead") ? (cur.collection?.note === "to be determined" ? "" : cur.collection?.note || "") : "to be determined" } };
      if (row.sort == null) row.sort = Math.max(0, ...D.items.map((x) => x.sort || 0)) + 1;
    } else if (f.kind === "outlets") {
      ["spf-code", "spf-en"].forEach((id) => need(id));
      if (v("spf-code") && !/^[a-z0-9_-]{2,30}$/.test(v("spf-code"))) errs["spf-code"] = L("2-30 lowercase letters, digits, _ or -.", "2-30 حرفاً صغيراً أو رقماً أو _ أو -.");
      else if (v("spf-code") && D.outlets.some((x, i) => x.code === v("spf-code") && i !== f.idx)) errs["spf-code"] = L(`The code “${v("spf-code")}” is already used.`, `الرمز «${v("spf-code")}» مستخدم.`);
      row = { ...cur, code: v("spf-code"), name_en: v("spf-en"), name_ar: v("spf-ar"), kind: v("spf-kind"), market: v("spf-market") || null, access: v("spf-access"), url: v("spf-url"), status: cur.status || "active" };
    } else {
      ["spf-outlet", "spf-item"].forEach((id) => need(id));
      const it = D.items.find((i) => i.code === v("spf-item"));
      if (it && (it.kind === "hotel") !== (v("spf-survey") === "packages")) errs["spf-item"] = L("Tickets take routes; packages take hotels.", "التذاكر للمسارات؛ الباقات للفنادق.");
      if (D.sample.some((x, i) => i !== f.idx && x.survey === v("spf-survey") && x.outlet === v("spf-outlet") && x.item === v("spf-item"))) errs["spf-item"] = L("This survey, outlet and item are already sampled.", "هذا المسح والمنفذ والبند في العينة بالفعل.");
      row = { ...cur, survey: v("spf-survey"), outlet: v("spf-outlet"), item: v("spf-item"), legs: v("spf-survey") === "packages" ? ["package"] : ["out", "back"], since: v("spf-since") || todayDubai(), status: cur.status || "active" };
    }
    for (const el of $$("#spf .f-err")) { el.hidden = true; el.textContent = ""; }
    for (const el of $$("#spf [aria-invalid]")) el.removeAttribute("aria-invalid");
    const ks = Object.keys(errs);
    if (ks.length) { for (const k of ks) { const e2 = $("#" + k + "-err"); e2.hidden = false; e2.textContent = errs[k]; $("#" + k).setAttribute("aria-invalid", "true"); } $("#" + ks[0]).focus(); return; }
    if (f.idx == null) D[f.kind].push(row); else D[f.kind][f.idx] = row;
    spEd.dirty = true; spEd.form = null; drawSppiEditor(); toast(L("Applied; press Save basket to write it", "طُبّق؛ اضغط «حفظ السلة» لكتابته"));
  };
}
async function sppiSaveMeta() {
  if (!spEd?.dirty) return toast(L("Nothing to save yet", "لا تعديلات للحفظ"));
  const d = sppiCache, btn = $("#sp-save"); btn.disabled = true;
  try {
    const now = await getDocStrict(d.metaPath);   // a failed read throws (pink box below), never a write
    const raw = d.metaPath === "projects/sppi" ? (now?.meta ? JSON.stringify(now.meta) : JSON.stringify(now)) : now ? JSON.stringify(now) : null;
    if (raw !== d.metaRaw) {
      $("#sp-box").innerHTML = errBox(L("The SPPI basket changed since you opened it (another viewer or the data routine). Nothing was overwritten. Reload and retry: your unsaved edits are dropped.", "تغيّرت سلة SPPI منذ فتحها (مستخدم آخر أو مهمة البيانات). لم يُستبدل شيء. أعد التحميل وحاول: تُفقد تعديلاتك غير المحفوظة."), "sp-reload");
      $("#sp-reload").textContent = L("Reload and retry", "أعد التحميل وحاول"); $("#sp-reload").onclick = () => { spEd = null; sppiEditor(renderSeq, true); };
      $("#sp-reload").focus(); return;
    }
    const base = d.metaPath === "projects/sppi" && now?.meta ? now.meta : now || {};
    const next = { ...base, items: spEd.draft.items, outlets: spEd.draft.outlets, sample: spEd.draft.sample, version: (base.version || 0) + 1, updated_at: new Date().toISOString() };
    if (d.metaPath === "projects/sppi" && now?.meta) await db.doc("projects/sppi").set({ ...now, meta: next }); else await db.doc(d.metaPath).set(next);
    spEd.dirty = false; toast(L("SPPI basket saved", "حُفظت سلة SPPI"));
    await sppiLoad(true); spEd.draft = JSON.parse(JSON.stringify({ items: sppiCache.items, outlets: sppiCache.outlets, sample: sppiCache.sample }));
    drawSppiEditor();
  } catch (e) { $("#sp-box").innerHTML = errBox(dbErr(e)); }
  finally { if ($("#sp-save")) $("#sp-save").disabled = false; }
}
