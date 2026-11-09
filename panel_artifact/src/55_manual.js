// ============================================================ Manual Entry: prices typed by hand for outlets the scrapers cannot read
// CPI: projects/cpi/manual/<YYYY-MM-DD> {rows:[...]} (the same documents the Price History card writes). SPPI: the manual rows of
// projects/sppi/observations/<collection> through sppiManualCard. A manual price is never prefilled from another day, carries
// source "manual", who entered it and when, and stays out of the CPI monitor.
const MAN_EXTRA = [{ code: "unioncoop", en: "Union Coop", ar: "تعاونية الاتحاد" }, { code: "spinneys", en: "Spinneys", ar: "سبينيس" }];
const manOutlets = () => [...CPI_OUTLETS.filter((o) => o.daily), ...MAN_EXTRA, ...CPI_OUTLETS.filter((o) => !o.daily)];
const manOutletName = (code) => { const o = manOutlets().find((x) => x.code === code); return o ? L(o.en, o.ar) : code; };
const MAN_SOURCES = [["store", "Store visit", "زيارة المحل"], ["site", "Shop website or app, read by a person", "موقع المحل أو تطبيقه، اطلاع شخصي"], ["phone", "Phone or shop staff", "هاتف أو موظف المحل"], ["other", "Other", "أخرى"]];
const manSourceName = (k) => { const s = MAN_SOURCES.find((x) => x[0] === k); return s ? L(s[1], s[2]) : (k || "—"); };
const manState = { outlet: "carrefour", date: null, line: null, from: null, to: null, edit: null, loaded: {} };

function pgManual(r, seq) {
  if (r.pid === "sppi") return pgManualSppi(r, seq);
  if (r.pid !== "cpi") return pgUnknown(r);
  const today = todayDubai();
  manState.date = manState.date && manState.date <= today ? manState.date : today;
  manState.to = manState.to || today; manState.from = manState.from || dayAdd(today, -13);
  manState.edit = null; manState.line = null;
  const oOpts = manOutlets().map((o) => `<option value="${esc(o.code)}"${o.code === manState.outlet ? " selected" : ""}>${esc(L(o.en, o.ar))}</option>`).join("");
  const sOpts = MAN_SOURCES.map(([k, en, ar]) => `<option value="${k}">${esc(L(en, ar))}</option>`).join("");
  $("#page").innerHTML = titleRow(L("Manual Entry", "الإدخال اليدوي")) + `
  <section class="card stack" id="mn-add" aria-labelledby="mn-add-h">
    <div class="card-h"><h2 id="mn-add-h">${esc(L("Add a price", "إضافة سعر"))}</h2>
      <p class="sub">${esc(L("For outlets the scrapers cannot read, like Carrefour while it refuses our pages. Saved with source “manual”, your name and the time. Nothing is prefilled from another day, and manual prices are not used by the CPI monitor.", "للمنافذ التي لا تقرؤها الكاشطات، مثل كارفور ما دام يرفض صفحاتنا. يُحفظ بالمصدر «يدوي» مع اسمك والوقت. لا يُملأ شيء من يوم آخر، والأسعار اليدوية لا تدخل في المؤشر الداخلي."))}</p></div>
    <form id="mn-form" class="stack" novalidate>
      <div class="form-grid">
        <label class="f"><span>${esc(L("Date seen", "تاريخ الرؤية"))} *</span><input type="date" id="mn-date" dir="ltr" min="2026-01-01" max="${today}" value="${manState.date}"></label>
        <label class="f"><span>${esc(L("Outlet", "المنفذ"))} *</span><select id="mn-outlet">${oOpts}</select></label>
        <label class="f"><span>${esc(L("How it was seen", "طريقة الرؤية"))}</span><select id="mn-source">${sOpts}</select></label>
      </div>
      <div class="f"><label for="mn-q"><span class="fl">${esc(L("Basket line", "بند السلة"))} *</span></label>
        <input id="mn-q" type="search" autocomplete="off" dir="auto" placeholder="${esc(L("Code, Arabic name, brand or barcode", "الرمز أو الاسم العربي أو العلامة أو الباركود"))}" aria-describedby="mn-q-hint" aria-controls="mn-pick">
        <small class="hint" id="mn-q-hint">${esc(L("Type at least 2 characters, then choose the line.", "اكتب حرفين على الأقل ثم اختر البند."))}</small>
        <div id="mn-pick" class="mn-pick" role="listbox" aria-label="${esc(L("Matching basket lines", "بنود السلة المطابقة"))}"></div>
        <div id="mn-chosen" class="mn-chosen" hidden></div></div>
      <div class="form-grid">
        <label class="f"><span>${esc(L("Price paid (AED)", "السعر المدفوع (درهم)"))} *</span><input id="mn-price" inputmode="decimal" dir="ltr" aria-describedby="mn-err"></label>
        <label class="f"><span>${esc(L("Regular price, if on offer (AED)", "السعر العادي إن كان عليه عرض (درهم)"))}</span><input id="mn-reg" inputmode="decimal" dir="ltr"></label>
        <label class="f"><span>${esc(L("Pack size seen", "حجم العبوة المرئي"))}</span><input id="mn-unit" dir="auto"></label>
      </div>
      <div class="form-grid">
        <label class="f"><span>${esc(L("Product name as seen", "اسم المنتج كما رُئي"))}</span><input id="mn-title" dir="auto"></label>
        <label class="f"><span>${esc(L("Product link (optional)", "رابط المنتج (اختياري)"))}</span><input id="mn-url" dir="ltr" inputmode="url"></label>
      </div>
      <label class="f"><span>${esc(L("Note (or screenshot reference)", "ملاحظة (أو مرجع لقطة الشاشة)"))}</span><textarea id="mn-note" rows="2"></textarea></label>
      <div id="mn-box"></div><p class="f-err" id="mn-err" hidden></p>
      <div class="row"><button class="primary" type="submit" id="mn-save">${ico("hand")}${esc(L("Save price", "حفظ السعر"))}</button><button type="button" id="mn-clear">${esc(L("Clear", "مسح"))}</button><span class="muted" id="mn-mode" role="status"></span></div>
    </form>
  </section>
  <section class="card stack" id="mn-todo" aria-labelledby="mn-todo-h">
    <div class="card-h"><h2 id="mn-todo-h">${esc(L("Still to price", "ما زال بلا سعر"))}</h2><span class="spacer"></span><span id="mn-todo-chip"></span>
      <p class="sub" id="mn-todo-sub"></p></div>
    <div id="mn-todo-body">${loadingHtml(L("Reading the day’s run…", "يُقرأ تشغيل اليوم…"))}</div>
  </section>
  <section class="card stack" id="mn-log" aria-labelledby="mn-log-h">
    <div class="card-h"><h2 id="mn-log-h">${esc(L("Manual prices entered", "الأسعار المُدخلة يدوياً"))}</h2><span class="spacer"></span>
      <label class="f inline"><span>${esc(L("From", "من"))}</span><input type="date" id="mn-from" dir="ltr" value="${manState.from}" max="${today}"></label>
      <label class="f inline"><span>${esc(L("To", "إلى"))}</span><input type="date" id="mn-to" dir="ltr" value="${manState.to}" max="${today}"></label>
      <button type="button" id="mn-log-go">${esc(L("Show", "عرض"))}</button><button type="button" id="mn-csv">${ico("download")}${esc(L("CSV", "CSV"))}</button></div>
    <div id="mn-log-body">${loadingHtml(L("Reading the manual prices…", "تُقرأ الأسعار اليدوية…"))}</div>
  </section>`;
  manBind(seq);
}

async function manBind(seq) {
  let basketList = [];
  try { basketList = await ensureBasket("cpi"); } catch (e) { if (alive(seq)) $("#mn-pick").innerHTML = errBox(L("The basket could not be read. ", "تعذّرت قراءة السلة. ") + dbErr(e), "mn-b-retry"); return; }
  if (!alive(seq)) return;
  const norm = (s) => String(s || "").toLowerCase().replace(/[ً-ْ]/g, "");
  const hay = basketList.map((b) => [b, norm([b.item_code, b.name_ar, b.name_en, b.brand_ar, b.brand_en, b.barcode_raw, b.qty_raw].join(" "))]);
  const pick = $("#mn-pick"), q = $("#mn-q");
  const showPick = () => {
    const t = norm(q.value.trim()); if (t.length < 2) { pick.innerHTML = ""; return; }
    const words = t.split(/\s+/), hits = hay.filter(([, h]) => words.every((w) => h.includes(w))).slice(0, 8);
    pick.innerHTML = hits.length ? hits.map(([b]) => `<button type="button" role="option" class="mn-opt" data-code="${esc(b.item_code)}"><span class="mono">${esc(b.item_code)}</span> <b dir="auto">${esc(b.name_ar || "")}</b> <span class="muted" dir="auto">${esc([b.brand_ar, b.qty_raw].filter(Boolean).join(" · "))}</span></button>`).join("")
      : `<p class="muted" style="margin:0">${esc(L("No basket line matches.", "لا يوجد بند مطابق."))}</p>`;
  };
  q.addEventListener("input", showPick);
  pick.addEventListener("click", (e) => { const b = e.target.closest("[data-code]"); if (b) manChoose(basketList.find((x) => x.item_code === b.dataset.code)); });
  const v = (id) => $("#" + id).value.trim();
  $("#mn-outlet").onchange = () => { manState.outlet = v("mn-outlet"); manTodo(seq); };
  $("#mn-date").onchange = () => { manState.date = v("mn-date") || todayDubai(); manTodo(seq); };
  $("#mn-clear").onclick = () => manReset();
  $("#mn-form").onsubmit = async (e) => {
    e.preventDefault();
    const err = $("#mn-err"), day = v("mn-date"), pr = v("mn-price"), rg = v("mn-reg"), today = todayDubai();
    const num = (s) => /^\d+(\.\d+)?$/.test(s) && +s > 0;
    const bad = !/^\d{4}-\d{2}-\d{2}$/.test(day) || day > today || day < "2026-01-01" ? L("Date: a day up to today.", "التاريخ: يوم حتى اليوم.")
      : !manState.line ? L("Choose the basket line.", "اختر بند السلة.")
      : !num(pr) ? L("Price: a number above 0 (AED).", "السعر: رقم أكبر من 0 (درهم).")
      : rg && !num(rg) ? L("Regular price: a number above 0, or leave it empty.", "السعر العادي: رقم أكبر من 0، أو اتركه فارغاً.")
      : rg && +rg < +pr ? L("The regular price is below the price paid; check both.", "السعر العادي أقل من المدفوع؛ راجع الرقمين.") : "";
    err.hidden = !bad; err.textContent = bad; if (bad) return;
    const row = { line_code: manState.line.item_code, outlet: v("mn-outlet"), price: +pr, regular_price: rg ? +rg : +pr, unit: v("mn-unit"), title: v("mn-title"), url: v("mn-url"), note: v("mn-note"),
      seen_by: v("mn-source"), entered_by: viewerName(), entered_at: new Date().toISOString(), source: "manual", currency: "AED", status: "ok" };
    const ed = manState.edit;
    $("#mn-save").disabled = true;
    try {
      if (ed && ed.day !== day) await manWrite(ed.day, (rows) => { const i = rows.findIndex((x) => x.line_code === ed.row.line_code && x.outlet === ed.row.outlet && x.status !== "withdrawn"); if (i >= 0) rows[i] = { ...rows[i], status: "withdrawn", withdrawn_at: row.entered_at, note: (rows[i].note ? rows[i].note + " · " : "") + "moved to " + day }; }, manState.loaded[ed.day]);
      await manWrite(day, (rows) => { const i = rows.findIndex((x) => x.line_code === row.line_code && x.outlet === row.outlet && x.status !== "withdrawn"); if (i >= 0) rows[i] = { ...rows[i], ...row }; else rows.push(row); }, ed && ed.day === day ? manState.loaded[day] : undefined);
      toast(L("Manual price saved", "حُفظ السعر اليدوي")); $("#mn-box").innerHTML = "";
      manReset(true); manTodo(seq); manLog(seq);
    } catch (x) {
      $("#mn-box").innerHTML = errBox((x?.conflict ? L("These manual prices changed since you opened them. Show the list again and retry; nothing was overwritten. ", "تغيّرت هذه الأسعار منذ فتحها. اعرض القائمة مجدداً وحاول؛ لم يُستبدل شيء. ") : L("Not saved: nothing was written. ", "لم يُحفظ: لم يُكتب شيء. ")) + (x?.conflict ? "" : dbErr(x)), "mn-retry");
      $("#mn-retry").onclick = () => { $("#mn-box").innerHTML = ""; if (x?.conflict) manLog(seq); else $("#mn-form").requestSubmit(); };
    } finally { $("#mn-save").disabled = false; }
  };
  $("#mn-log-go").onclick = () => { manState.from = v("mn-from"); manState.to = v("mn-to"); manLog(seq); };
  $("#mn-csv").onclick = () => manCsv();
  manTodo(seq); manLog(seq);
}
function manChoose(line, keepQuery) {
  if (!line) return;
  manState.line = line; $("#mn-pick").innerHTML = ""; if (!keepQuery) $("#mn-q").value = "";
  const c = $("#mn-chosen"); c.hidden = false;
  c.innerHTML = `<dl class="kv"><dt>${esc(L("Line", "البند"))}</dt><dd><span class="mono">${esc(line.item_code)}</span> <b dir="auto">${esc(line.name_ar || "")}</b></dd>
    <dt>${esc(L("Basket unit", "وحدة السلة"))}</dt><dd dir="auto">${esc(line.qty_raw || "—")}</dd>${line.brand_ar ? `<dt>${esc(L("Brand", "العلامة"))}</dt><dd dir="auto">${esc(line.brand_ar)}</dd>` : ""}${line.barcode_raw ? `<dt>${esc(L("Barcode", "الباركود"))}</dt><dd class="mono">${esc(line.barcode_raw)}</dd>` : ""}</dl>
    <button type="button" class="ghost" id="mn-unpick">${esc(L("Change line", "تغيير البند"))}</button>`;
  $("#mn-unpick").onclick = () => { manState.line = null; c.hidden = true; $("#mn-q").focus(); };
  $("#mn-price").focus();
}
function manReset(keepPlace) {
  manState.line = null; manState.edit = null;
  for (const id of ["mn-q", "mn-price", "mn-reg", "mn-unit", "mn-title", "mn-url", "mn-note"]) $("#" + id).value = "";
  $("#mn-chosen").hidden = true; $("#mn-pick").innerHTML = ""; $("#mn-err").hidden = true; $("#mn-mode").textContent = "";
  if (!keepPlace) { $("#mn-date").value = manState.date = todayDubai(); }
}
// read-modify-write of one day's document; expectRaw (when given) must still match, so a stale screen never overwrites
async function manWrite(day, mutate, expectRaw) {
  const path = `projects/cpi/manual/${day}`, now = await getDocStrict(path);    // a failed read throws: no write
  const raw = now ? JSON.stringify(now) : null;
  if (expectRaw !== undefined && raw !== expectRaw) { const e = new Error("conflict"); e.conflict = true; throw e; }
  const doc = now || { rows: [] }, rows = [...(doc.rows || [])];
  mutate(rows);
  const next = { ...doc, rows, version: (doc.version || 0) + 1 };
  await db.doc(path).set(next);
  manState.loaded[day] = JSON.stringify(next);
  return next;
}
// lines of the day's run that the outlet has no price for (blocked, not found, not observed), minus those entered by hand
async function manTodo(seq) {
  const body = $("#mn-todo-body"), outlet = manState.outlet, day = manState.date; if (!body) return;
  $("#mn-todo-sub").textContent = L(`${manOutletName(outlet)} · ${fmtDay(day, { year: true })}`, `${manOutletName(outlet)} · ${fmtDay(day, { year: true })}`);
  $("#mn-todo-chip").innerHTML = "";
  if (!CPI_OUTLETS.some((o) => o.code === outlet && o.daily)) { body.innerHTML = emptyHtml("hand", L("Not in the daily run", "ليس في التشغيل اليومي"), L("This outlet is not collected every day, so there is no list of missing lines. Enter what you saw.", "هذا المنفذ لا يُجمع يومياً، فلا توجد قائمة بنود ناقصة. أدخل ما رأيته.")); return; }
  body.innerHTML = loadingHtml(L("Reading the day’s run…", "يُقرأ تشغيل اليوم…"));
  try {
    const { days } = dayRunsOf(await ensureRuns("cpi")), hit = days.find((x) => x.day === day);
    if (!alive(seq)) return;
    if (!hit) { body.innerHTML = emptyHtml("calendar", L("No run on this day", "لا تشغيل في هذا اليوم"), L("There is no collection run saved for this day yet. Enter prices you saw, or pick another day.", "لا يوجد تشغيل محفوظ لهذا اليوم بعد. أدخل الأسعار التي رأيتها أو اختر يوماً آخر.")); return; }
    const [rows, b, mdoc] = await Promise.all([runRows("cpi", hit.run), ensureBasket("cpi"), getDocStrict(`projects/cpi/manual/${day}`)]);
    if (!alive(seq) || manState.outlet !== outlet || manState.date !== day) return;
    const done = new Set((mdoc?.rows || []).filter((x) => x.outlet === outlet && x.status !== "withdrawn").map((x) => x.line_code));
    const blocked = cpiBlockedSet(hit.run).has(outlet);
    const priced = new Set(rows.filter((x) => x.retailer === outlet && x.accepted === "yes" && !(blocked && x.source === "category")).map((x) => x.item_code));   // carried rows of a blocked outlet are not prices
    const asked = new Map(); for (const x of rows) if (x.retailer === outlet && !priced.has(x.item_code)) asked.set(x.item_code, x);
    // a refused barcode page leaves no row at all: every barcoded line the run did not price is still to price
    for (const l of b) if (/\d{8,14}/.test(String(l.barcode_raw || "")) && !priced.has(l.item_code) && !asked.has(l.item_code)) asked.set(l.item_code, { item_code: l.item_code, source: "barcode", status: "not_observed" });
    const byCode = new Map(b.map((x) => [x.item_code, x]));
    const todo = [...asked.values()].filter((x) => !done.has(x.item_code)).map((x) => ({ x, line: byCode.get(x.item_code) })).filter((t) => t.line)
      .sort((a, c) => (a.x.source === "barcode" ? 0 : 1) - (c.x.source === "barcode" ? 0 : 1) || String(a.line.item_code).localeCompare(String(c.line.item_code)));
    $("#mn-todo-chip").innerHTML = (blocked ? chip(L("Blocked that day", "محجوب ذلك اليوم"), "bad") + " " : "") + chip(L(`${fmtN(todo.length)} lines · ${fmtN(done.size)} entered`, `${fmtN(todo.length)} بنداً · أُدخل ${fmtN(done.size)}`), todo.length ? "warn" : "ok");
    if (!todo.length) { body.innerHTML = emptyHtml("check", L("Nothing missing", "لا شيء ناقص"), L("Every line of this outlet has a price for this day, from the run or by hand.", "كل بنود هذا المنفذ لها سعر في هذا اليوم، من التشغيل أو يدوياً.")); return; }
    const show = todo.slice(0, 60);
    body.innerHTML = `<p class="muted" style="margin:0">${esc(L("Barcoded lines first (exact products), then the rest by code. Choose a line to fill the form above.", "بنود الباركود أولاً (منتجات محددة)، ثم البقية حسب الرمز. اختر بنداً لملء النموذج أعلاه."))}</p>
      <div class="tw"><table id="mn-todo-table"><caption class="sr-only">${esc(L("Lines still to price", "بنود ما زالت بلا سعر"))}</caption><thead><tr><th scope="col">${esc(L("Code", "الرمز"))}</th><th scope="col">${esc(L("Line", "البند"))}</th><th scope="col">${esc(L("Unit", "الوحدة"))}</th><th scope="col">${esc(L("Barcode", "الباركود"))}</th><th scope="col">${esc(L("In the run", "في التشغيل"))}</th><th scope="col"><span class="sr-only">${esc(L("Action", "إجراء"))}</span></th></tr></thead><tbody>
      ${show.map(({ x, line }) => `<tr><td class="mono">${esc(line.item_code)}</td><td dir="auto">${esc(line.name_ar || "")}${line.brand_ar ? ` <span class="muted">${esc(line.brand_ar)}</span>` : ""}</td><td dir="auto">${esc(line.qty_raw || "")}</td><td class="mono">${esc(line.barcode_raw || "—")}</td><td>${chip(x.status === "not_observed" || blocked ? L("Not read", "لم يُقرأ") : L("Not found", "غير موجود"), x.status === "not_observed" || blocked ? "bad" : "grey")}</td><td><button type="button" class="ghost" data-todo="${esc(line.item_code)}">${esc(L("Enter", "أدخل"))}</button></td></tr>`).join("")}
      </tbody></table></div>${todo.length > show.length ? `<p class="muted" style="margin:0">${esc(L(`Showing ${show.length} of ${fmtN(todo.length)}. Search the line in the form for the others.`, `يُعرض ${show.length} من ${fmtN(todo.length)}. ابحث عن البند في النموذج للبقية.`))}</p>` : ""}`;
    body.onclick = (e) => { const t = e.target.closest("[data-todo]"); if (!t) return; const line = byCode.get(t.dataset.todo); manChoose(line); $("#mn-add").scrollIntoView({ block: "start", behavior: "smooth" }); };
  } catch (e) { if (alive(seq)) { body.innerHTML = errBox(L("Unable to read the day’s run right now. ", "تعذّرت قراءة تشغيل اليوم الآن. ") + dbErr(e), "mn-todo-retry"); $("#mn-todo-retry").onclick = () => manTodo(seq); } }
}
let manLogRows = [];
async function manLog(seq) {
  const body = $("#mn-log-body"); if (!body) return;
  let f = manState.from, t = manState.to;
  if (!f || !t || f > t) { body.innerHTML = errBox(L("Choose a From date on or before the To date.", "اختر تاريخ «من» قبل تاريخ «إلى» أو مساوياً له.")); return; }
  if (calDays(f, t).length > 62) { body.innerHTML = errBox(L("Choose at most 62 days.", "اختر 62 يوماً على الأكثر.")); return; }
  body.innerHTML = loadingHtml(L("Reading the manual prices…", "تُقرأ الأسعار اليدوية…"));
  try {
    const out = [], b = await ensureBasket("cpi"), byCode = new Map(b.map((x) => [x.item_code, x]));
    for (const d of calDays(f, t)) {
      const doc = await getDocStrict(`projects/cpi/manual/${d}`);
      manState.loaded[d] = doc ? JSON.stringify(doc) : null;
      for (const x of doc?.rows || []) out.push({ day: d, row: x, line: byCode.get(x.line_code) });
    }
    if (!alive(seq)) return;
    manLogRows = out.sort((a, c) => (c.day.localeCompare(a.day)) || String(c.row.entered_at || "").localeCompare(String(a.row.entered_at || "")));
    if (!out.length) { body.innerHTML = emptyHtml("hand", L("No manual prices in these days", "لا أسعار يدوية في هذه الأيام"), L("Prices you save above appear here, with who entered them and when.", "الأسعار التي تحفظها أعلاه تظهر هنا مع من أدخلها ومتى.")); return; }
    const active = out.filter((o) => o.row.status !== "withdrawn").length;
    body.innerHTML = `<p class="muted" style="margin:0">${esc(L(`${fmtN(active)} active · ${fmtN(out.length - active)} withdrawn`, `${fmtN(active)} فعّال · ${fmtN(out.length - active)} مسحوب`))}</p>
      <div class="tw"><table id="mn-log-table"><caption class="sr-only">${esc(L("Manual prices entered", "الأسعار المُدخلة يدوياً"))}</caption><thead><tr>
      <th scope="col">${esc(L("Date", "التاريخ"))}</th><th scope="col">${esc(L("Outlet", "المنفذ"))}</th><th scope="col">${esc(L("Line", "البند"))}</th><th scope="col" class="num">${esc(L("Price", "السعر"))}</th><th scope="col" class="num">${esc(L("Regular", "العادي"))}</th><th scope="col">${esc(L("Seen", "الرؤية"))}</th><th scope="col">${esc(L("Entered", "الإدخال"))}</th><th scope="col">${esc(L("Status", "الحالة"))}</th><th scope="col"><span class="sr-only">${esc(L("Actions", "إجراءات"))}</span></th></tr></thead><tbody>
      ${manLogRows.map((o, i) => { const x = o.row, off = x.status === "withdrawn"; return `<tr${off ? ' class="off"' : ""}><td>${esc(fmtDay(o.day))}</td><td>${esc(manOutletName(x.outlet))}</td><td><span class="mono">${esc(x.line_code)}</span> <span dir="auto">${esc(o.line?.name_ar || "")}</span>${x.title ? `<br><span class="muted" dir="auto">${esc(x.title)}</span>` : ""}</td><td class="num">${fmtN(x.price, 2)}</td><td class="num">${x.regular_price != null && x.regular_price !== x.price ? fmtN(x.regular_price, 2) : "—"}</td><td>${esc(manSourceName(x.seen_by))}</td><td><span dir="auto">${esc(x.entered_by || "—")}</span><br><span class="muted">${esc(x.entered_at ? fmtWhen(x.entered_at) : "")}</span></td><td>${off ? chip(L("Withdrawn", "مسحوب"), "grey") : chip(L("Manual", "يدوي"), "manual")}</td><td>${off ? "" : `<button type="button" class="ghost" data-medit="${i}">${esc(L("Edit", "تعديل"))}</button><button type="button" class="ghost danger" data-mwd="${i}">${esc(L("Withdraw", "سحب"))}</button>`}</td></tr>`; }).join("")}
      </tbody></table></div><div id="mn-log-confirm"></div>`;
    body.onclick = async (e) => {
      const ed = e.target.closest("[data-medit]"), wd = e.target.closest("[data-mwd]");
      if (ed) { const o = manLogRows[+ed.dataset.medit]; manEdit(o); return; }
      if (wd) {
        const o = manLogRows[+wd.dataset.mwd];
        $("#mn-log-confirm").innerHTML = `<div class="confirm" role="alert"><span>${esc(L(`Withdraw the manual price of ${o.row.line_code} (${manOutletName(o.row.outlet)}, ${fmtDay(o.day)})? It stays in the record as withdrawn.`, `سحب السعر اليدوي للبند ${o.row.line_code} (${manOutletName(o.row.outlet)}، ${fmtDay(o.day)})؟ يبقى في السجل كمسحوب.`))}</span><button type="button" class="danger" id="mn-wd-yes">${esc(L("Withdraw", "سحب"))}</button><button type="button" id="mn-wd-no">${esc(L("Keep", "إبقاء"))}</button></div>`;
        $("#mn-wd-no").onclick = () => { $("#mn-log-confirm").innerHTML = ""; };
        $("#mn-wd-yes").onclick = async () => {
          try { await manWrite(o.day, (rows) => { const i = rows.findIndex((x) => x.line_code === o.row.line_code && x.outlet === o.row.outlet && x.entered_at === o.row.entered_at && x.status !== "withdrawn"); if (i >= 0) rows[i] = { ...rows[i], status: "withdrawn", withdrawn_at: new Date().toISOString() }; }, manState.loaded[o.day]); toast(L("Manual price withdrawn", "سُحب السعر اليدوي")); manLog(seq); manTodo(seq); }
          catch (x) { $("#mn-log-confirm").innerHTML = errBox((x?.conflict ? L("These manual prices changed since you opened them. Show the list again; nothing was changed. ", "تغيّرت هذه الأسعار منذ فتحها. اعرض القائمة مجدداً؛ لم يتغير شيء. ") : L("Not withdrawn: nothing was written. ", "لم يُسحب: لم يُكتب شيء. ")) + (x?.conflict ? "" : dbErr(x)), "mn-wd-retry"); $("#mn-wd-retry").onclick = () => manLog(seq); }
        };
      }
    };
  } catch (e) { if (alive(seq)) { body.innerHTML = errBox(L("Unable to load the manual prices right now. ", "تعذّر تحميل الأسعار اليدوية الآن. ") + dbErr(e), "mn-log-retry"); $("#mn-log-retry").onclick = () => manLog(seq); } }
}
function manEdit(o) {
  const x = o.row;
  manState.edit = { day: o.day, row: x };
  $("#mn-date").value = manState.date = o.day; $("#mn-outlet").value = manState.outlet = x.outlet;
  if (o.line) manChoose(o.line); else manState.line = { item_code: x.line_code, name_ar: x.line_code };
  $("#mn-price").value = x.price ?? ""; $("#mn-reg").value = x.regular_price != null && x.regular_price !== x.price ? x.regular_price : "";
  $("#mn-unit").value = x.unit || ""; $("#mn-title").value = x.title || ""; $("#mn-url").value = x.url || ""; $("#mn-note").value = x.note || "";
  if (x.seen_by) $("#mn-source").value = x.seen_by;
  $("#mn-mode").textContent = L(`Editing the price of ${fmtDay(o.day)}`, `تعديل سعر ${fmtDay(o.day)}`);
  $("#mn-add").scrollIntoView({ block: "start", behavior: "smooth" });
  $("#mn-price").focus();
}
function manCsv() {
  if (!manLogRows.length) { toast(L("Nothing to download in these days", "لا شيء للتنزيل في هذه الأيام"), true); return; }
  const cols = ["date", "outlet", "line_code", "line_name", "basket_unit", "price", "regular_price", "unit_seen", "title_seen", "url", "seen_by", "note", "entered_by", "entered_at", "status", "source"];
  const rows = manLogRows.map((o) => ({ date: o.day, outlet: o.row.outlet, line_code: o.row.line_code, line_name: o.line?.name_ar || "", basket_unit: o.line?.qty_raw || "", price: o.row.price, regular_price: o.row.regular_price, unit_seen: o.row.unit || "", title_seen: o.row.title || "", url: o.row.url || "", seen_by: o.row.seen_by || "", note: o.row.note || "", entered_by: o.row.entered_by || "", entered_at: o.row.entered_at || "", status: o.row.status || "ok", source: "manual" }));
  offerFile(`CPI manual prices ${manState.from}_${manState.to}.csv`, toCsv(rows, cols));
}

// ---------------- SPPI: the manual rows of every collection, and the same card as Price History
async function pgManualSppi(r, seq) {
  $("#page").innerHTML = titleRow(L("Manual Entry", "الإدخال اليدوي"), `<button class="primary" type="button" id="ms-add">${ico("hand")}${esc(L("Add price manually", "إضافة سعر يدوياً"))}</button>`) + `
  <section class="card stack" aria-labelledby="ms-h"><div class="card-h"><h2 id="ms-h">${esc(L("Manual prices entered", "الأسعار المُدخلة يدوياً"))}</h2>
    <p class="sub">${esc(L("For outlets the scrapers cannot read (blocked, PC only, manual), like Emirates or Emirates Holidays. Saved into the collection with source “manual”.", "للمنافذ التي لا تقرؤها الكاشطات (محجوبة، على الحاسوب فقط، يدوية)، مثل طيران الإمارات وEmirates Holidays. يُحفظ في الجمع بالمصدر «يدوي»."))}</p></div>
    <div id="ms-body">${loadingHtml(L("Reading the collections…", "تُقرأ مرات الجمع…"))}</div></section>`;
  let d;
  try { d = await sppiLoad(); } catch (e) { if (alive(seq)) { $("#ms-body").innerHTML = errBox(L("Unable to read the SPPI data right now. ", "تعذّرت قراءة بيانات SPPI الآن. ") + dbErr(e), "ms-retry"); $("#ms-retry").onclick = () => { sppiCache = null; rerender(); }; } return; }
  if (!alive(seq)) return;
  if (!d?.meta) { $("#ms-add").disabled = true; $("#ms-body").innerHTML = emptyHtml("hand", L("No SPPI basket yet", "لا سلة SPPI بعد"), L("Start the SPPI basket under Price History › Commodities first.", "ابدأ سلة SPPI أولاً من سجل الأسعار › السلع.")); return; }
  const draw = () => {
    const rows = []; for (const w of d.weeks) for (const x of d.obs.get(w.id)?.rows || []) if (x.source === "manual") rows.push({ w, x });
    rows.sort((a, c) => String(c.x.entered_at || "").localeCompare(String(a.x.entered_at || "")));
    const itemName = (code) => { const i = d.items.find((y) => y.code === code); return i ? sppiName(i) : code; };
    const outName = (code) => { const o = d.outlets.find((y) => y.code === code); return o ? sppiName(o) : code; };
    $("#ms-body").innerHTML = !rows.length ? emptyHtml("hand", L("No manual prices yet", "لا أسعار يدوية بعد"), L("Use “Add price manually” for an outlet the scrapers could not read.", "استخدم «إضافة سعر يدوياً» لمنفذ لم تقرأه الكاشطات."))
      : `<div class="tw"><table id="ms-table"><caption class="sr-only">${esc(L("SPPI manual prices", "أسعار SPPI اليدوية"))}</caption><thead><tr><th scope="col">${esc(L("Collection", "الجمع"))}</th><th scope="col">${esc(L("Outlet", "المنفذ"))}</th><th scope="col">${esc(L("Item", "البند"))}</th><th scope="col">${esc(L("Leg", "الاتجاه"))}</th><th scope="col" class="num">${esc(L("Lowest", "الأدنى"))}</th><th scope="col" class="num">${esc(L("Highest", "الأعلى"))}</th><th scope="col" class="num">${esc(L("Price", "السعر"))}</th><th scope="col">${esc(L("Entered", "الإدخال"))}</th><th scope="col">${esc(L("Status", "الحالة"))}</th><th scope="col"><span class="sr-only">${esc(L("Actions", "إجراءات"))}</span></th></tr></thead><tbody>
        ${rows.map(({ w, x }, i) => `<tr${x.status === "withdrawn" ? ' class="off"' : ""}><td>${esc(fmtMonth(w.month) + " · " + sppiWeekLabel(w))}</td><td>${esc(outName(x.outlet))}</td><td>${esc(itemName(x.item))}</td><td>${esc(x.leg || "")}</td><td class="num">${fmtN(x.lowest)}</td><td class="num">${fmtN(x.highest)}</td><td class="num">${fmtN(x.price)}</td><td><span dir="auto">${esc(x.entered_by || "—")}</span><br><span class="muted">${esc(x.entered_at ? fmtWhen(x.entered_at) : "")}</span></td><td>${x.status === "withdrawn" ? chip(L("Withdrawn", "مسحوب"), "grey") : chip(L("Manual", "يدوي"), "manual")}</td><td>${x.status === "withdrawn" ? "" : `<button type="button" class="ghost" data-sedit="${i}">${esc(L("Edit", "تعديل"))}</button>`}</td></tr>`).join("")}
        </tbody></table></div>`;
    $("#ms-body").onclick = (e) => { const b = e.target.closest("[data-sedit]"); if (!b) return; const o = rows[+b.dataset.sedit]; sppiManualCard({ row: o.x, wid: o.w.id, onSaved: draw }); };
  };
  $("#ms-add").onclick = () => sppiManualCard({ onSaved: draw });
  draw();
}
