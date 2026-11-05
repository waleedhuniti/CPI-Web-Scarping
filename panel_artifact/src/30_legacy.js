// ------------------------------------------------------------ run tab
function hasGroups() { return basket.some((i) => i.group_code); }
function renderRunPicks() {
  const p = P(); if (!p) return;
  $("#run-actors").innerHTML = Object.entries(p.actors || {}).map(([k, a]) => `<label><input type="checkbox" value="${esc(k)}" ${a.enabled ? "checked" : ""}>${esc(a.label || k)}</label>`).join("") || `<span class="muted">${L("No Actor; add one under Scrapers › Apify actors.", "لا يوجد Actor؛ أضفه من الكاشطات › Apify actors.")}</span>`;
  const groups = groupsOf(basket);
  $("#run-groups-box").hidden = !groups.length;
  $("#run-codes-box").hidden = p.kind !== "barcode";
  $("#run-groups").innerHTML = groups.map(([c, n]) => `<label><input type="checkbox" value="${esc(c)}">${esc(n)}</label>`).join("");
  $$("#run-actors input, #run-groups input").forEach((i) => i.addEventListener("change", updateRunCount));
  updateRunCount();
}
function runSelection() {
  const groups = $$("#run-groups input:checked").map((i) => i.value);
  const codes = $("#run-codes").value.split(/[\s,،]+/).filter(Boolean);
  let items = basket;
  if (groups.length) items = items.filter((i) => groups.includes(i.group_code));
  if (codes.length && P().kind === "barcode") items = items.filter((i) => codes.includes(i.item_code));
  return { actors: $$("#run-actors input:checked").map((i) => i.value), items };
}
function updateRunCount() {
  const s = runSelection(), p = P();
  if (p.kind === "barcode") {
    const n = s.items.filter((i) => gtinValid(i.barcode_raw)).length;
    $("#run-count").textContent = L(`${n} lines with a valid barcode will be searched by ${s.actors.length} Actor(s). Lines without a barcode are not in this run.`, `${n} صنف بباركود صالح سيُبحث عنه عبر ${s.actors.length} Actor. الأصناف بدون باركود لا يشملها هذا التشغيل.`);
  } else if (p.kind === "list") {
    const n = s.items.filter((i) => i.enabled !== false && i.enabled !== "no").length;
    $("#run-count").textContent = n ? L(`${n} enabled items will be read from the page.`, `${n} عنصر مفعّل سيُستخرج من الصفحة.`) : L("The basket is empty: every row on the page will be saved.", "السلة فارغة: ستُحفظ كل الصفوف التي في الصفحة.");
  } else $("#run-count").textContent = L("Every row the Actor returns will be saved.", "ستُحفظ كل الصفوف التي يرجعها الـ Actor.");
}
$("#run-codes").addEventListener("input", updateRunCount);

$("#btn-run").addEventListener("click", async () => {
  if (!mcp) return toast(L("Apify is not available in this view; open the page in claude.ai with the Apify connector", "Apify غير متاح في هذا العرض؛ افتح الصفحة داخل claude.ai مع موصل Apify"), true);
  if (job?.running) return;
  const sel = runSelection(), p = P();
  if (!sel.actors.length) return toast(L("Choose at least one Actor", "اختر Actor واحداً على الأقل"), true);
  if (p.kind === "barcode" && !sel.items.some((i) => gtinValid(i.barcode_raw))) return toast(L("No line with a valid barcode in this choice", "لا يوجد صنف بباركود صالح في هذا الاختيار"), true);
  if (basketDirty) toast(L("The run uses the basket as shown now, even before saving", "التشغيل يستخدم السلة كما تظهر الآن، حتى قبل الحفظ"));
  startJob(current, sel);
});
$("#btn-stop").addEventListener("click", () => { if (job) { job.stop = true; log("stop requested: no new batches will start"); } });

function log(m) { if (!job) return; job.log.push(`${new Date().toLocaleTimeString("en-GB")}  ${m}`); renderJob(); }
function renderJob() {
  const box = $("#job");
  if (!job || job.pid !== current) { box.hidden = true; $("#btn-run").disabled = !!job?.running; $("#btn-stop").disabled = true; return; }
  box.hidden = false;
  const st = job.running ? [L("Running", "يعمل"), "warn"] : job.status === "done" ? [L("Completed", "انتهى"), "ok"] : job.status === "stopped" ? [L("Stopped", "أُوقف"), "warn"] : [L("Failed", "خطأ"), "bad"];
  $("#job-state").textContent = st[0]; $("#job-state").className = "chip " + st[1];
  $("#job-bars").innerHTML = Object.entries(job.progress).map(([k, g]) => `<div><div class="row" style="justify-content:space-between"><span>${esc(g.label)}</span><span class="muted mono">${g.done}/${g.total}${g.failed ? ` · ${g.failed} failed` : ""}</span></div><div class="bar"><i style="width:${g.total ? (100 * g.done) / g.total : 0}%"></i></div></div>`).join("");
  const l = $("#job-log"); l.textContent = job.log.join("\n"); l.scrollTop = l.scrollHeight;
  $("#job-summary").innerHTML = job.summary ? summaryHtml(job.summary) : "";
  $("#btn-run").disabled = job.running; $("#btn-stop").disabled = !job.running;
}
function summaryHtml(sum) {
  return `<div class="tw"><table><thead><tr><th>Actor</th><th>${L("Rows", "صفوف")}</th><th>${L("Accepted", "مقبول")}</th><th>${L("Details", "التفاصيل")}</th></tr></thead><tbody>${Object.values(sum).map((v) =>
    `<tr><td>${esc(v.label)}</td><td class="num">${v.lines}</td><td class="num"><b>${v.accepted}</b></td><td>${Object.entries(v.statuses).map(([s, n]) => `${esc(statusLabel(s))}: ${n}`).join(" · ")}</td></tr>`).join("")}</tbody></table></div>`;
}

async function startJob(pid, sel) {
  const p = projects[pid];
  job = { pid, running: true, stop: false, status: "running", log: [], progress: {}, summary: null };
  const runId = new Date().toISOString().replace(/[-:]/g, "").slice(0, 13) + "-" + Math.random().toString(36).slice(2, 6);
  const startedAt = new Date().toISOString();
  log(`${p.name}: ${sel.actors.length} Actor`);
  const results = [], summary = {};
  try {
    for (const key of sel.actors) {
      const cfg = p.actors[key], label = cfg.label || key;
      const runs = buildRuns(cfg, sel.items);
      job.progress[key] = { label, done: 0, total: runs.length, failed: 0 };
      log(`${label}: ${runs.length} run(s) of ${cfg.actor}`);
      const rows = [], searched = new Set(), failed = new Set(); let nextIdx = 0;
      const worker = async () => {
        while (nextIdx < runs.length && !job.stop) {
          const r = runs[nextIdx++];
          try {
            const { runId: rid, items } = await runActor(cfg, r.input, () => job.stop);
            const parsed = PARSERS[cfg.parser](items, r.batch, cfg);
            rows.push(...parsed.rows); parsed.searched?.forEach((c) => searched.add(c));
            log(`${label}: run ${rid} — ${items.length} items, ${parsed.rows.length} rows`);
          } catch (e) {
            (r.batch || []).forEach((c) => failed.add(c)); job.progress[key].failed++;
            log(`${label}: ${r.batch ? r.batch[0] + "…" : "run"} failed: ${mcpErr(e)}`);
          }
          job.progress[key].done++; renderJob();
        }
      };
      await Promise.all(Array.from({ length: Math.max(1, Math.min(+cfg.parallel_runs || 1, runs.length)) }, worker));
      let res;
      if (p.kind === "barcode") res = matchBarcode(key, label, sel.items, rows, searched, failed);
      else if (p.kind === "list") res = matchList(label, sel.items, rows, p.list_key || "name");
      else res = rows.map((r) => ({ actor: label, ...r, status: "row", accepted: "yes" }));
      if (p.kind !== "barcode" && failed.size === 0 && job.progress[key].failed) res = [];
      results.push(...res);
      const statuses = {}; res.forEach((r) => (statuses[r.status] = (statuses[r.status] || 0) + 1));
      summary[key] = { label, lines: res.length, accepted: res.filter((r) => r.accepted === "yes").length, statuses };
      log(`${label}: ${summary[key].accepted} of ${res.length} accepted`);
    }
    job.status = job.stop ? "stopped" : "done";
  } catch (e) { job.status = "error"; log("ERROR: " + mcpErr(e)); }
  job.summary = summary; job.running = false; renderJob();
  try {
    const n = await saveChunks(`projects/${pid}/runs/${runId}/rows`, "rows", results, []);
    const accepted = results.filter((r) => r.accepted === "yes").length;
    await db.doc(`projects/${pid}/runs/${runId}`).set({ startedAt, finishedAt: new Date().toISOString(), status: job.status, summary, chunks: n, count: results.length, accepted, log: job.log.slice(-200) });
    projects[pid] = { ...projects[pid], lastRun: { at: startedAt, status: job.status, accepted } };
    await db.doc(`projects/${pid}`).update({ lastRun: projects[pid].lastRun });
    log(`saved run ${runId}`); toast(L("The run ended and its results were saved", "انتهى التشغيل وحُفظت النتائج"));
    if (current === pid) loadRuns();
  } catch (e) { log("could not save results: " + dbErr(e)); toast(dbErr(e), true); }
}

// ------------------------------------------------------------ basket tab
let bPage = 0; const PER = 50;
function cols() { return P()?.columns || []; }
const COL_EN = { item_code: "Code", name_ar: "Item", brand_ar: "Brand", barcode_raw: "Barcode", qty_raw: "Quantity", origin_raw: "Origin", cpi_group: "Group", match_mode: "Pricing method",
  category: "Category", commodity: "Commodity", unit: "Unit", enabled: "Enabled", name: "Name", stage: "Stage", area: "Area", type: "Unit type", beds: "Rooms", company: "Company", isic: "Activity (ISIC)", source: "Source" };
const colLabel = (c) => (LANG === "ar" ? c.label : COL_EN[c.key] || c.label || c.key);
function groupsOf(items) { const g = new Map(); items.forEach((i) => i.group_code && g.set(i.group_code, i.group_name || i.group_code)); return [...g].sort(); }
function fillGroupSelect() {
  const g = groupsOf(basket); $("#b-group").hidden = !g.length;
  $("#b-group").innerHTML = `<option value="">${L("All groups", "كل المجموعات")}</option>` + g.map(([c, n]) => `<option value="${esc(c)}">${esc(n)}</option>`).join("");
}
function filtered() {
  const q = $("#b-search").value.trim().toLowerCase(), g = $("#b-group").value;
  return basket.map((it, idx) => ({ it, idx })).filter(({ it }) => (!g || it.group_code === g) && (!q || cols().map((c) => it[c.key]).join(" ").toLowerCase().includes(q)));
}
function cell(it, c) {
  const v = it[c.key];
  if (c.type === "bool") return `<td><input type="checkbox" data-tog="${esc(c.key)}" ${v !== false && v !== "no" ? "checked" : ""} aria-label="${esc(colLabel(c))}"></td>`;
  if (c.key === "barcode_raw" && v) return `<td class="num mono">${esc(v)}${gtinValid(v) ? "" : ` <span class="chip warn">${L("invalid", "غير صالح")}</span>`}</td>`;
  if (c.key === "match_mode") return `<td>${esc((LANG === "ar" ? { barcode: "باركود", spec: "مسح الأقسام", name: "اسم/موديل (كتالوج)", service: "خدمة", market: "سعر سوق" } : { barcode: "Barcode", spec: "Category crawl", name: "Name/model (catalogue)", service: "Service", market: "Market price" })[v] || v || "")}</td>`;
  if (c.key === "qty_raw" && P().kind === "barcode") return `<td>${esc(v)}${v && !itemQty(it) ? ` <span class="chip warn">${L("not read", "لم تُقرأ")}</span>` : ""}</td>`;
  return `<td class="${c.type === "code" ? "num mono" : ""}">${esc(v)}</td>`;
}
function renderBasket() {
  const p = P(); if (!p) return;
  $("#b-table thead").innerHTML = `<tr>${cols().map((c) => `<th scope="col">${esc(colLabel(c))}</th>`).join("")}<th scope="col"><span class="sr-only">${esc(L("Actions", "إجراءات"))}</span></th></tr>`;
  const rows = filtered(), pages = Math.max(1, Math.ceil(rows.length / PER)); bPage = Math.min(bPage, pages - 1);
  $("#b-table tbody").innerHTML = rows.length ? rows.slice(bPage * PER, (bPage + 1) * PER).map(({ it, idx }) =>
    `<tr data-i="${idx}">${cols().map((c) => cell(it, c)).join("")}<td style="white-space:nowrap"><button class="ghost" type="button" data-edit>${L("Edit", "تعديل")}</button><button class="ghost" type="button" data-del style="color:var(--bad)">${L("Delete", "حذف")}</button></td></tr>`).join("")
    : `<tr><td colspan="${cols().length + 1}" class="empty">${basket.length ? L("No results for this search.", "لا نتائج لهذا البحث.") : L("The basket is empty. Add a line or import a CSV with the project columns.", "السلة فارغة. أضف عنصراً أو استورد ملف CSV بأعمدة المشروع.")}</td></tr>`;
  $("#b-page").textContent = `${bPage + 1} / ${pages}`;
  $("#b-info").textContent = basketLoaded ? `${basket.length.toLocaleString("en")} ${L("lines", "عنصر")}${basketDirty ? L(" · unsaved changes", " · تعديلات غير محفوظة") : ""}` : L("Loading the basket…", "تُحمَّل السلة…");
  // Save is blocked until the basket has loaded and something changed: an unread basket is never written over
  const sv = $("#b-save"); sv.setAttribute("aria-disabled", String(!basketLoaded || !basketDirty)); sv.title = !basketLoaded ? L("The basket has not loaded yet", "لم تُحمَّل السلة بعد") : !basketDirty ? L("Nothing to save yet", "لا تعديلات للحفظ") : "";
  $$("#b-table [data-edit]").forEach((b) => b.addEventListener("click", () => editItem(+b.closest("tr").dataset.i)));
  $$("#b-table [data-del]").forEach((b) => b.addEventListener("click", () => { basket.splice(+b.closest("tr").dataset.i, 1); basketDirty = true; renderBasket(); toast(L("Line removed; save the basket to keep it", "حُذف العنصر؛ احفظ السلة لتثبيت الحذف")); }));
  $$("#b-table [data-tog]").forEach((b) => b.addEventListener("change", () => { basket[+b.closest("tr").dataset.i][b.dataset.tog] = b.checked; basketDirty = true; renderBasket(); }));
}
$("#b-search").addEventListener("input", () => { bPage = 0; renderBasket(); });
$("#b-group").addEventListener("change", () => { bPage = 0; renderBasket(); });
$("#b-prev").addEventListener("click", () => { bPage = Math.max(0, bPage - 1); renderBasket(); });
$("#b-next").addEventListener("click", () => { bPage++; renderBasket(); });

let editing = null;
function editItem(idx) {
  editing = idx; const it = idx === null ? {} : basket[idx];
  $("#dlg-title").textContent = idx === null ? L("New line", "عنصر جديد") : L("Edit line", "تعديل عنصر");
  $("#dlg-fields").innerHTML = cols().map((c, i) => c.type === "bool"
    ? `<label class="f"><span>${esc(colLabel(c))}</span><select id="fld-${i}" name="${esc(c.key)}"><option value="yes">${L("Yes", "نعم")}</option><option value="no">${L("No", "لا")}</option></select></label>`
    : `<label class="f"><span>${esc(colLabel(c))}</span><input id="fld-${i}" name="${esc(c.key)}" ${c.type === "code" ? 'dir="ltr" class="mono"' : ""}></label>`).join("");
  cols().forEach((c, i) => { const el = $("#fld-" + i); el.value = c.type === "bool" ? (it[c.key] === false || it[c.key] === "no" ? "no" : "yes") : it[c.key] ?? ""; });
  preview(); $("#dlg").showModal();
}
function formItem() {
  const it = editing === null ? {} : { ...basket[editing] };
  cols().forEach((c, i) => { const v = $("#fld-" + i).value.trim(); it[c.key] = c.type === "bool" ? v !== "no" : v; });
  if (P().kind === "barcode") {
    const q = parseQty(it.qty_raw); it.qty_total = q?.total ?? null; it.qty_unit = q?.unit ?? "";
    if (gtinValid(it.barcode_raw)) it.match_mode = "barcode"; else if (!it.match_mode || it.match_mode === "barcode") it.match_mode = "spec";
  }
  return it;
}
function preview() {
  if (P().kind !== "barcode") return ($("#dlg-preview").textContent = "");
  const it = formItem(), q = itemQty(it);
  $("#dlg-preview").textContent = `${L("Barcode", "الباركود")}: ${it.barcode_raw ? (gtinValid(it.barcode_raw) ? L("valid, searched as ", "صالح، يُبحث بـ ") + searchForm(it.barcode_raw) : L("invalid, not searched", "غير صالح، لن يُبحث عنه")) : L("none", "لا يوجد")} · ${L("Size", "الحجم")}: ${q ? q.total + " " + q.unit : L("not read; the result goes to review", "لم يُقرأ، ستذهب النتيجة للمراجعة")}`;
}
$("#dlg-form").addEventListener("input", preview);
$("#dlg").addEventListener("close", () => {
  if ($("#dlg").returnValue !== "ok") return;
  const it = formItem();
  if (editing === null) basket.unshift(it); else basket[editing] = it;
  basketDirty = true; fillGroupSelect(); renderBasket(); renderRunPicks();
});
$("#b-add").addEventListener("click", () => editItem(null));
// read the basket of `pid` into the mounted editor; a failed read shows the pink box with Retry and keeps Save blocked
async function mountBasketLoad(pid, seq) {
  if (!(basketLoaded && S[pid]?.basket)) basketLoaded = false;
  renderBasket();
  let b;
  try { b = await ensureBasket(pid); }
  catch (e) {
    if (!alive(seq)) return;
    basketLoaded = false; renderBasket();
    const slot = document.querySelector('#page [data-slot="basket"]');
    if (slot) { slot.hidden = true; slot.insertAdjacentHTML("beforebegin", `<div id="b-loaderr">${errBox(L("Unable to load the basket right now; nothing can be saved until it loads. ", "تعذّر تحميل السلة الآن؛ لا يمكن الحفظ حتى تُحمَّل. ") + dbErr(e), "b-retry")}</div>`); bindRetry(); }
    return;
  }
  if (!alive(seq) || current !== pid) return;
  if (!basketLoaded || !basketDirty) basket = b;     // keep unsaved edits made on this project
  basketLoaded = true; bPage = 0; fillGroupSelect(); renderBasket();
}
$("#b-save").addEventListener("click", async () => {
  if (!basketLoaded) return toast(L("The basket has not loaded, so nothing was saved", "لم تُحمَّل السلة، لذلك لم يُحفظ شيء"), true);
  if (!basketDirty) return toast(L("Nothing to save yet", "لا تعديلات للحفظ"));
  try {
    await saveChunks(`projects/${current}/basket`, "items", basket);
    const nb = basket.filter((i) => gtinValid(i.barcode_raw)).length;
    const cnt = (m) => basket.filter((i) => i.match_mode === m).length;
    await saveProject({ itemCount: basket.length, barcodeCount: nb, specCount: basket.some((i) => i.match_mode) ? cnt("spec") : basket.length - nb, nameCount: cnt("name"), serviceCount: cnt("service") + cnt("market") });
    basketDirty = false; renderBasket(); renderRunPicks(); toast(L(`Basket saved (${basket.length} lines)`, `حُفظت السلة (${basket.length} عنصر)`));
  } catch (e) { toast(dbErr(e), true); }
});

function toCsv(rows, columns) {
  const q = (v) => { const s = v === null || v === undefined ? "" : typeof v === "object" ? JSON.stringify(v) : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  return "﻿" + [columns.join(","), ...rows.map((r) => columns.map((c) => q(r[c])).join(","))].join("\n");
}
function parseCsv(text) {
  const rows = []; let row = [], cur = "", inQ = false;
  text = text.replace(/^﻿/, "");
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQ) { if (ch === '"') { if (text[i + 1] === '"') { cur += '"'; i++; } else inQ = false; } else cur += ch; }
    else if (ch === '"') inQ = true; else if (ch === ",") { row.push(cur); cur = ""; }
    else if (ch === "\n" || ch === "\r") { if (ch === "\r" && text[i + 1] === "\n") i++; row.push(cur); rows.push(row); row = []; cur = ""; }
    else cur += ch;
  }
  if (cur || row.length) { row.push(cur); rows.push(row); }
  const [head, ...body] = rows.filter((r) => r.some((x) => x.trim()));
  return body.map((r) => Object.fromEntries(head.map((h, i) => [h.trim(), r[i] ?? ""])));
}
async function offerFile(filename, text) {
  if (!downloads) return toast(L("Downloads are not available in this view", "التنزيل غير متاح في هذا العرض"), true);
  try { await downloads.save({ filename, data: new Blob([text], { type: "text/csv;charset=utf-8" }) }); }
  catch (e) { if (e?.code !== "cancelled" && e?.code !== "declined") toast(e?.message || L("The download did not finish", "لم يكتمل التنزيل"), true); }
}
// ------------------------------------------------------------ Excel download in the catalogue layout (navy header, white rows, photos)
const EXCELJS = "https://cdnjs.cloudflare.com/ajax/libs/exceljs/4.4.0/exceljs.min.js";
let excelLib = null;
function loadExcel() {
  return excelLib ??= new Promise((ok, fail) => {
    const s = document.createElement("script"); s.src = EXCELJS;
    s.onload = () => ok(window.ExcelJS); s.onerror = () => { excelLib = null; fail(new Error(L("Could not load the Excel library", "تعذّر تحميل مكتبة Excel"))); };
    document.head.appendChild(s);
  });
}
const OUTLET = { carrefour: "Carrefour", lulu: "Lulu", spinneys: "Spinneys" };
function catalogueSheet(rows) {
  const found = rows.filter((r) => r.accepted === "yes" && r.title)
    .sort((a, b) => String(b.run_date).localeCompare(String(a.run_date)) || String(a.group_code).localeCompare(String(b.group_code)) || String(a.retailer).localeCompare(String(b.retailer)));
  return {
    title: "Dubai bulk product catalogue",
    subtitle: `${found.length.toLocaleString("en")} prices • ${[...new Set(found.map((r) => r.run_date))].sort().join(", ")} • Choose Yes in the first column, then filter`,
    headers: ["Select", "Outlet", "Product name", "Photo", "Price (AED)", "Pack / size", "Brand", "Retailer ID", "Availability", "Category", "Product URL", "Photo URL", "Collected (Dubai)", "Notes", "obs_state"],
    widths: [8, 11, 42, 13, 11, 14, 14, 12, 12, 24, 46, 30, 16, 46, 16],
    photoCol: 4, priceCols: [5], select: true,
    rows: found.map((r) => ["No", OUTLET[r.retailer] || r.retailer || "", r.title, r.photo || "", r.price === "" ? null : Number(r.price),
      r.size || r.basket_qty || "", r.brand || "", r.retailer_id || (String(r.url || "").match(/\/p\/([^/?]+)/) || [])[1] || "", "Available",
      [r.group_name, r.section].filter(Boolean).join(" · "), r.url || "", r.photo || "", r.run_date || "",
      [r.note, `Basket item: ${r.name || ""} (${r.item_code || ""})`].filter(Boolean).join(" · "), r.obs_state || "seen"]),
  };
}
function globalSheet(rows) {
  const ok = rows.filter((r) => r.accepted === "yes").sort((a, b) => String(b.run_date).localeCompare(String(a.run_date)) || String(a.category).localeCompare(String(b.category)));
  const num = (v) => (v === "" || v == null || isNaN(Number(String(v).replace(/[%,]/g, ""))) ? (v ?? "") : Number(String(v).replace(/[%,]/g, "")));
  return {
    title: "Global commodity prices",
    subtitle: `${ok.length.toLocaleString("en")} prices • ${[...new Set(ok.map((r) => r.run_date))].length} days • Trading Economics`,
    headers: ["Commodity", "Category", "Price", "Unit", "Change", "Change %", "Weekly %", "Monthly %", "YTD %", "YoY %", "Price date", "Collected (Dubai)", "price_date", "collected_dubai"],
    widths: [30, 16, 12, 18, 10, 10, 10, 10, 10, 10, 14, 16, 14, 18], priceCols: [3, 5],
    rows: ok.map((r) => [r.commodity || r.name || "", r.category || "", num(r.price), r.unit || "", num(r.change), r.pct ?? "", r.weekly ?? "", r.monthly ?? "", r.ytd ?? "", r.yoy ?? "", r.price_date || "", r.run_date || "", r.price_date || "", r.collected_dubai || ""]),
  };
}
async function offerXlsx(filename, sheet) {
  if (!downloads) return toast(L("Downloads are not available in this view", "التنزيل غير متاح في هذا العرض"), true);
  if (!sheet.rows.length) return toast(L("No prices to download", "لا توجد أسعار للتنزيل"), true);
  const ExcelJS = await loadExcel();
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet(sheet.photoCol ? "Catalogue" : "Prices", { views: [{ state: "frozen", ySplit: 5 }] });
  ws.getCell("A2").value = sheet.title; ws.getCell("A2").font = { size: 16, bold: true, color: { argb: "FF173653" } };
  ws.getCell("A3").value = sheet.subtitle; ws.getCell("A3").font = { size: 10, color: { argb: "FF627184" } };
  const head = ws.getRow(5); head.height = 32; const imgIds = new Map();
  sheet.headers.forEach((h, i) => {
    const c = head.getCell(i + 1); c.value = h;
    c.font = { bold: true, color: { argb: "FFFFFFFF" } };
    c.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF223F62" } };
    c.alignment = { horizontal: "center", vertical: "middle", wrapText: true };
  });
  sheet.widths.forEach((w, i) => (ws.getColumn(i + 1).width = w));
  sheet.rows.forEach((vals, k) => {
    const row = ws.getRow(6 + k);
    vals.forEach((v, i) => {
      const c = row.getCell(i + 1);
      if (sheet.photoCol === i + 1) {
        c.value = null;
        if (v && thumbs.has(v)) {
          if (!imgIds.has(v)) imgIds.set(v, wb.addImage({ base64: thumbs.get(v), extension: "jpeg" }));
          ws.addImage(imgIds.get(v), { tl: { col: i + 0.1, row: 5 + k + 0.1 }, ext: { width: 72, height: 72 } });
        }
      } else c.value = v === "" ? null : v;
      c.alignment = { vertical: "middle", wrapText: i === 2 };
      if (sheet.priceCols.includes(i + 1)) c.numFmt = "#,##0.00";
      if (sheet.select && i === 0) c.dataValidation = { type: "list", allowBlank: false, formulae: ['"No,Yes"'] };
    });
    if (sheet.photoCol) row.height = 60;
  });
  ws.autoFilter = { from: { row: 5, column: 1 }, to: { row: 5 + sheet.rows.length, column: sheet.headers.length } };
  const buf = await wb.xlsx.writeBuffer();
  try { await downloads.save({ filename, data: new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }) }); }
  catch (e) { if (e?.code !== "cancelled" && e?.code !== "declined") toast(e?.message || L("The download did not finish", "لم يكتمل التنزيل"), true); }
}
// ------------------------------------------------------------ daily product catalogue: rows (photo, size, unit price) and photos per section
let catDoc = null, catData = null, catIx = null; const catThumbs = {}, catGot = {};
async function ensureCat(groups) {
  if (!catData) { catData = await (await fetch("/_blob/" + catDoc.rows_asset)).json(); catIx = Object.fromEntries(catData.cols.map((c, i) => [c, i])); }
  for (const g of groups) {
    const id = (catDoc.thumbs_assets || {})[g];
    if (id && !catGot[g]) { catGot[g] = 1; try { Object.assign(catThumbs, (await (await fetch("/_blob/" + id)).json()).thumbs || {}); } catch (e) { catGot[g] = 0; } }
  }
}
const sheetFor = (rows) => (P()?.kind === "barcode" ? catalogueSheet(rows) : globalSheet(rows));
$("#b-export").addEventListener("click", () => {
  const keys = [...new Set([...cols().map((c) => c.key), ...basket.flatMap((i) => Object.keys(i))])];
  offerFile(`${P().name}-basket.csv`, toCsv(basket, keys));
});
$("#b-file").addEventListener("change", async (ev) => {
  const f = ev.target.files[0]; ev.target.value = ""; if (!f) return;
  const items = parseCsv(await f.text());
  const missing = cols().filter((c) => !(items[0] && c.key in items[0])).map((c) => c.key);
  $("#b-import-confirm").innerHTML = `<div class="confirm"><span>${L(`Replace the basket (${basket.length} lines) with ${items.length} lines from ${esc(f.name)}?`, `استبدال السلة (${basket.length} عنصر) بـ ${items.length} عنصر من ${esc(f.name)}؟`)}${missing.length ? ` ${L("Missing columns:", "أعمدة ناقصة:")} <code>${esc(missing.join(", "))}</code>` : ""}</span><button class="danger" type="button" id="imp-yes">${L("Replace", "استبدال")}</button><button type="button" id="imp-no">${L("Cancel", "إلغاء")}</button></div>`;
  $("#imp-no").onclick = () => ($("#b-import-confirm").innerHTML = "");
  $("#imp-yes").onclick = () => {
    items.forEach((it) => { cols().filter((c) => c.type === "bool").forEach((c) => (it[c.key] = !/^(no|false|0|لا)$/i.test(String(it[c.key] ?? "").trim())));
      if (it.qty_total !== undefined && it.qty_total !== "") it.qty_total = +it.qty_total; });
    basket = items; basketDirty = true; bPage = 0; $("#b-import-confirm").innerHTML = "";
    fillGroupSelect(); renderBasket(); renderRunPicks(); toast(L("File imported; press Save basket to keep it", "استُورد الملف؛ اضغط حفظ السلة لتثبيته"));
  };
});

// ------------------------------------------------------------ actors tab
const MODES = ["barcodes", "search_urls", "single"];
let actorsDraft = {};
function renderActors() {
  const p = P(); if (!p) return; actorsDraft = JSON.parse(JSON.stringify(p.actors || {}));
  drawActors();
}
function drawActors() {
  $("#a-list").innerHTML = Object.entries(actorsDraft).map(([k, a]) => `<div class="actor" data-key="${esc(k)}">
    <div class="row"><b>${esc(a.label || k)}</b><span class="muted mono">${esc(k)}</span><label class="row" style="gap:6px"><input type="checkbox" data-f="enabled" ${a.enabled ? "checked" : ""}> ${L("Enabled", "مفعّل")}</label><span class="spacer"></span><button class="danger" type="button" data-rm>${L("Delete", "حذف")}</button></div>
    <div class="grid">
      <label class="f"><span>${L("Name", "الاسم")}</span><input data-f="label" value="${esc(a.label || "")}"></label>
      <label class="f"><span>Actor</span><input data-f="actor" class="mono" dir="ltr" value="${esc(a.actor || "")}"></label>
      <label class="f"><span>${L("Mode", "النمط")}</span><select data-f="mode">${MODES.map((m) => `<option ${m === a.mode ? "selected" : ""}>${m}</option>`).join("")}</select></label>
      <label class="f"><span>${L("Parser", "المحلل")}</span><select data-f="parser">${Object.keys(PARSERS).map((m) => `<option ${m === a.parser ? "selected" : ""}>${m}</option>`).join("")}</select></label>
      <label class="f"><span>${L("Codes per run", "أكواد لكل تشغيل")}</span><input data-f="batch_size" type="number" min="1" value="${esc(a.batch_size ?? 10)}"></label>
      <label class="f"><span>${L("Parallel runs", "تشغيلات متوازية")}</span><input data-f="parallel_runs" type="number" min="1" max="10" value="${esc(a.parallel_runs ?? 1)}"></label>
    </div>
    <label class="f"><span>${L("Search URL (mode search_urls, contains {barcode})", "رابط البحث (للنمط search_urls، فيه {barcode})")}</span><input data-f="url_template" class="mono" dir="ltr" value="${esc(a.url_template || "")}"></label>
    <label class="f"><span>${L("Dataset fields from Apify (optional, comma separated)", "حقول البيانات المطلوبة من Apify (اختياري، مفصولة بفاصلة)")}</span><input data-f="dataset_fields" class="mono" dir="ltr" value="${esc(a.dataset_fields || "")}"></label>
    <label class="f"><span>${L("Input (JSON)", "الإدخال (JSON)")}</span><textarea data-f="input" class="code" rows="8" spellcheck="false">${esc(JSON.stringify(a.input ?? {}, null, 2))}</textarea></label>
    <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));">
      <label class="f"><span>${L("Run options (JSON: memory, timeout…)", "خيارات التشغيل (JSON: memory, timeout…)")}</span><textarea data-f="call_options" class="code" rows="3" spellcheck="false">${esc(JSON.stringify(a.call_options ?? {}, null, 2))}</textarea></label>
      <label class="f"><span>${L("generic parser fields (JSON: column → data field)", "حقول المحلل generic (JSON: اسم العمود ← حقل البيانات)")}</span><textarea data-f="fields" class="code" rows="3" spellcheck="false">${esc(JSON.stringify(a.fields ?? {}, null, 2))}</textarea></label>
    </div>
    <label class="f"><span>${L("Notes", "ملاحظات")}</span><input data-f="notes" value="${esc(a.notes || "")}"></label>
    <div data-confirm></div>
  </div>`).join("") || `<div class="empty">${L("No Actor in this project.", "لا يوجد Actor في هذا المشروع.")}</div>`;
  $$("#a-list [data-rm]").forEach((b) => b.addEventListener("click", () => {
    const box = b.closest(".actor"), k = box.dataset.key;
    $("[data-confirm]", box).innerHTML = `<div class="confirm"><span>${L(`Delete ${esc(k)}? Applied on save.`, `حذف ${esc(k)}؟ يُطبّق عند الحفظ.`)}</span><button class="danger" type="button" data-yes>${L("Delete", "حذف")}</button><button type="button" data-no>${L("Cancel", "إلغاء")}</button></div>`;
    $("[data-no]", box).onclick = () => ($("[data-confirm]", box).innerHTML = "");
    $("[data-yes]", box).onclick = () => { try { collectActors(); } catch (e) {} delete actorsDraft[k]; drawActors(); };
  }));
}
function collectActors() {
  const out = {};
  for (const box of $$("#a-list .actor")) {
    const k = box.dataset.key, a = { ...actorsDraft[k] };
    for (const el of $$("[data-f]", box)) {
      const f = el.dataset.f;
      if (f === "enabled") a.enabled = el.checked;
      else if (["input", "call_options", "fields"].includes(f)) { try { a[f] = JSON.parse(el.value || "{}"); } catch (e) { throw new Error(L(`${k}: ${f} is not valid JSON (${e.message})`, `${k}: ${f} ليس JSON صحيحاً (${e.message})`)); } }
      else if (f === "batch_size" || f === "parallel_runs") a[f] = Math.max(1, +el.value || 1);
      else a[f] = el.value.trim();
    }
    if (!/^[\w.-]+[/~][\w.-]+$/.test(a.actor)) throw new Error(L(`${k}: write the Actor as username/actor-name`, `${k}: اكتب الـ Actor بصيغة username/actor-name`));
    if (a.mode === "search_urls" && !String(a.url_template).includes("{barcode}")) throw new Error(L(`${k}: the search URL must contain {barcode}`, `${k}: رابط البحث يجب أن يحتوي {barcode}`));
    out[k] = a;
  }
  actorsDraft = out; return out;
}
$("#a-add").addEventListener("click", () => {
  try { collectActors(); } catch (e) { return toast(e.message, true); }
  let k = "actor" + (Object.keys(actorsDraft).length + 1); while (actorsDraft[k]) k += "x";
  actorsDraft[k] = { label: L("New Actor", "Actor جديد"), enabled: false, actor: "username/actor-name", mode: P().kind === "barcode" ? "barcodes" : "single", batch_size: 10, parallel_runs: 1, input: P().kind === "barcode" ? { query: "{barcodes_json}" } : {}, parser: "generic", fields: P().kind === "barcode" ? { code: "searchQuery", title: "title", price: "price", regular_price: "regularPrice", url: "url" } : {}, dataset_fields: "", call_options: {}, notes: "" };
  drawActors();
});
$("#a-save").addEventListener("click", async () => {
  try { await saveProject({ actors: collectActors() }); renderActors(); renderRunPicks(); toast(L("Actors saved", "حُفظت الـ Actors")); }
  catch (e) { toast(e.code ? dbErr(e) : e.message, true); }
});

// ------------------------------------------------------------ results tab
let runs = [], shownRun = null, shownRows = [];
async function loadRuns() {
  try {
    const snap = await db.collection(`projects/${current}/runs`).orderBy("startedAt", "desc").limit(50).get();
    runs = snap.docs.map((d) => ({ id: d.id, ...plain(d) }));
  } catch (e) { runs = []; }
  $("#r-list").innerHTML = runs.length ? `<div class="tw"><table><thead><tr><th>${L("Date", "التاريخ")}</th><th>${L("Status", "الحالة")}</th><th>${L("Rows", "صفوف")}</th><th>${L("Accepted", "مقبول")}</th><th></th></tr></thead><tbody>${runs.map((r) => {
    const st = r.status === "done" ? [L("Done", "انتهى"), "ok"] : r.status === "stopped" ? [L("Stopped", "أُوقف"), "warn"] : [L("Error", "خطأ"), "bad"];
    return `<tr><td class="num">${esc((r.startedAt || "").replace("T", " ").slice(0, 16))}</td><td><span class="chip ${st[1]}">${st[0]}</span></td><td class="num">${r.count ?? ""}</td><td class="num">${r.accepted ?? ""}</td><td><button class="ghost" type="button" data-run="${esc(r.id)}">${L("View", "عرض")}</button></td></tr>`;
  }).join("")}</tbody></table></div>` : `<div class="empty">${L("No runs yet.", "لا توجد تشغيلات بعد.")}</div>`;
  $$("#r-list [data-run]").forEach((b) => b.addEventListener("click", () => showRun(b.dataset.run)));
}
async function showRun(id) {
  shownRun = runs.find((r) => r.id === id);
  $("#r-view").hidden = false; $("#r-more").textContent = L("Reading the rows…", "تُحمَّل الصفوف…");
  try { shownRows = annotateRows(current, shownRun, (await rowDocs(current, shownRun)).flatMap((d) => plain(d).rows || []).map((x) => ({ ...x, run_date: x.run_date || dubaiDay(shownRun.startedAt) }))); await loadThumbs(current, shownRun); }
  catch (e) { shownRows = []; $("#r-more").textContent = ""; toast(L("Could not read the run rows: ", "تعذّر تحميل صفوف التشغيل: ") + dbErr(e), true); return; }
  $("#r-view").hidden = false; $("#r-del-confirm").innerHTML = "";
  $("#r-title").textContent = L("Run ", "تشغيل ") + fmtWhen(shownRun.startedAt);
  // filters: outlet, source, status, group (values seen in this run)
  const opts = (k, lbl) => [...new Set(shownRows.map((r) => r[k]).filter(Boolean))].sort().map((v) => `<option value="${esc(k + ":" + v)}">${esc(lbl)}: ${esc(v)}</option>`).join("");
  $("#r-filter").innerHTML = `<option value="">${esc(L("All outlets, sources, statuses and groups", "كل المنافذ والمصادر والحالات والمجموعات"))}</option>` + opts("retailer", L("Outlet", "المنفذ")) + opts("source", L("Source", "المصدر")) + opts("status", L("Status", "الحالة")) + opts("group_name", L("Group", "المجموعة")) + opts("category", L("Category", "الفئة"));
  $("#r-stats").innerHTML = Object.values(shownRun.summary || {}).map((s) => `<div class="stat"><span class="muted">${esc(s.label)}</span><b>${s.accepted} / ${s.lines}</b><span class="muted">${L("found", "موجود")}</span></div>`).join("");
  drawRun(); $("#r-view").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
}
function runColumns() {
  const first = ["actor", "status"], seen = new Set(first);
  shownRows.forEach((r) => Object.keys(r).forEach((k) => seen.add(k)));
  return [...seen].filter((k) => k !== "accepted");
}
function drawRun() {
  // the same columns as the Excel download (catalogue layout), without the Select and Photo URL helpers
  const q = $("#r-search").value.trim().toLowerCase();
  const fv = $("#r-filter").value, fk = fv.slice(0, fv.indexOf(":")), fx = fv.slice(fv.indexOf(":") + 1);
  const sheet = sheetFor(shownRows.filter((x) => !fv || String(x[fk] ?? "") === fx));
  const keep = sheet.headers.map((h, i) => i).filter((i) => !["Select", "Photo URL"].includes(sheet.headers[i]));
  const rows = sheet.rows.filter((r) => !q || r.join(" ").toLowerCase().includes(q));
  const URLS = new Set(["Product URL"]), PHOTO = sheet.photoCol ? sheet.photoCol - 1 : -1;
  $("#r-table thead").innerHTML = `<tr>${keep.map((i) => `<th>${esc(sheet.headers[i])}</th>`).join("")}</tr>`;
  $("#r-table tbody").innerHTML = rows.slice(0, 400).map((r) => `<tr>${keep.map((i) => {
    const v = r[i], h = sheet.headers[i];
    if (i === PHOTO) return `<td>${v ? `<img class="thumb" src="${esc(photoSrc(v))}" alt="" loading="lazy" onerror="this.remove()">` : ""}</td>`;
    if (URLS.has(h)) return v ? `<td><a href="${esc(v)}" target="_blank" rel="noopener">${L("Open", "فتح")}</a></td>` : "<td></td>";
    if (sheet.priceCols.includes(i + 1) && typeof v === "number") return `<td class="num"><b>${v.toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</b></td>`;
    return `<td>${esc(v ?? "")}</td>`;
  }).join("")}</tr>`).join("") || `<tr><td class="empty" colspan="${keep.length}">${L("No prices.", "لا أسعار.")}</td></tr>`;
  $("#r-more").textContent = rows.length > 400 ? L(`First 400 of ${rows.length} shown; download Excel for all.`, `يظهر أول 400 من ${rows.length}؛ نزّل Excel لرؤية الكل.`) : L(`${rows.length} prices`, `${rows.length} سعر`);
}
$("#r-search").addEventListener("input", drawRun);
$("#r-filter").addEventListener("change", drawRun);
$("#r-export").addEventListener("click", async () => {
  if (!shownRun) return;
  const btn = $("#r-export"); btn.disabled = true; btn.textContent = L("Preparing…", "يُجهَّز…");
  try { await loadThumbs(current, shownRun); await offerXlsx(`${P()?.short || current} ${shownRun.id}.xlsx`, sheetFor(shownRows)); }
  catch (e) { toast(e?.message || String(e), true); }
  finally { btn.disabled = false; btn.textContent = L("Download Excel", "تنزيل Excel"); }
});
$("#r-delete").addEventListener("click", () => {
  $("#r-del-confirm").innerHTML = `<div class="confirm"><span>${L("Delete this run and its results for good?", "حذف هذا التشغيل ونتائجه نهائياً؟")}</span><button class="danger" type="button" id="rd-yes">${L("Delete", "حذف")}</button><button type="button" id="rd-no">${L("Cancel", "إلغاء")}</button></div>`;
  $("#rd-yes").focus();
  $("#rd-no").onclick = () => ($("#r-del-confirm").innerHTML = "");
  $("#rd-yes").onclick = async () => {
    try {
      const rows = await db.collection(`projects/${current}/runs/${shownRun.id}/rows`).get();
      for (const d of rows.docs) await db.doc(`projects/${current}/runs/${shownRun.id}/rows/${d.id}`).delete();
      await db.doc(`projects/${current}/runs/${shownRun.id}`).delete();
      $("#r-view").hidden = true; await loadRuns(); afterRunsChanged(); toast(L("Run deleted", "حُذف التشغيل"));
    } catch (e) { toast(dbErr(e), true); }
  };
});

// ------------------------------------------------------------ settings tab
function renderSettings() {
  const p = P(); if (!p) return;
  $("#s-name").value = p.name || ""; $("#s-desc").value = p.description || ""; $("#s-kind").value = p.kind || "list";
  $("#s-cols").value = JSON.stringify(p.columns || [], null, 2); $("#s-listkey").value = p.list_key || "";
  $("#s-del-confirm").innerHTML = "";
}
const builtinRefused = () => P()?.builtin && (toast(L("This is a built-in plan; it is not saved", "هذه خطة مبدئية من الصفحة؛ لا تُحفظ في قاعدة البيانات"), true), true);
$("#s-save").addEventListener("click", async () => {
  if (builtinRefused()) return;
  let columns; try { columns = JSON.parse($("#s-cols").value); if (!Array.isArray(columns) || columns.some((c) => !c.key)) throw new Error(L("each column needs a key", "كل عمود يحتاج key")); }
  catch (e) { return toast(L("Basket columns: ", "أعمدة السلة: ") + e.message, true); }
  try {
    await saveProject({ name: $("#s-name").value.trim() || L("Untitled", "بدون اسم"), description: $("#s-desc").value.trim(), kind: $("#s-kind").value, columns, list_key: $("#s-listkey").value.trim() });
    renderBasket(); renderRunPicks(); refreshBand(); toast(L("Settings saved", "حُفظت الإعدادات"));
  } catch (e) { toast(dbErr(e), true); }
});
$("#s-delete").addEventListener("click", () => {
  if (builtinRefused()) return;
  $("#s-del-confirm").innerHTML = `<div class="confirm"><span>${L(`Delete the project “${esc(P().name)}” with its basket? Its saved runs are deleted too.`, `حذف مشروع «${esc(P().name)}» مع سلته؟ التشغيلات المحفوظة تُحذف أيضاً.`)}</span><button class="danger" type="button" id="sd-yes">${L("Delete project", "حذف المشروع")}</button><button type="button" id="sd-no">${L("Cancel", "إلغاء")}</button></div>`;
  $("#sd-no").focus();
  $("#sd-no").onclick = () => ($("#s-del-confirm").innerHTML = "");
  $("#sd-yes").onclick = async () => {
    try {
      const pid = current;
      for (const d of (await db.collection(`projects/${pid}/basket`).get()).docs) await db.doc(`projects/${pid}/basket/${d.id}`).delete();
      for (const r of (await db.collection(`projects/${pid}/runs`).get()).docs) {
        for (const d of (await db.collection(`projects/${pid}/runs/${r.id}/rows`).get()).docs) await db.doc(`projects/${pid}/runs/${r.id}/rows/${d.id}`).delete();
        await db.doc(`projects/${pid}/runs/${r.id}`).delete();
      }
      await db.doc(`projects/${pid}`).delete(); delete projects[pid];
      basketDirty = false; current = null; toast(L("Project deleted", "حُذف المشروع")); go("#home");
    } catch (e) { toast(dbErr(e), true); }
  };
});

// ------------------------------------------------------------ schedules: claude.ai Routines read with get_trigger and changed with update_trigger / fire_trigger
const CCR = "Claude Code Remote";
const TZ_LABEL = { "Asia/Dubai": ["Dubai time", "توقيت دبي"] };
const tzName = (tz) => (TZ_LABEL[tz] ? L(TZ_LABEL[tz][0], TZ_LABEL[tz][1]) : tz);
function parseCron(c) {
  const m = String(c || "").match(/^(?:CRON_TZ=(\S+)\s+)?(\d{1,2})\s+(\d{1,2})\s+(\S+)\s+(\S+)\s+(\S+)$/);
  return m ? { tz: m[1] || "UTC", min: +m[2], hour: +m[3], dom: m[4], mon: m[5], dow: m[6] } : null;
}
const pad = (n) => String(n).padStart(2, "0");
function fmtWhen(iso) { if (!iso) return "—"; try { return new Date(iso).toLocaleString(LANG === "ar" ? "ar-u-nu-latn" : "en-GB", { timeZone: "Asia/Dubai", day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false }); } catch (e) { return iso; } }
function schedFail(e) {
  const fix = { needs_reauth: L("Reconnect Claude Code Remote in claude.ai settings", "أعد ربط Claude Code Remote من إعدادات claude.ai"), server_not_connected: L("The Claude Code Remote connector is not available for this account", "موصل Claude Code Remote غير متاح لهذا الحساب"),
    not_in_manifest: L("This page may not manage schedules; reopen it and allow the connector", "لم يُسمح للصفحة بإدارة الجدولة؛ أعد فتحها واسمح بالموصل") }[e?.code];
  return fix || e?.message || String(e);
}
async function ccr(tool, input) { return (await mcp.callTool(CCR, tool, input, { cache: false })).payload; }
const trigCache = {};          // trigger id -> trigger, for this session ("Sync schedules" reads them again)
async function getTrigger(tid, fresh) {
  if (!fresh && trigCache[tid]) return trigCache[tid];
  const r = await ccr("get_trigger", { trigger_id: tid }); const t = r?.trigger || r?.data || r;
  trigCache[tid] = t; return t;
}
// Dubai wall time of a cron (a cron without CRON_TZ is UTC)
function cronDubai(c) {
  if (!c) return null;
  if (c.tz === "Asia/Dubai") return { h: c.hour, m: c.min };
  if (c.tz === "UTC") return { h: (c.hour + 4) % 24, m: c.min };
  return null;
}
/* The live part of one schedule card: time, enable switch, "Save time", "Run now" (inline confirm). `key` prefixes the ids
   ("sched" for the project's daily routine, as before). Called with no box it re-renders the open Schedules page. */
async function renderSchedule(box, tid, key = "sched", opts = {}) {
  if (!box) { if (typeof schedRefresh === "function") schedRefresh(); return; }
  const chip = opts.chip;
  if (!mcp) { if (chip) { chip.textContent = L("Not available", "غير متاح"); chip.className = "chip grey"; } box.innerHTML = `<p class="notice info" style="margin:0">${esc(L("Schedules need this page opened in claude.ai.", "إدارة الجدولة تحتاج فتح الصفحة داخل claude.ai."))}</p>`; return; }
  box.innerHTML = `<div class="loading">${esc(L("Reading the schedule…", "يُقرأ موعد التشغيل…"))}</div>`;
  let t;
  try { t = await getTrigger(tid, opts.fresh); }
  catch (e) { if (chip) { chip.textContent = L("Could not read", "تعذّرت القراءة"); chip.className = "chip bad"; }
    box.innerHTML = `<div class="errbox" role="alert"><span class="bang" aria-hidden="true">!</span><span class="msg">${esc(schedFail(e))}</span><button type="button" data-retry>${esc(L("Retry", "أعد المحاولة"))}</button></div>`;
    $("[data-retry]", box).onclick = () => renderSchedule(box, tid, key, { ...opts, fresh: true }); return; }
  if (!box.isConnected) return;
  const c = parseCron(t.cron_expression) || { tz: "Asia/Dubai", hour: 8, min: 0, dom: "*", mon: "*", dow: "*" };
  const dub = cronDubai(c) || { h: c.hour, m: c.min };
  const lr = t.last_run;
  const lrTxt = lr ? `${fmtWhen(lr.fired_at)} · ${/SUCCEEDED/.test(lr.status) ? L("succeeded", "نجح") : /FAILED/.test(lr.status) ? L("failed", "فشل") + (lr.failure_reason ? ` (${String(lr.failure_reason).replace("ROUTINE_RUN_FAILURE_REASON_", "").toLowerCase()})` : "") : String(lr.status || "").replace("ROUTINE_RUN_STATUS_", "").toLowerCase()}` : L("not run yet", "لم يعمل بعد");
  if (chip) { chip.textContent = t.enabled ? L("Enabled", "مفعّل") : L("Paused", "متوقف"); chip.className = "chip " + (t.enabled ? "ok" : "warn"); }
  box.innerHTML = `
    <dl class="kv">
      <dt>${esc(L("Time", "الوقت"))}</dt><dd><b class="ltr">${pad(dub.h)}:${pad(dub.m)}</b> ${esc(L("Dubai", "دبي"))}</dd>
      <dt>${esc(L("Next run", "التشغيل القادم"))}</dt><dd>${esc(t.enabled ? fmtWhen(t.next_run_at) : L("paused", "متوقف"))}</dd>
      <dt>${esc(L("Last trigger", "آخر تشغيل للمهمة"))}</dt><dd>${esc(lrTxt)}</dd>
      ${opts.lastRunHtml ? `<dt>${esc(L("Last run", "آخر تشغيل"))}</dt><dd>${opts.lastRunHtml}</dd>` : ""}
    </dl>
    <div class="row" style="align-items:end">
      <label class="f" style="width:170px"><span>${esc(L("Time", "الوقت"))} (${esc(tzName("Asia/Dubai"))})</span><input type="time" id="${key}-time" value="${pad(dub.h)}:${pad(dub.m)}"></label>
      <label class="row" style="gap:8px;padding-bottom:10px"><input type="checkbox" id="${key}-on" ${t.enabled ? "checked" : ""}> ${esc(L("Enabled", "مفعّل"))}</label>
      <button class="primary" type="button" id="${key}-save">${esc(L("Save time", "حفظ الموعد"))}</button>
      ${opts.noRun ? "" : `<button type="button" id="${key}-fire">${ico("play", "fill")}${esc(L("Run now", "شغّل الآن"))}</button>`}
    </div>
    <div id="${key}-confirm"></div>`;
  $(`#${key}-save`).onclick = async () => {
    const [h, m] = ($(`#${key}-time`).value || "").split(":").map(Number);
    if (isNaN(h) || isNaN(m)) return toast(L("Choose a valid time", "اختر وقتاً صحيحاً"), true);
    const H = c.tz === "UTC" ? (h + 20) % 24 : h;             // the routine keeps its own zone; UTC crons get the Dubai time minus 4 h
    const cron = `${c.tz === "UTC" ? "" : `CRON_TZ=${c.tz} `}${m} ${H} ${c.dom || "*"} ${c.mon || "*"} ${c.dow && c.dow !== "1-5" ? c.dow : "*"}`;
    try { await ccr("update_trigger", { trigger_id: tid, cron_expression: cron, enabled: $(`#${key}-on`).checked }); delete trigCache[tid]; toast(L(`Saved: ${pad(h)}:${pad(m)} Dubai time`, `حُفظ: ${pad(h)}:${pad(m)} بتوقيت دبي`)); renderSchedule(box, tid, key, { ...opts, fresh: true }); }
    catch (e) { toast(schedFail(e), true); }
  };
  const fire = $(`#${key}-fire`);
  if (fire) fire.onclick = () => askInline($(`#${key}-confirm`), esc(L("Run this routine now? It runs in the background; its result appears in Price Logs when it ends.", "تشغيل المهمة الآن؟ تعمل في الخلفية وتظهر نتيجتها في سجل الأسعار عند انتهائها.")), L("Run now", "شغّل الآن"), async () => {
    try { await ccr("fire_trigger", { trigger_id: tid }); toast(L("Started in the background", "بدأ التشغيل في الخلفية")); delete trigCache[tid]; setTimeout(() => box.isConnected && renderSchedule(box, tid, key, { ...opts, fresh: true }), 4000); }
    catch (e) { toast(schedFail(e), true); }
  }, false, fire);
}

// ------------------------------------------------------------ quick run through the project's routine (Scrapling, server side)
function renderQuick() {
  const p = P(); const on = p?.runner === "routine" && p?.schedule?.trigger_id;
  $("#quick").hidden = !on;
  $("#apify-title").textContent = L("Legacy: Apify run (not part of the daily CPI method)", "قديم: تشغيل عبر Apify (ليس جزءاً من طريقة CPI اليومية)");
}
$("#btn-quick").addEventListener("click", () => {
  if (!mcp) return toast(L("Running needs the page opened in claude.ai", "التشغيل يحتاج فتح الصفحة داخل claude.ai"), true);
  $("#quick-confirm").innerHTML = `<div class="confirm"><span>${L(`Start a full scrape of “${esc(P().short || P().name)}” now?`, `بدء سحب كامل لمشروع «${esc(P().short || P().name)}» الآن؟`)}</span><button class="primary" type="button" id="q-yes">${L("Start", "ابدأ")}</button><button type="button" id="q-no">${L("Cancel", "إلغاء")}</button></div>`;
  $("#q-yes").focus();
  $("#q-no").onclick = () => ($("#quick-confirm").innerHTML = "");
  $("#q-yes").onclick = async () => {
    $("#quick-confirm").innerHTML = "";
    try { await ccr("fire_trigger", { trigger_id: P().schedule.trigger_id }); toast(L("The scrape started; the result appears in Price Logs when it ends", "بدأ السحب؛ النتيجة تظهر في سجل الأسعار عند انتهائه")); setTimeout(renderSchedule, 4000); }
    catch (e) { toast(schedFail(e), true); }
  };
});

// ------------------------------------------------------------ one long table of every saved run (for Dataiku); the same columns as before, new ones at the end
const LEAD = ["run_date", "run_id", "retailer", "actor", "item_code", "barcode", "name", "brand", "basket_qty", "category", "commodity", "unit",
  "title", "price", "regular_price", "currency", "change", "pct", "weekly", "monthly", "ytd", "yoy", "price_date", "status", "accepted", "url"];
async function exportAllRuns(only, filename, btn) {
  const old = btn ? btn.innerHTML : ""; if (btn) { btn.disabled = true; btn.textContent = L("Collecting…", "يُجمع…"); }
  try {
    const all = only || (await db.collection(`projects/${current}/runs`).get()).docs.map((d) => ({ id: d.id, ...plain(d) }));
    const rows = [];
    let k = 0;
    for (const r of all.sort((a, b) => String(a.startedAt).localeCompare(String(b.startedAt)))) {
      if (btn) { k++; btn.textContent = L(`Reading run ${k} of ${all.length}…`, `يُقرأ التشغيل ${k} من ${all.length}…`); }
      const chunks = await rowDocs(current, r), list = [];
      for (const c of chunks) for (const x of plain(c).rows || []) list.push({ ...x, run_id: r.id, run_date: x.run_date || dubaiDay(r.startedAt) });
      rows.push(...annotateRows(current, r, list));
    }
    if (!rows.length) return toast(L("No saved runs yet", "لا توجد تشغيلات محفوظة بعد"), true);
    for (const r of all) await loadThumbs(current, r);
    await offerXlsx(filename || `${P()?.name || P()?.short || current} - all prices.xlsx`, sheetFor(rows));
  } catch (e) { toast(dbErr(e), true); }
  finally { if (btn) { btn.disabled = false; btn.innerHTML = old; } }
}
$("#r-export-all").addEventListener("click", () => exportAllRuns(null, null, $("#r-export-all")));

// ------------------------------------------------------------ chart library
const CH_LIB = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js";
let chLib = null;
const loadChartLib = () => window.Chart ? Promise.resolve(window.Chart) : (chLib ??= new Promise((ok, fail) => {
  const el = document.createElement("script"); el.src = CH_LIB; el.onload = () => ok(window.Chart);
  el.onerror = () => { chLib = null; fail(new Error(L("Could not load the chart library", "تعذّر تحميل مكتبة الرسوم"))); }; document.head.appendChild(el); }));
// the two non-food groups come from the daily catalogue history (our category -> the CPI group name)
const CH_COLORS = ["#223f62", "#e07a1f", "#1b998b", "#c0392b", "#6c5ce7", "#2e86de", "#8d6e63", "#d4a017", "#e84393", "#00a8a8", "#7f8c8d", "#5b8c2a", "#a3318c", "#cc5500", "#1f6f9f", "#b8860b", "#3d5a80", "#9c2f2f", "#2a9d8f", "#6d597a"];
// ------------------------------------------------------------ COICOP 2018 price tree (division > group > class > subclass > item type > products)
// Codes and English titles: UN COICOP 2018. Arabic titles: the Dubai Statistics Center CPI basket names where it has the
// class (4-digit codes such as 0112 = 01.1.2), otherwise a translation of the COICOP title. Item types (the last level, e.g.
// red meat / poultry) are the elementary aggregates under a COICOP subclass, coded "<subclass>-<letter>".
const COICOP = [
  ["01", "الأغذية والمشروبات غير الكحولية", "Food and non-alcoholic beverages"],
  ["01.1", "الأغذية", "Food"],
  ["01.1.1", "الحبوب ومنتجاتها", "Cereals and cereal products"],
  ["01.1.1.1", "الحبوب", "Cereals"], ["01.1.1.1-a", "الأرز", "Rice"],
  ["01.1.1.2", "دقيق الحبوب", "Flour of cereals"], ["01.1.1.2-a", "الدقيق والسميد", "Flour and semolina"],
  ["01.1.1.3", "الخبز والمخبوزات", "Bread and bakery products"], ["01.1.1.3-a", "الخبز والمخبوزات", "Bread and bakery products"],
  ["01.1.1.4", "حبوب الإفطار", "Breakfast cereals"], ["01.1.1.4-a", "حبوب الإفطار والشوفان", "Breakfast cereals and oats"],
  ["01.1.1.5", "المعكرونة والشعيرية والكسكس", "Macaroni, noodles, couscous and similar pasta products"],
  ["01.1.1.5-a", "المعكرونة", "Pasta"], ["01.1.1.5-b", "الشعيرية والنودلز", "Noodles and vermicelli"],
  ["01.1.2", "اللحوم", "Live animals, meat and other parts of slaughtered land animals"],
  ["01.1.2.2", "لحوم طازجة أو مبرّدة أو مجمّدة", "Meat, fresh, chilled or frozen"],
  ["01.1.2.2-a", "اللحوم الحمراء (بقري، ضأن، ماعز)", "Red meat (beef, lamb, goat)"], ["01.1.2.2-b", "الدواجن", "Poultry"],
  ["01.1.2.4", "الأحشاء والأجزاء الأخرى من الذبائح", "Offal, blood and other parts of slaughtered animals"], ["01.1.2.4-a", "الكبدة والأحشاء", "Liver and offal"],
  ["01.1.2.5", "مستحضرات اللحوم", "Meat, offal and other parts' preparations"], ["01.1.2.5-a", "لحوم مصنّعة ومحضّرة (نقانق، برجر، ناجتس)", "Processed meat (sausages, burgers, nuggets)"],
  ["01.1.3", "الأسماك والأغذية البحرية", "Fish and other seafood"],
  ["01.1.3.1", "أسماك طازجة أو مبرّدة أو مجمّدة", "Fish, live, fresh, chilled or frozen"], ["01.1.3.1-a", "الأسماك الطازجة والمجمّدة", "Fresh and frozen fish"],
  ["01.1.3.2", "أسماك مجففة أو مملّحة أو مدخّنة", "Fish, dried, salted, in brine or smoked"], ["01.1.3.2-a", "أسماك مدخّنة ومجففة", "Smoked and dried fish"],
  ["01.1.3.3", "مستحضرات الأسماك", "Fish preparations"], ["01.1.3.3-a", "التونة والسردين والأسماك المحضّرة", "Tuna, sardines and prepared fish"],
  ["01.1.3.4", "أغذية بحرية أخرى طازجة أو مجمّدة", "Other seafood, live, fresh, chilled or frozen"], ["01.1.3.4-a", "الروبيان والأغذية البحرية", "Shrimp and seafood"],
  ["01.1.4", "اللبن والجبن والبيض", "Milk, other dairy products and eggs"],
  ["01.1.4.1", "الحليب الخام وكامل الدسم", "Raw and whole milk"], ["01.1.4.1-a", "الحليب الطازج", "Fresh milk"],
  ["01.1.4.2", "الحليب منزوع الدسم", "Skimmed milk"], ["01.1.4.2-a", "حليب قليل أو خالي الدسم", "Low-fat and skimmed milk"],
  ["01.1.4.3", "أنواع أخرى من الحليب والقشطة", "Other milk and cream"], ["01.1.4.3-a", "الحليب المجفف والمكثف والقشطة", "Powdered and condensed milk, cream"],
  ["01.1.4.4", "الحليب النباتي", "Non-animal milk"], ["01.1.4.4-a", "الحليب النباتي", "Plant-based milk"],
  ["01.1.4.5", "الأجبان", "Cheese"], ["01.1.4.5-a", "الأجبان", "Cheese"],
  ["01.1.4.6", "الزبادي والمنتجات المشابهة", "Yoghurt and similar products"], ["01.1.4.6-a", "الزبادي واللبن", "Yoghurt and laban"],
  ["01.1.4.7", "حلويات ومشروبات الحليب", "Milk-based dessert and beverages"], ["01.1.4.7-a", "الحليب المنكّه", "Flavoured milk"], ["01.1.4.7-b", "حلويات الألبان", "Dairy desserts"],
  ["01.1.4.8", "البيض", "Eggs"], ["01.1.4.8-a", "البيض", "Eggs"],
  ["01.1.5", "الزيوت والدهون", "Oils and fats"],
  ["01.1.5.1", "الزيوت النباتية", "Vegetable oils"], ["01.1.5.1-a", "زيوت الطبخ والزيتون", "Cooking and olive oils"],
  ["01.1.5.2", "الزبدة والدهون المشتقة من الحليب", "Butter and other fats derived from milk"], ["01.1.5.2-a", "الزبدة والسمن", "Butter and ghee"],
  ["01.1.5.3", "المارجرين والمستحضرات المشابهة", "Margarine and similar preparations"], ["01.1.5.3-a", "المارجرين", "Margarine"],
  ["01.1.6", "الفواكه والمكسرات", "Fruits and nuts"],
  ["01.1.6.1", "التمور والتين والفواكه الاستوائية", "Dates, figs and tropical fruits, fresh"], ["01.1.6.1-a", "التمور", "Dates"], ["01.1.6.1-b", "الموز والمانجو والفواكه الاستوائية", "Bananas, mangoes and tropical fruit"],
  ["01.1.6.2", "الحمضيات", "Citrus fruits, fresh"], ["01.1.6.2-a", "البرتقال والليمون والحمضيات", "Oranges, lemons and citrus"],
  ["01.1.6.3", "الفواكه ذات النواة والتفاحيات", "Stone fruits and pome fruits, fresh"], ["01.1.6.3-a", "التفاح والكمثرى والخوخ", "Apples, pears and stone fruit"],
  ["01.1.6.4", "العنب والتوت", "Berries, fresh"], ["01.1.6.4-a", "العنب والفراولة والتوت", "Grapes, strawberries and berries"],
  ["01.1.6.5", "فواكه طازجة أخرى", "Other fruits, fresh"], ["01.1.6.5-a", "البطيخ والرمان وفواكه أخرى", "Melons, pomegranates and other fruit"],
  ["01.1.6.6", "الفواكه المجمّدة", "Frozen fruit"], ["01.1.6.6-a", "الفواكه المجمّدة", "Frozen fruit"],
  ["01.1.6.7", "الفواكه المجففة", "Fruit, dried and dehydrated"], ["01.1.6.7-a", "الفواكه المجففة", "Dried fruit"],
  ["01.1.6.8", "المكسرات", "Nuts, in shell or shelled"], ["01.1.6.8-a", "المكسرات", "Nuts"],
  ["01.1.7", "البقول والخضروات", "Vegetables, tubers, plantains, cooking bananas and pulses"],
  ["01.1.7.1", "الخضروات الورقية والساقية", "Leafy or stem vegetables, fresh or chilled"], ["01.1.7.1-a", "الخس والسبانخ والخضار الورقية", "Lettuce, spinach and leafy vegetables"],
  ["01.1.7.2", "الخضروات الثمرية", "Fruit-bearing vegetables, fresh or chilled"], ["01.1.7.2-a", "الطماطم والخيار والفلفل", "Tomatoes, cucumbers and peppers"],
  ["01.1.7.3", "البقول الخضراء", "Green leguminous vegetables, fresh or chilled"], ["01.1.7.3-a", "الفاصوليا والبازلاء الخضراء", "Green beans and peas"],
  ["01.1.7.4", "خضروات أخرى", "Other vegetables, fresh or chilled"], ["01.1.7.4-a", "البصل والثوم والجزر والفطر", "Onions, garlic, carrots and mushrooms"],
  ["01.1.7.5", "الدرنيات", "Tubers, plantains and cooking bananas"], ["01.1.7.5-a", "البطاطس والدرنيات", "Potatoes and tubers"],
  ["01.1.7.6", "البقوليات الجافة", "Pulses"], ["01.1.7.6-a", "العدس والحمص والفول", "Lentils, chickpeas and beans"],
  ["01.1.7.8", "الخضروات المجمّدة", "Vegetables, tubers, plantains and cooking bananas, frozen"], ["01.1.7.8-a", "الخضار والبطاطس المجمّدة", "Frozen vegetables and fries"],
  ["01.1.7.9", "مستحضرات الخضروات والبقول", "Vegetables and pulses ground and other preparations"], ["01.1.7.9-a", "الخضار والبقول المعلّبة", "Canned vegetables and pulses"],
  ["01.1.8", "السكر والمربى والعسل والشوكولاتة والحلوى", "Sugar, confectionery and desserts"],
  ["01.1.8.1", "سكر القصب والبنجر", "Cane and beet sugar"], ["01.1.8.1-a", "السكر", "Sugar"],
  ["01.1.8.2", "بدائل السكر", "Other sugar and sugar substitutes"], ["01.1.8.2-a", "المحليات وبدائل السكر", "Sweeteners"],
  ["01.1.8.3", "المربى والعسل", "Jams, fruit jellies, marmalades, honey"], ["01.1.8.3-a", "العسل", "Honey"], ["01.1.8.3-b", "المربى", "Jam"],
  ["01.1.8.4", "زبدة المكسرات والطحينة", "Nut purée, nut butter and nut pastes"], ["01.1.8.4-a", "زبدة الفول السوداني والطحينة", "Peanut butter and tahini"],
  ["01.1.8.5", "الشوكولاتة والكاكاو", "Chocolate, cocoa, and cocoa-based food products"], ["01.1.8.5-a", "الشوكولاتة والكاكاو", "Chocolate and cocoa"],
  ["01.1.8.6", "المثلجات والآيس كريم", "Ice, ice cream and sorbet"], ["01.1.8.6-a", "الآيس كريم", "Ice cream"],
  ["01.1.8.9", "حلويات أخرى", "Other sugar confectionery and desserts n.e.c."], ["01.1.8.9-a", "الحلويات والجيلي والكاسترد", "Sweets, jelly and custard"],
  ["01.1.9", "منتجات غذائية غير مصنّفة في مكان آخر", "Ready-made food and other food products n.e.c."],
  ["01.1.9.1", "الأطعمة الجاهزة", "Ready-made food"], ["01.1.9.1-a", "الأطعمة الجاهزة والمجمّدة", "Ready and frozen meals"],
  ["01.1.9.3", "الملح والصلصات", "Salt, condiments and sauces"], ["01.1.9.3-a", "الملح", "Salt"], ["01.1.9.3-b", "الصلصات والخل", "Sauces and vinegar"],
  ["01.1.9.4", "البهارات والأعشاب", "Spices, culinary herbs and seeds"], ["01.1.9.4-a", "البهارات", "Spices"],
  ["01.1.9.9", "منتجات غذائية أخرى", "Other food products n.e.c."], ["01.1.9.9-a", "مستلزمات الطبخ والخبز الأخرى", "Other cooking and baking products"],
  ["01.2", "المشروبات غير الكحولية", "Non-alcoholic beverages"],
  ["01.2.1", "العصائر", "Fruit and vegetable juices"], ["01.2.1.0", "العصائر", "Fruit and vegetable juices"], ["01.2.1.0-a", "العصائر", "Juices"],
  ["01.2.2", "البن", "Coffee and coffee substitutes"], ["01.2.2.0", "البن", "Coffee and coffee substitutes"], ["01.2.2.0-a", "البن والقهوة", "Coffee"],
  ["01.2.3", "الشاي", "Tea, maté and other plant products for infusion"], ["01.2.3.0", "الشاي", "Tea, maté and other plant products for infusion"], ["01.2.3.0-a", "الشاي", "Tea"],
  ["01.2.5", "المياه المعدنية", "Water"], ["01.2.5.0", "المياه المعدنية", "Water"], ["01.2.5.0-a", "مياه الشرب", "Drinking water"],
  ["01.2.6", "المشروبات الغازية", "Soft drinks"], ["01.2.6.0", "المشروبات الغازية", "Soft drinks"], ["01.2.6.0-a", "المشروبات الغازية", "Soft drinks"],
  ["01.2.9", "مشروبات أخرى (الطاقة وغيرها)", "Other non-alcoholic beverages"], ["01.2.9.0", "مشروبات أخرى", "Other non-alcoholic beverages"], ["01.2.9.0-a", "مشروبات الطاقة", "Energy drinks"],
  ["03", "الملابس والأحذية", "Clothing and footwear"],
  ["03.1", "الملابس", "Clothing"],
  ["03.1.2", "الملابس الجاهزة", "Garments"],
  ["03.1.2.1", "ملابس الرجال والأولاد", "Garments for men or boys"],
  ["03.1.2.1-a", "القمصان والتيشيرتات", "Shirts and T-shirts"], ["03.1.2.1-b", "الجينز والبناطيل", "Jeans and trousers"], ["03.1.2.1-c", "الجاكيتات والبدلات والتريكو", "Jackets, suits and knitwear"], ["03.1.2.1-d", "الملابس الداخلية والجوارب", "Underwear and socks"], ["03.1.2.1-e", "ملابس أخرى", "Other garments"],
  ["03.1.2.2", "ملابس النساء والبنات", "Garments for women or girls"],
  ["03.1.2.2-a", "البلوزات والقمصان والتيشيرتات", "Tops, shirts and T-shirts"], ["03.1.2.2-b", "الجينز والبناطيل", "Jeans and trousers"], ["03.1.2.2-c", "الفساتين والعبايات", "Dresses and abayas"], ["03.1.2.2-d", "الجاكيتات والتريكو", "Jackets and knitwear"], ["03.1.2.2-e", "الملابس الداخلية والجوارب", "Underwear and socks"], ["03.1.2.2-f", "ملابس أخرى", "Other garments"],
  ["03.1.2.3", "ملابس الرضّع (حتى سنتين)", "Garments for infants (0 to under 2 years)"], ["03.1.2.3-a", "ملابس الرضّع", "Infant clothing"],
  ["03.2", "الأحذية", "Footwear"],
  ["03.2.1", "الأحذية", "Shoes and other footwear"],
  ["03.2.1.1", "أحذية الرجال", "Footwear for men"], ["03.2.1.1-a", "أحذية الرجال", "Men's shoes"],
  ["03.2.1.2", "أحذية النساء", "Footwear for women"], ["03.2.1.2-a", "أحذية النساء", "Women's shoes"],
  ["03.2.1.3", "أحذية الرضّع والأطفال", "Footwear for infants and children"], ["03.2.1.3-a", "أحذية الأطفال", "Children's shoes"],
  ["05", "الأثاث والتجهيزات المنزلية", "Furnishings, household equipment and routine household maintenance"],
  ["05.2", "المنسوجات المنزلية", "Household textiles"], ["05.2.1", "المنسوجات المنزلية", "Household textiles"],
  ["05.2.1.2", "مفارش وأغطية السرير", "Bed linen and bedding"], ["05.2.1.2-a", "مفارش السرير", "Bed sheets"],
  ["05.3", "الأجهزة المنزلية", "Household appliances"],
  ["05.3.1", "الأجهزة المنزلية الكبيرة", "Major household appliances, whether electric or not"],
  ["05.3.1.1", "أجهزة المطبخ الكبيرة", "Major kitchen appliances"], ["05.3.1.1-a", "الثلاجات والمجمّدات", "Refrigerators and freezers"], ["05.3.1.1-b", "غسالات الصحون", "Dishwashers"],
  ["05.3.1.2", "أجهزة الغسيل الكبيرة", "Major laundry appliances"], ["05.3.1.2-a", "غسالات الملابس", "Washing machines"],
  ["05.3.1.3", "المدافئ والمكيفات", "Heaters, air conditioners"], ["05.3.1.3-a", "المكيفات", "Air conditioners"],
  ["05.3.1.4", "أجهزة التنظيف", "Cleaning equipment"], ["05.3.1.4-a", "المكانس الكهربائية", "Vacuum cleaners"],
  ["05.3.2", "الأجهزة المنزلية الصغيرة", "Small household appliances"],
  ["05.3.2.1", "أجهزة الطبخ وتحضير الطعام الصغيرة", "Small appliances for cooking and processing of food"], ["05.3.2.1-a", "الخلاطات وأجهزة المطبخ الصغيرة", "Blenders and small kitchen appliances"],
  ["05.3.2.2", "أجهزة تحضير المشروبات", "Small appliances for preparing beverages"], ["05.3.2.2-a", "الغلايات وآلات القهوة", "Kettles and coffee machines"],
  ["05.3.2.9", "أجهزة منزلية صغيرة أخرى", "Other small household appliances"], ["05.3.2.9-a", "المكاوي والمراوح وأجهزة أخرى", "Irons, fans and other appliances"],
  ["05.4", "الأواني وأدوات المائدة والمطبخ", "Glassware, tableware and household utensils"], ["05.4.0", "الأواني وأدوات المائدة والمطبخ", "Glassware, tableware and household utensils"],
  ["05.4.0.1", "الأواني الزجاجية والخزفية", "Glassware, crystal-ware, ceramic ware and chinaware"], ["05.4.0.1-a", "الأطباق وأواني المائدة", "Plates and tableware"],
  ["05.4.0.3", "أدوات المطبخ", "Kitchen utensils and articles"], ["05.4.0.3-a", "أواني الطبخ", "Cookware"],
  ["05.5", "الأدوات والمعدات للمنزل والحديقة", "Tools and equipment for house and garden"], ["05.5.2", "الأدوات الصغيرة ومستلزمات المنزل", "Non-motorized tools and miscellaneous accessories"],
  ["05.5.2.2", "مستلزمات متنوعة", "Miscellaneous accessories"], ["05.5.2.2-a", "البطاريات والمصابيح", "Batteries and light bulbs"],
  ["05.6", "السلع والخدمات للصيانة المنزلية الاعتيادية", "Goods and services for routine household maintenance"],
  ["05.6.1", "السلع المنزلية غير المعمّرة", "Non-durable household goods"],
  ["05.6.1.1", "منتجات التنظيف والصيانة المنزلية", "Household cleaning and maintenance products"], ["05.6.1.1-a", "منظفات الغسيل", "Laundry detergents"], ["05.6.1.1-b", "منظفات الصحون", "Dishwashing products"], ["05.6.1.1-c", "منظفات المنزل والمطهرات", "Household cleaners and disinfectants"],
  ["05.6.1.9", "سلع منزلية غير معمّرة أخرى", "Other non-durable household goods"], ["05.6.1.9-a", "المعطّرات ومبيدات الحشرات", "Air fresheners and insecticides"], ["05.6.1.9-b", "مناديل المطبخ الورقية", "Kitchen paper towels"],
  ["06", "الصحة", "Health"],
  ["06.1", "الأدوية والمنتجات الصحية", "Medicines and health products"],
  ["06.1.1", "الأدوية", "Medicines"], ["06.1.1.1", "الأدوية واللقاحات والمستحضرات الصيدلانية", "Medicines, vaccines and other pharmaceutical preparations"], ["06.1.1.1-a", "المسكّنات (باراسيتامول)", "Painkillers (paracetamol)"], ["06.1.1.1-b", "الفيتامينات والمكمّلات", "Vitamins and supplements"],
  ["06.1.2", "المنتجات الطبية", "Medical products"], ["06.1.2.1", "منتجات التشخيص الطبي", "Medical diagnostic products"], ["06.1.2.1-a", "موازين الحرارة", "Thermometers"],
  ["06.1.2.3", "أدوات العلاج للاستخدام الشخصي", "Treatment devices for personal use"], ["06.1.2.3-a", "مستلزمات الإسعافات الأولية", "First aid supplies"],
  ["07", "النقل", "Transport"],
  ["07.1", "شراء المركبات", "Purchase of vehicles"], ["07.1.3", "الدراجات الهوائية", "Bicycles"], ["07.1.3.0", "الدراجات الهوائية", "Bicycles"], ["07.1.3.0-a", "الدراجات الهوائية", "Bicycles"],
  ["07.2", "تشغيل معدات النقل الشخصية", "Operation of personal transport equipment"],
  ["07.2.1", "قطع غيار وإكسسوارات المركبات", "Parts and accessories for personal transport equipment"],
  ["07.2.1.2", "قطع غيار المركبات", "Parts for personal transport equipment"], ["07.2.1.2-a", "بطاريات السيارات", "Car batteries"],
  ["07.2.1.3", "إكسسوارات المركبات", "Accessories for personal transport equipment"], ["07.2.1.3-a", "إكسسوارات السيارات", "Car accessories"],
  ["07.2.2", "الوقود ومواد التشحيم", "Fuels and lubricants for personal transport equipment"], ["07.2.2.4", "مواد التشحيم", "Lubricants"], ["07.2.2.4-a", "زيوت المحركات", "Engine oil"],
  ["08", "الاتصالات والمعلومات", "Information and communication"],
  ["08.1", "أجهزة المعلومات والاتصالات", "Information and communication equipment"],
  ["08.1.2", "الهواتف المحمولة", "Mobile telephone equipment"], ["08.1.2.0", "الهواتف المحمولة", "Mobile telephone equipment"], ["08.1.2.0-a", "الهواتف المحمولة", "Mobile phones"],
  ["08.1.3", "أجهزة الحاسوب واللوحية", "Information processing equipment"],
  ["08.1.3.1", "الحواسيب المحمولة واللوحية", "Computers, laptops and tablets"], ["08.1.3.1-a", "الحواسيب المحمولة", "Laptops"], ["08.1.3.1-b", "الأجهزة اللوحية", "Tablets"],
  ["08.1.3.2", "الملحقات الطرفية ومستهلكاتها", "Peripheral equipment and its consumable components"], ["08.1.3.2-a", "الشاشات والطابعات والتخزين والشبكات", "Monitors, printers, storage and networking"],
  ["08.1.4", "أجهزة التلفاز والصوت", "Equipment for the reception, recording and reproduction of sound and vision"], ["08.1.4.0", "أجهزة التلفاز والصوت", "Equipment for the reception, recording and reproduction of sound and vision"],
  ["08.1.4.0-a", "أجهزة التلفاز", "Televisions"], ["08.1.4.0-b", "السماعات وأجهزة الصوت", "Headphones, earphones and speakers"],
  ["08.1.9", "أجهزة اتصالات وصوت أخرى", "Other information and communication equipment and accessories"],
  ["08.1.9.1", "أجهزة اتصالات أخرى", "Other information and communication equipment"], ["08.1.9.1-a", "الساعات الذكية", "Smartwatches"],
  ["08.1.9.2", "ملحقات أجهزة الاتصالات", "Other information and communication accessories"], ["08.1.9.2-a", "الشواحن والكوابل والأغطية", "Chargers, cables, power banks and cases"],
  ["09", "الترفيه والرياضة والثقافة", "Recreation, sport and culture"],
  ["09.1", "السلع المعمّرة للترفيه", "Recreational durables"], ["09.1.1", "معدات التصوير والأجهزة البصرية", "Photographic and cinematographic equipment and optical instruments"],
  ["09.1.1.1", "الكاميرات", "Cameras"], ["09.1.1.1-a", "الكاميرات", "Cameras"],
  ["09.2", "سلع ترفيهية أخرى", "Other recreational goods"], ["09.2.1", "الألعاب", "Games, toys and hobbies"],
  ["09.2.1.1", "أجهزة وألعاب الفيديو", "Video game computers, game consoles, game apps and software"], ["09.2.1.1-a", "أجهزة وألعاب الفيديو", "Game consoles and video games"],
  ["09.2.1.2", "ألعاب أخرى", "Other games, toys and hobbies"], ["09.2.1.2-a", "ألعاب الأطفال", "Toys"],
  ["09.2.1.3", "مستلزمات الاحتفالات", "Celebration articles"], ["09.2.1.3-a", "الأزياء التنكرية ومستلزمات الحفلات", "Costumes and party articles"],
  ["09.3", "منتجات الحدائق والحيوانات الأليفة", "Garden products and pets"],
  ["09.3.1", "منتجات الحدائق والنباتات والزهور", "Garden products, plants and flowers"], ["09.3.1.1", "منتجات الحدائق", "Garden products"], ["09.3.1.1-a", "مستلزمات الحدائق", "Garden supplies"],
  ["09.3.2", "مستلزمات الحيوانات الأليفة", "Pets and products for pets"], ["09.3.2.2", "منتجات الحيوانات الأليفة", "Products for pets and other household animals"], ["09.3.2.2-a", "أغذية الحيوانات الأليفة", "Pet food"],
  ["09.7", "الصحف والكتب والقرطاسية", "Newspapers, books and stationery"],
  ["09.7.1", "الكتب", "Books"], ["09.7.1.9", "كتب أخرى", "Other books"], ["09.7.1.9-a", "الكتب", "Books"],
  ["09.7.4", "القرطاسية ومواد الرسم", "Stationery and drawing materials"], ["09.7.4.0", "القرطاسية ومواد الرسم", "Stationery and drawing materials"], ["09.7.4.0-a", "الدفاتر والأقلام والقرطاسية", "Notebooks, pens and stationery"],
  ["13", "العناية الشخصية والسلع والخدمات المتنوعة", "Personal care, social protection and miscellaneous goods and services"],
  ["13.1", "العناية الشخصية", "Personal care"],
  ["13.1.1", "أجهزة العناية الشخصية الكهربائية", "Electric appliances for personal care"], ["13.1.1.1", "أجهزة العناية الشخصية الكهربائية", "Electric appliances for personal care"], ["13.1.1.1-a", "مجففات الشعر وماكينات الحلاقة", "Hair dryers, shavers and trimmers"],
  ["13.1.2", "أجهزة أخرى (غير كهربائية) وأصناف ومنتجات معدة للعناية الشخصية", "Other appliances, articles and products for personal care"],
  ["13.1.2.0", "منتجات العناية الشخصية", "Other appliances, articles and products for personal care"],
  ["13.1.2.0-a", "العطور", "Perfumes"], ["13.1.2.0-b", "مزيلات العرق", "Deodorants"], ["13.1.2.0-c", "الشامبو والصابون", "Shampoo and soap"], ["13.1.2.0-d", "العناية بالبشرة", "Skin care"],
  ["13.1.2.0-e", "معجون الأسنان", "Toothpaste"], ["13.1.2.0-f", "المناديل الورقية", "Facial tissues"], ["13.1.2.0-g", "أدوات الحلاقة", "Razors"], ["13.1.2.0-h", "الفوط الصحية والحفاضات", "Sanitary pads and diapers"],
  ["13.2", "مقتنيات شخصية أخرى", "Other personal effects"], ["13.2.9", "سلع شخصية أخرى", "Other personal effects n.e.c."],
  ["13.2.9.1", "حقائب السفر ومستلزمات الأطفال وسلع شخصية أخرى", "Travel goods and articles for babies and other personal effects n.e.c."], ["13.2.9.1-a", "الحقائب المدرسية", "School bags"],
];
const COICOP_SKIP = ["06", "07"];                 // health and transport: outside this team's scope
const CNODE = Object.fromEntries(COICOP.map(([c, ar, en]) => [c, { code: c, ar, en }]));
const cParent = (c) => c.includes("-") ? c.slice(0, c.indexOf("-")) : c.includes(".") ? c.slice(0, c.lastIndexOf(".")) : "";

// which item type a scraped product belongs to, from the shop's category (our crawl) and the product title
function coicopOf(cat, title) {
  const c = String(cat || "").toLowerCase().trim(), t = " " + String(title || "").toLowerCase() + " ";
  const has = (re) => re.test(t);
  const gender = () => has(/\bwomen|\bwoman|\bladies|\blady\b|\bgirls?\b|\bfemale/) ? "f" : has(/\bmen\b|\bmen'?s\b|\bmens\b|\bboys?\b|\bmale\b|\bgents?\b/) ? "m" : has(/\bbaby\b|\binfants?\b|\bnewborn|\btoddler|\bmonths?\b|\b\d+\s?-\s?\d+\s?m\b/) ? "b" : has(/\bkids?\b|\bchildren|\bjunior|\byouth\b/) ? "k" : "";
  const garment = (g) => {                      // which garment type for men/boys (m) or women/girls (f)
    if (has(/costume|cosplay|halloween|fancy dress|party dress up/)) return "09.2.1.3-a";
    if (g === "b") return "03.1.2.3-a";
    const m = g !== "f";
    if (has(/underwear|brief|boxer|panty|panties|bra\b|vests?\b|socks?\b|sleepsuit|pyjama|pajama/)) return m ? "03.1.2.1-d" : "03.1.2.2-e";
    if (!m && has(/dress|abaya|skirt|kaftan|jumpsuit/)) return "03.1.2.2-c";
    if (has(/jeans|trouser|pants|chino|short|jogger|legging/)) return m ? "03.1.2.1-b" : "03.1.2.2-b";
    if (has(/jacket|coat|blazer|suit\b|knit|cardigan|jumper|sweater|hoodie|sweatshirt|gilet|bomber|parka/)) return m ? "03.1.2.1-c" : "03.1.2.2-d";
    if (has(/shirt|t-shirt|tee\b|top\b|polo|blouse/)) return m ? "03.1.2.1-a" : "03.1.2.2-a";
    return m ? "03.1.2.1-e" : "03.1.2.2-f";
  };
  const fish = () => has(/shrimp|prawn|crab\b|lobster|squid|calamari|mussel|clam\b|octopus|oyster|scallop|cuttlefish|seafood/) ? (has(/stick|breaded|tempura/) ? "01.1.3.3-a" : "01.1.3.4-a")
    : has(/tuna|sardine|canned|\btin\b|in oil|in brine|finger|breaded|fish cake|surimi|crab stick|mackerel in/) ? "01.1.3.3-a"
    : has(/smoked|salted|dried|anchov/) ? "01.1.3.2-a" : "01.1.3.1-a";
  const meat = (poultryCat) => has(/sausage|burger|nugget|kofta|kebab|kabab|mortadella|salami|hot ?dog|luncheon|frank|shawarma|popcorn|tender|strips|breaded|marinated|meat ?ball|pepperoni|bacon|pastrami|\bham\b|cold cut|tikka|samosa|crispy|cordon|escalope|schnitzel|sliced turkey|smoked|spicy|bbq|kibbeh|corned/) ? "01.1.2.5-a"
    : has(/liver|kidney|heart|gizzard|tripe|tongue|brain|\bfeet\b|trotter|offal|marrow/) ? "01.1.2.4-a"
    : poultryCat || has(/chicken|poultry|turkey|duck|quail|\bhen\b/) ? "01.1.2.2-b" : "01.1.2.2-a";
  const fruit = () => has(/frozen/) ? "01.1.6.6-a" : has(/dried|raisin|prune|dehydrated/) ? "01.1.6.7-a"
    : has(/orange|lemon|lime\b|mandarin|tangerine|grapefruit|clementine|pomelo|citrus|kumquat/) ? "01.1.6.2-a"
    : has(/apple|pear\b|pears|peach|plum|apricot|cherr|nectarine|quince/) ? "01.1.6.3-a"
    : has(/berr|grape/) ? "01.1.6.4-a"
    : has(/banana|mango|pineapple|papaya|kiwi|avocado|guava|passion|dragon|lychee|rambutan|coconut|\bfigs?\b|jackfruit|mangosteen|longan/) ? "01.1.6.1-b"
    : "01.1.6.5-a";
  const veg = () => has(/frozen/) ? "01.1.7.8-a" : has(/canned|\btin\b|paste|puree|pickle/) ? "01.1.7.9-a"
    : has(/lentil|chickpea|kidney bean|fava|\bfoul\b|\bdal\b|dhal|split pea|black eyed|moong|dried beans/) ? "01.1.7.6-a"
    : has(/potato|cassava|yam\b|taro|sweet potato|colocasia/) ? "01.1.7.5-a"
    : has(/lettuce|spinach|cabbage|parsley|coriander|\bmint|celery|broccoli|cauliflower|leek|rocket|arugula|kale|molokhia|mulukhiyah|dill|basil|asparagus|artichoke|chard|watercress|spring onion|herbs?\b/) ? "01.1.7.1-a"
    : has(/tomato|cucumber|pepper|capsicum|eggplant|aubergine|brinjal|zucchini|courgette|squash|pumpkin|okra|bhindi|chil+i|\bcorn\b|marrow|gourd/) ? "01.1.7.2-a"
    : has(/green beans?|\bpeas?\b|snow pea|beans/) ? "01.1.7.3-a" : "01.1.7.4-a";
  const fruitOrVeg = () => has(/apple|banana|orange|mango|grape|berr|melon|pear\b|peach|plum|lemon|lime\b|kiwi|avocado|pineapple|papaya|pomegranate|guava|fig\b|cherr|apricot|mandarin|fruit|dates?\b/) && !has(/tomato|pepper|aubergine|eggplant/) ? fruit() : veg();
  const cupboard = () => has(/tuna|sardine/) ? "01.1.3.3-a" : has(/tomato paste|canned|chickpea|baked beans|\bbeans\b|sweet corn|\bpeas\b|foul|fava/) ? "01.1.7.9-a"
    : has(/sauce|ketchup|mayo|mustard|vinegar|dressing|chutney|stock|bouillon|\bcubes?\b|soy/) ? "01.1.9.3-b"
    : has(/spice|cumin|turmeric|cardamom|cinnamon|masala|paprika|saffron|curry|black pepper|chil+i powder|clove|oregano|thyme|za.?atar|seasoning/) ? "01.1.9.4-a"
    : has(/\bsalt\b/) ? "01.1.9.3-a" : has(/\boil\b|ghee/) ? (has(/ghee/) ? "01.1.5.2-a" : "01.1.5.1-a")
    : has(/noodle|vermicelli/) ? "01.1.1.5-b" : has(/pasta|spaghetti|macaroni|penne|fusilli|lasagn/) ? "01.1.1.5-a" : has(/\brice\b/) ? "01.1.1.1-a"
    : has(/jam\b|marmalade/) ? "01.1.8.3-b" : has(/honey/) ? "01.1.8.3-a" : has(/chocolate|cocoa|nutella/) ? "01.1.8.5-a"
    : has(/oats|corn ?flakes|cereal|muesli|granola/) ? "01.1.1.4-a" : has(/soup|ready meal|instant/) ? "01.1.9.1-a"
    : has(/sweetener|stevia|sucralose/) ? "01.1.8.2-a" : has(/\bsugar\b/) ? "01.1.8.1-a" : has(/flour|semolina/) ? "01.1.1.2-a"
    : has(/cake mix|brownie mix|pancake mix|muffin mix/) ? "01.1.1.3-a" : has(/jelly|custard|pudding|caramel/) ? "01.1.8.9-a" : "01.1.9.9-a";
  switch (true) {
    // food
    case /^(beef|lamb|fresh food fresh meat poultry fresh beef veal)$/.test(c): return meat(false);
    case /^(chicken|fresh food fresh meat poultry fresh chicken)$/.test(c): return meat(true);
    case /^(fish|fresh food fresh fish seafoods)$/.test(c): return fish();
    case /^(milk|fresh food dairy eggs cheese fresh milk)$/.test(c):
      return has(/almond|\boat|soy|coconut|rice milk|plant/) ? "01.1.4.4-a" : has(/chocolate|strawberry|banana|flavou?r|milkshake|vanilla|mango|saffron|coffee/) ? "01.1.4.7-a"
        : has(/condensed|evaporated|powder|cream|creamer/) ? "01.1.4.3-a" : has(/laban|buttermilk|ayran/) ? "01.1.4.6-a"
        : has(/skim|fat free|low fat|light|\b0%|\b1%|half/) ? "01.1.4.2-a" : "01.1.4.1-a";
    case c === "cheese": return "01.1.4.5-a";
    case /^(yoghurt|fresh food dairy eggs cheese yoghurt chilled desserts)$/.test(c): return has(/dessert|pudding|custard|caramel|jelly|mousse/) ? "01.1.4.7-b" : "01.1.4.6-a";
    case /^(eggs|fresh food dairy eggs cheese eggs)$/.test(c): return has(/\beggs?\b/) ? "01.1.4.8-a" : null;
    case c === "butter": return has(/margarine|spread/) ? "01.1.5.3-a" : "01.1.5.2-a";
    case c === "oil": return has(/\boil\b|ghee/) ? (has(/ghee/) ? "01.1.5.2-a" : "01.1.5.1-a") : null;
    case c === "fruit": return fruitOrVeg();
    case c === "dates": return "01.1.6.1-a";
    case c === "nuts": return has(/peanut butter|nut butter|tahini|tahina/) ? "01.1.8.4-a" : "01.1.6.8-a";
    case c === "vegetables": return fruitOrVeg();
    case c === "fresh food fruits vegetables": return fruitOrVeg();
    case c === "rice": return "01.1.1.1-a";
    case c === "grocery food cupboard rice pasta noodles": return has(/\brice\b/) ? "01.1.1.1-a" : has(/noodle|vermicelli/) ? "01.1.1.5-b" : "01.1.1.5-a";
    case c === "flour": return "01.1.1.2-a";
    case c === "bread": return "01.1.1.3-a";
    case c === "pasta": return has(/noodle|vermicelli/) ? "01.1.1.5-b" : "01.1.1.5-a";
    case c === "sugar": return has(/sweetener|stevia|sucralose/) ? "01.1.8.2-a" : "01.1.8.1-a";
    case c === "honey": return has(/jam\b|marmalade/) ? "01.1.8.3-b" : "01.1.8.3-a";
    case c === "salt": return "01.1.9.3-a";
    case /^grocery food cupboard( cooking ingredients| home baking sweeteners)?$/.test(c): return cupboard();
    case c === "grocery food cupboard frozen food":
      return has(/fries|potato|vegetable|\bpeas\b|\bcorn\b|okra|spinach|beans|molokhia/) ? "01.1.7.8-a" : has(/fish|shrimp|prawn|fillet|seafood/) ? fish()
        : has(/chicken|nugget|burger|sausage|kofta|meat|beef|kebab/) ? "01.1.2.5-a" : has(/ice cream/) ? "01.1.8.6-a" : has(/fruit|berr|mango/) ? "01.1.6.6-a" : "01.1.9.1-a";
    case c === "coffee": return "01.2.2.0-a";
    case c === "tea": return "01.2.3.0-a";
    case c === "juice": return "01.2.1.0-a";
    case c === "water": return "01.2.5.0-a";
    case c === "soft drinks": return has(/energy/) ? "01.2.9.0-a" : "01.2.6.0-a";
    case c === "garden": return has(/canned|chickpea|\bcorn\b|\bpeas\b|beans|foul|fava|tahin|\d+\s?g\b|frozen|vegetable/) ? (has(/frozen/) ? "01.1.7.8-a" : "01.1.7.9-a") : "09.3.1.1-a";
    // clothing and footwear
    case /^(men > shoes|men shoes)$/.test(c): return "03.2.1.1-a";
    case /^(women > shoes|women shoes)$/.test(c): return "03.2.1.2-a";
    case /^(kids shoes|boys > shoes|girls > shoes)$/.test(c): return "03.2.1.3-a";
    case /^(shoes|sports shoes|sandals)$/.test(c):
      if (has(/shoe ?laces|\blaces\b|insoles?|inserts|shoe cleaner|polish|brush|stretcher|shoe horn|deodori[sz]er|massag|organi[sz]er|\brack\b|display|storage|shoe bag|cover|protector|spray|charm|shoe lifts|soap|incense|dhoop|cream/)) return null;
      { const g = gender(); return g === "f" ? "03.2.1.2-a" : g === "k" || g === "b" ? "03.2.1.3-a" : g === "m" ? "03.2.1.1-a" : null; }
    case /^(baby > t-shirts|baby clothing)$/.test(c): return garment("b");
    case /^(boys > |men > |men )/.test(c): return garment("m");
    case /^(girls > |women > |women )/.test(c) || c === "abaya": return garment("f");
    case /^(kids clothing|underwear|socks)$/.test(c): { const g = gender(); return g === "b" ? "03.1.2.3-a" : has(/costume|cosplay|halloween/) ? "09.2.1.3-a" : g === "f" ? garment("f") : g === "m" || c !== "kids clothing" ? garment("m") : null; }
    case c === "jeans": return has(/yarn|extender|button|patch|hanger|iron-on|fabric|sticker/) || !has(/\bjeans?\b|denim/) || has(/parfum|perfume|eau de|toilette/) ? null : garment(gender() === "f" ? "f" : gender() === "b" ? "b" : "m");
    // furnishings and household
    case /^(refrigerator|home appliances > fridges & freezers)$/.test(c): return "05.3.1.1-a";
    case c === "home appliances > dishwashers": return "05.3.1.1-b";
    case /^(washing machine|home appliances > laundry)$/.test(c): return "05.3.1.2-a";
    case /^(air conditioner|home appliances > cooling & heating)$/.test(c): return has(/\bfan\b/) ? "05.3.2.9-a" : "05.3.1.3-a";
    case /^(vacuum cleaner|home appliances > floorcare)$/.test(c): return "05.3.1.4-a";
    case /^(blender|home appliances > cooking)$/.test(c): return has(/kettle|coffee|espresso|tea maker/) ? "05.3.2.2-a" : "05.3.2.1-a";
    case c === "kettle": return "05.3.2.2-a";
    case /^(iron|fan|home appliances > small appliances)$/.test(c): return has(/blender|mixer|chopper|juicer|air fryer|toaster/) ? "05.3.2.1-a" : has(/kettle|coffee/) ? "05.3.2.2-a" : "05.3.2.9-a";
    case c === "bedsheet": return "05.2.1.2-a";
    case c === "plates": return "05.4.0.1-a";
    case c === "cookware": return "05.4.0.3-a";
    case /^(batteries|light bulb)$/.test(c): return has(/charger|tester/) ? null : "05.5.2.2-a";
    case /^(detergent|grocery household laundry essentials)$/.test(c): return "05.6.1.1-a";
    case /^(dishwashing|grocery household dishwashing liquids tablets)$/.test(c): return "05.6.1.1-b";
    case /^(cleaning|grocery household cleaning essentials|grocery household)$/.test(c): return "05.6.1.1-c";
    case /^(air freshener|insecticide)$/.test(c): return "05.6.1.9-a";
    case c === "towel": return "05.6.1.9-b";
    case c === "tissue": return "13.1.2.0-f";
    // health
    case c === "paracetamol": return "06.1.1.1-a";
    case c === "vitamins": return "06.1.1.1-b";
    case c === "thermometer": return "06.1.2.1-a";
    case c === "first aid": return "06.1.2.3-a";
    // transport
    case c === "bicycle": return has(/bicycle|cycle|bike/) && !has(/\block\b|pump|helmet|light|bell|stand|cover|glove|bottle|holder|rack/) ? "07.1.3.0-a" : null;
    case c === "car battery": return has(/charger|tester|connector|clamp|cable|jump/) ? null : "07.2.1.2-a";
    case c === "car accessories": return "07.2.1.3-a";
    case c === "engine oil": return "07.2.2.4-a";
    // information and communication
    case /^(mobile phone|mobiles & tablets > mobiles)$/.test(c): return has(/case|cover|protector|charger|cable|holder/) ? "08.1.9.2-a" : "08.1.2.0-a";
    case /^(laptop|computing > laptops)$/.test(c): return has(/bag|sleeve|stand|cooler|skin|charger/) ? "08.1.3.2-a" : "08.1.3.1-a";
    case /^(tablet|mobiles & tablets > tablets)$/.test(c): return has(/case|cover|protector|stylus|pen\b|keyboard/) ? "08.1.9.2-a" : "08.1.3.1-b";
    case /^(router|computing > (monitors|printers & ink|storage|computing accessories|networking & wireless))$/.test(c): return "08.1.3.2-a";
    case /^(television|tv, video & audio > tvs)$/.test(c): return has(/wall mount|bracket|remote control|tv stand|hdmi|cable/) && !has(/smart tv|oled|qled|uhd|television/) ? null : "08.1.4.0-a";
    case /^(headphones|earphones|speaker|tv, video & audio > (audio|home cinema & soundbars))$/.test(c): return "08.1.4.0-b";
    case /^(smart watch|wearables & smartwatches > smartwatches)$/.test(c): return has(/strap|band\b|protector|charger|case/) ? "08.1.9.2-a" : "08.1.9.1-a";
    case /^(charger|power bank|usb cable|phone case|screen protector|mobiles & tablets > (mobile|tablet) accessories)$/.test(c): return "08.1.9.2-a";
    // recreation
    case /^(camera|cameras & camcorders > digital cameras)$/.test(c): return "09.1.1.1-a";
    case /^(gaming console|video games|gaming > (games|gaming consoles|gaming accessories))$/.test(c): return has(/foam|sword|plush|figure|costume|poster|mug/) ? "09.2.1.2-a" : "09.2.1.1-a";
    case c === "toys": return "09.2.1.2-a";
    case c === "pet food": return "09.3.2.2-a";
    case c === "books": return "09.7.1.9-a";
    case /^(notebook|pens|stationery)$/.test(c): return "09.7.4.0-a";
    // personal care
    case /^(hair dryer|health, fitness & beauty > grooming appliances)$/.test(c): return "13.1.1.1-a";
    case /^(perfume|health, fitness & beauty > fragrances)$/.test(c): return "13.1.2.0-a";
    case c === "deodorant": return "13.1.2.0-b";
    case /^(shampoo|soap)$/.test(c): return "13.1.2.0-c";
    case /^(body lotion|face mask)$/.test(c): return "13.1.2.0-d";
    case c === "toothpaste": return "13.1.2.0-e";
    case c === "razor": return "13.1.2.0-g";
    case /^(sanitary pads|diapers)$/.test(c): return "13.1.2.0-h";
    case c === "school bag": return "13.2.9.1-a";
  }
  return null;
}

// Indices over the saved days. A product's daily price comes from the history change log; the item type's daily change is the
// geometric mean of its products' price relatives (same product, same shop, two consecutive days); each higher level's daily
// change is the plain mean of its children's changes; the monitor chains the daily changes, first day = 100.
function coicopBuild(hist, weights, opts = {}) {
  const days = hist.days, D = days.length, store = opts.store || "", weighted = opts.weighted !== false;
  const nodes = new Map(), node = (code) => {
    if (!nodes.has(code)) { const n = { ...(CNODE[code] || { code, ar: code, en: code }), kids: [], prods: [] }; nodes.set(code, n); const p = cParent(code); if (code) node(p).kids.push(n); }
    return nodes.get(code);
  };
  const root = node(""); root.ar = "كل الأقسام"; root.en = "All items";
  let unclassified = 0;
  for (const [k, p] of Object.entries(hist.p)) {
    if (store && p.o !== store) continue;
    const type = coicopOf(p.c, p.t);
    if (!type) { unclassified++; continue; }
    if (COICOP_SKIP.includes(type.slice(0, 2))) continue;
    const pr = new Array(D).fill(null); let cur = null, e = 0;
    for (let d = 0; d < D; d++) { while (e < p.h.length && p.h[e][0] <= d) { cur = p.h[e][1]; e++; } pr[d] = cur > 0 ? cur : null; }
    if (!pr.some((x) => x)) continue;
    node(type).prods.push({ k, t: p.t, o: p.o, u: p.u, c: p.c, g: p.g, pr });
  }
  const cw = {};                                 // no official weights: every level is the plain mean of the levels below
  // what the reader walks through: a division lists its classes directly (the COICOP group level, e.g. 01.1 Food, is folded
  // in), and a level with a single branch below it takes that branch's content, so every click opens a real choice
  for (const d of root.kids) d.kids = d.kids.flatMap((g) => (g.prods.length ? [g] : g.kids));
  (function squash(n) { while (n !== root && n.kids.length === 1 && !n.prods.length) { const c = n.kids[0]; n.kids = c.kids; n.prods = c.prods; } n.kids.forEach(squash); })(root);
  const LN3 = Math.log(3);
  (function calc(n) {
    n.rel = new Array(D).fill(null);
    if (n.prods.length) {
      n.count = new Array(D).fill(0);
      for (let d = 0; d < D; d++) {
        let s = 0, m = 0;
        for (const q of n.prods) {
          if (q.pr[d]) n.count[d]++;
          if (d && q.pr[d] && q.pr[d - 1]) { const l = Math.log(q.pr[d] / q.pr[d - 1]); if (Math.abs(l) <= LN3) { s += l; m++; } }
        }
        if (d && m) n.rel[d] = Math.exp(s / m);
      }
      n.ow = cw[n.code] || 0;                                             // a class whose single branch was folded in keeps its weight
    } else {
      n.kids.forEach(calc);
      n.kids = n.kids.filter((k) => k.count && k.count.some((x) => x));
      n.ow = n.kids.reduce((a, k) => a + k.ow, 0) || cw[n.code] || 0;      // official weight: the class figure, or the sum of the classes below
      if (cw[n.code]) n.ow = cw[n.code];
      const anyW = weighted && n.kids.some((k) => k.ow > 0);
      for (const k of n.kids) k.w = anyW ? k.ow : 1;                         // children without an official weight count 0 when the others have one
      n.count = new Array(D).fill(0);
      for (let d = 0; d < D; d++) {
        let sw = 0, sr = 0;
        for (const k of n.kids) { n.count[d] += k.count[d]; if (k.rel[d] && k.w > 0) { sw += k.w; sr += k.w * k.rel[d]; } }
        if (d && sw) n.rel[d] = sr / sw;
      }
    }
    n.first = n.count.findIndex((x) => x > 0);
    n.idx = n.rel.map(() => null); let I = 100;
    for (let d = Math.max(n.first, 0); d < D; d++) { if (d > n.first && n.rel[d]) I *= n.rel[d]; n.idx[d] = n.count[d] || d > n.first ? +I.toFixed(3) : null; }
    n.last = n.idx[D - 1]; n.chg = n.last - 100;
    const prev = n.idx[D - 2]; n.day = prev ? (n.last / prev - 1) * 100 : 0;
    n.products = n.count[D - 1];
  })(root);
  (function impact(n) {
    const sw = n.kids.reduce((a, k) => a + (k.w > 0 ? k.w : 0), 0);
    for (const k of n.kids) { k.share = sw && k.w > 0 ? k.w / sw : 0; k.imp = k.share * k.chg; impact(k); }
    n.kids.sort((a, b) => Math.abs(b.imp) - Math.abs(a.imp) || Math.abs(b.chg) - Math.abs(a.chg) || b.products - a.products);
    for (const q of n.prods) { const f = q.pr.find((x) => x), l = q.pr[D - 1]; q.first = f; q.lastp = l; q.chg = f && l ? (l / f - 1) * 100 : null; }
    n.prods.sort((a, b) => Math.abs(b.chg ?? -1) - Math.abs(a.chg ?? -1));
  })(root);
  return { root, nodes, days, unclassified };
}

// The CPI Dashboard's internal card: a COICOP 2018 category browser fed by the daily crawl (every scraped product, not only
// the basket). It starts from one row (all divisions); a click lists the level below, and an item type lists its products with
// their photos. Levels are equal-weighted chains of product price changes: an internal monitor, no official figures.
let ctHist = null, ctTree = null; const ctOpen = new Set(), ctChartOpen = new Set(); let ctCharts = []; const ctInfo = new Map();
const CT_UP = "#b42318", CT_DOWN = "#1f7a3a";                       // a price rise is red, a fall green
const ctCol = (v) => (v > 0.005 ? CT_UP : v < -0.005 ? CT_DOWN : "var(--muted)");
const ctPct = (v, d = 2) => (v == null || !isFinite(v) ? "—" : (v > 0.005 ? "+" : v < -0.005 ? "−" : "") + Math.abs(v).toFixed(d) + "%");
const ctLevel = (c) => (!c ? L("All", "الكل") : c.includes("-") ? L("Item type", "نوع السلعة") : (LANG === "ar" ? ["القسم", "المجموعة", "الفئة", "الفئة الفرعية"] : ["Division", "Group", "Class", "Subclass"])[c.split(".").length - 1]);
const ctName = (n) => (LANG === "ar" ? n.ar : n.en);
function ctSpark(vals, W = 150, H = 32) {
  const pts = vals.map((v, i) => [i, v]).filter((x) => x[1] != null);
  if (!pts.length) return "";
  const v = pts.map((x) => x[1]), lo = Math.min(...v), hi = Math.max(...v), span = hi - lo || 1, n = vals.length;
  const col = ctCol((v[v.length - 1] / v[0] - 1) * 100);
  const xy = pts.map(([i, y]) => [n === 1 ? W / 2 : 4 + (i * (W - 8)) / (n - 1), H - 4 - ((y - lo) / span) * (H - 8)]);
  const line = xy.length > 1 ? `<polyline fill="none" stroke="${col}" stroke-width="2" stroke-linejoin="round" points="${xy.map((p) => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ")}"/>` : "";
  const [lx, ly] = xy[xy.length - 1];
  return `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(L("Price trend", "اتجاه السعر"))}" style="direction:ltr">${line}<circle cx="${lx.toFixed(1)}" cy="${ly.toFixed(1)}" r="3" fill="${col}"/></svg>`;
}
async function loadCoicop() {
  const pid = current;
  try {
    const snap = await db.doc(`projects/${pid}/catalogue/latest`).get(); catDoc = snap.exists ? plain(snap) : null;
    if (current !== pid || !$("#ct-rows")) return;
    if (!catDoc?.history_asset) { $("#ct-rows").innerHTML = `<tr><td colspan="6" class="empty">${esc(L("No price history yet; it starts with the daily crawl.", "لا يوجد سجل أسعار بعد؛ يبدأ مع المسح اليومي."))}</td></tr>`; return; }
    $("#ov-n-prod").textContent = (catDoc.rows || 0).toLocaleString("en");
    $("#ov-n-store").textContent = Object.keys(catDoc.stores || {}).length.toLocaleString("en");
    $("#ct-store").innerHTML = `<option value="">${esc(L("All stores", "كل المتاجر"))}</option>` + Object.entries(catDoc.stores || {}).sort((a, b) => b[1] - a[1]).map(([s, n]) => `<option value="${esc(s)}">${esc(s)} (${n.toLocaleString("en")})</option>`).join("");
    const [h] = await Promise.all([fetch("/_blob/" + catDoc.history_asset).then((r) => r.json()), loadChartLib()]);
    if (current !== pid || !$("#ct-rows")) return;
    ctHist = h; $("#ov-n-days").textContent = h.days.length.toLocaleString("en");
    $("#ct-store").onchange = () => { ctBuild(); ctDraw(); };
    $("#ct-rows").onclick = (e) => { const tr = e.target.closest(".ct-row"); if (tr && !e.target.closest("a")) ctToggle(tr.dataset.code, !!e.target.closest(".ct-spark")); };
    $("#ct-rows").onkeydown = (e) => { if ((e.key === "Enter" || e.key === " ") && e.target.classList.contains("ct-row")) { e.preventDefault(); ctToggle(e.target.dataset.code, false); } };
    $("#ov-xlsx").onclick = (e) => ctExcel(e.currentTarget);
    ctBuild(); ctDraw();
    await ensureCat([]);                                                   // photos, sizes and unit prices of today's products
    const ix = catIx;
    for (const r of catData.rows) ctInfo.set(r[ix.outlet] + "|" + (r[ix.retailer_id] || r[ix.url]), { photo: r[ix.photo_url], size: String(r[ix.size] || "").replace(/\s*(min order|only \d+ left|tod\.|tom\.|global store|express|delivery).*$/i, "").trim(), unit: r[ix.unit_price], basis: r[ix.price_basis] });
    if (current === pid) ctDraw();
  } catch (e) { if ($("#ct-note")) $("#ct-note").textContent = L("Could not read the prices: ", "تعذّر تحميل الأسعار: ") + (e?.message || e); }
}
function ctBuild() { ctTree = coicopBuild(ctHist, {}, { store: $("#ct-store")?.value || "", weighted: false }); }
function ctToggle(code, chart) {
  const set = chart ? ctChartOpen : ctOpen;
  if (set.has(code)) { set.delete(code); if (!chart) for (const c of [...ctOpen, ...ctChartOpen]) if (code === "" ? c : c.startsWith(code + ".") || c.startsWith(code + "-")) { ctOpen.delete(c); ctChartOpen.delete(c); } }
  else set.add(code);
  ctDraw();
  const n = ctTree.nodes.get(code);
  if (!chart && ctOpen.has(code) && n?.prods.length) {                     // an item type: load the photos of its catalogue section
    const need = [...new Set(n.prods.map((q) => q.g))].filter((g) => catDoc?.thumbs_assets?.[g] && !catGot[g]);
    if (need.length) ensureCat(need).then(() => ctOpen.has(code) && ctDraw());
  }
}
const CT_LEVEL_COLORS = ["#14264b", "#1678be", "#1ea5e0", "#2e88c2", "#d9a43a", "#8d6e63"];
function ctDraw() {
  if (!ctTree || !$("#ct-rows")) return;
  ctCharts.forEach((c) => c.destroy()); ctCharts = [];
  const { root, days } = ctTree, d0 = days[0], out = [];
  const pad = (depth) => `padding-inline-start:${12 + depth * 26}px;border-inline-start:5px solid ${CT_LEVEL_COLORS[Math.min(depth, CT_LEVEL_COLORS.length - 1)]}`;
  const row = (n, depth) => {
    const open = ctOpen.has(n.code), leaf = n.prods.length > 0, nKids = leaf ? n.prods.length : n.kids.length;
    return `<tr class="ct-row" tabindex="0" aria-expanded="${open}" data-code="${esc(n.code)}" style="cursor:pointer;background:${open ? "#eaf4fb" : depth % 2 ? "#fafbfc" : "#fff"}">
      <td style="${pad(depth)}">${open ? ico("chevd") : ico("chevr", "flip")}
        ${n.code ? `<span class="mono" style="color:var(--muted)">${esc(n.code.replace(/-[a-z]$/, ""))}</span> ` : ""}<b>${esc(ctName(n))}</b>
        <div class="muted" style="font-size:12px;margin-inline-start:20px">${esc(ctLevel(n.code))} · ${esc(LANG === "ar" ? n.en : n.ar)} · ${leaf ? L(`${nKids.toLocaleString("en")} products with photos`, `${nKids.toLocaleString("en")} منتجاً بالصور`) : L(`${nKids} items below`, `${nKids} بنود تحته`)}</div></td>
      <td class="num">${(n.products || 0).toLocaleString("en")}</td>
      <td class="num"><b>${n.last != null ? n.last.toFixed(2) : "—"}</b></td>
      <td class="num" style="color:${ctCol(n.chg)}">${ctPct(n.chg)}</td>
      <td class="num" style="color:${ctCol(n.day)}">${ctPct(n.day)}</td>
      <td class="ct-spark" title="${esc(L("Open the full chart", "اضغط لعرض الرسم الكامل"))}" style="cursor:zoom-in">${ctSpark(n.idx)}<div class="muted" style="font-size:11px">${ctChartOpen.has(n.code) ? esc(L("Hide chart", "إخفاء الرسم")) : ico("chart") + " " + esc(L("Full chart", "الرسم الكامل"))}</div></td></tr>`;
  };
  const chartRow = (n, depth) => {
    const top = n.kids.slice(0, 6);
    return `<tr class="ct-detail"><td colspan="6" style="background:#fff;${pad(depth)}"><div class="ltr" style="position:relative;height:250px"><canvas data-ct="${esc(n.code)}" role="img" aria-label="${esc(ctName(n))}"></canvas></div>
      <p class="muted" style="margin:6px 0 0">${esc(ctName(n))} · ${esc(L(`internal monitor (${d0} = 100)`, `مؤشر داخلي (${d0} = 100)`))}${top.length ? esc(L(` with the ${top.length} largest items below`, ` مع أكبر ${top.length} بنود تحته`)) : ""} · ${days.length} ${esc(L("days", "يوماً"))}</p></td></tr>`;
  };
  const prodRow = (n, depth) => {
    const ps = n.prods.slice(0, 200);
    return `<tr class="ct-detail"><td colspan="6" style="background:#fff;${pad(depth)}"><div class="tw"><table><thead><tr><th>${esc(L("Photo", "صورة"))}</th><th>${esc(L("Product", "المنتج"))}</th><th>${esc(L("Store", "المتجر"))}</th><th>${esc(L("Size", "الحجم"))}</th><th class="num">${esc(L("First price", "أول سعر"))}</th><th class="num">${esc(L("Last price", "آخر سعر"))}</th><th class="num">${esc(L("Change", "التغير"))}</th><th>${esc(L("Trend", "الاتجاه"))}</th></tr></thead><tbody>${ps.map((q) => {
      const inf = ctInfo.get(q.k) || {}, b = inf.photo && catThumbs[inf.photo];
      const unit = inf.unit && inf.basis ? `<br><span class="muted">${Number(inf.unit).toFixed(2)} / ${esc(inf.basis)}</span>` : "";
      return `<tr><td>${b ? `<img class="thumb" src="data:image/jpeg;base64,${b}" alt="">` : inf.photo ? `<img class="thumb" src="${esc(inf.photo)}" alt="" loading="lazy" onerror="this.remove()">` : ""}</td>
        <td><a href="${esc(q.u)}" target="_blank" rel="noopener" dir="auto">${esc(q.t)}</a></td><td>${esc(q.o)}</td><td dir="auto">${esc(inf.size || "")}</td>
        <td class="num">${q.first != null ? q.first.toFixed(2) : "—"}</td><td class="num"><b>${q.lastp != null ? q.lastp.toFixed(2) : esc(L("not listed today", "غير معروض اليوم"))}</b>${unit}</td>
        <td class="num" style="color:${ctCol(q.chg)}">${ctPct(q.chg, 1)}</td><td class="ltr">${ctSpark(q.pr, 130, 30)}</td></tr>`; }).join("")}</tbody></table></div>
      <p class="muted" style="margin:6px 0 0">${esc(L(`${n.prods.length.toLocaleString("en")} products, largest change first${n.prods.length > 200 ? " · first 200 shown; all in the Excel file" : ""}. Shelf prices in AED; the price per kg, litre or piece below when known.`, `${n.prods.length.toLocaleString("en")} منتجاً، مرتبة من الأكبر تغيراً${n.prods.length > 200 ? " · يظهر أول 200؛ الكل في ملف Excel" : ""}. الأسعار بالدرهم كما على رف المتجر؛ تحتها سعر الكيلو أو اللتر أو القطعة حين يتوفر.`))}</p></td></tr>`;
  };
  const walk = (n, depth) => {
    out.push(row(n, depth));
    if (ctChartOpen.has(n.code)) out.push(chartRow(n, depth));
    if (!ctOpen.has(n.code)) return;
    if (n.prods.length) out.push(prodRow(n, depth + 1));
    else for (const k of n.kids) walk(k, depth + 1);
  };
  walk(root, 0);
  $("#ct-rows").innerHTML = out.join("");
  $("#ct-head-chg").textContent = L(`Change since ${d0}`, `التغير منذ ${d0}`);
  for (const cv of $$("#ct-rows canvas[data-ct]")) {
    const n = ctTree.nodes.get(cv.dataset.ct) || (cv.dataset.ct === "" ? root : null); if (!n) continue;
    const sets = [{ label: ctName(n), data: n.idx, borderColor: "#14264b", backgroundColor: "rgba(20,38,75,.08)", fill: true, borderWidth: 3, pointRadius: 3, tension: 0.2, spanGaps: true }]
      .concat(n.kids.slice(0, 6).map((k, i) => ({ label: ctName(k), data: k.idx, borderColor: CH_COLORS[(i + 1) % CH_COLORS.length], borderWidth: 1.5, pointRadius: 2, tension: 0.2, spanGaps: true })));
    ctCharts.push(new window.Chart(cv, { type: "line", data: { labels: days, datasets: sets },
      options: { responsive: true, maintainAspectRatio: false, interaction: { mode: "nearest", intersect: false },
        plugins: { legend: { position: "bottom", labels: { usePointStyle: true, font: { size: 11 } } }, tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${Number(c.parsed.y).toFixed(2)}` } } },
        scales: { y: { title: { display: true, text: L("Monitor (first day = 100)", "المؤشر (أول يوم = 100)") } } } } }));
  }
  $("#ct-note").textContent = L(`${ctTree.root.products.toLocaleString("en")} classified products over ${days.length} days (${d0} to ${days[days.length - 1]})`, `${ctTree.root.products.toLocaleString("en")} منتجاً مصنّفاً في ${days.length} يوماً (${d0} إلى ${days[days.length - 1]})`)
    + (ctTree.unclassified ? L(` · ${ctTree.unclassified.toLocaleString("en")} products outside the classification`, ` · ${ctTree.unclassified.toLocaleString("en")} منتجاً خارج التصنيف`) : "")
    + L(". Categories: COICOP 2018 (health and transport out of scope). Each item type: geometric mean of the day-to-day change of the same product in the same store; each level above: the plain mean of the levels below; first day = 100. An internal monitor, not the CPI. Red is a rise, green a fall.",
        ". التصنيف: COICOP 2018 (الصحة والنقل خارج النطاق). لكل نوع سلعة: متوسط هندسي لتغير سعر نفس المنتج في نفس المتجر من يوم لليوم التالي؛ وكل مستوى أعلى متوسط بسيط لما تحته؛ أول يوم = 100. مؤشر داخلي، ليس الرقم القياسي لأسعار المستهلك. الأحمر ارتفاع والأخضر انخفاض.");
}
async function ctExcel(btn) {
  if (!ctTree) return toast(L("The prices are still loading…", "تُحمَّل الأسعار بعد…"), true);
  if (!downloads) return toast(L("Downloads are not available in this view", "التنزيل غير متاح في هذا العرض"), true);
  const old = btn.innerHTML; btn.disabled = true; btn.textContent = L("Preparing…", "يُجهَّز…");
  try {
    const ExcelJS = await loadExcel(), wb = new ExcelJS.Workbook(), { root, days } = ctTree;
    const head = (ws, cols, widths) => { const r = ws.getRow(1); r.height = 30; cols.forEach((h, i) => { const c = r.getCell(i + 1); c.value = h; c.font = { bold: true, color: { argb: "FFFFFFFF" } }; c.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF14264B" } }; c.alignment = { horizontal: "center", vertical: "middle", wrapText: true }; ws.getColumn(i + 1).width = widths[i] || 12; }); ws.views = [{ state: "frozen", ySplit: 1 }]; };
    const t = wb.addWorksheet("COICOP tree");
    head(t, ["Level", "COICOP 2018 code", "Name (Arabic)", "Name (English)", "Products (last day)", `Change since ${days[0]} %`, "Last-day change %", ...days.map((d) => `Monitor ${d}`)], [14, 14, 38, 44, 12, 14, 12]);
    const prodRows = [];
    const lv = (c) => (!c ? "All" : c.includes("-") ? "Item type" : ["Division", "Group", "Class", "Subclass"][c.split(".").length - 1]);
    const walk = (n) => {
      t.addRow([lv(n.code), n.code.replace(/-[a-z]$/, "") || "All", n.ar, n.en, n.products, +n.chg.toFixed(3), +n.day.toFixed(3), ...n.idx.map((v) => (v == null ? null : +v.toFixed(3)))]);
      for (const q of n.prods) { const inf = ctInfo.get(q.k) || {}; prodRows.push([n.code.replace(/-[a-z]$/, ""), n.ar, n.en, q.o, q.t, inf.size || "", q.first, q.lastp, q.chg == null ? null : +q.chg.toFixed(3), ...q.pr, q.u, inf.photo || ""]); }
      n.kids.forEach(walk);
    };
    walk(root);
    const p = wb.addWorksheet("Products");
    head(p, ["COICOP 2018 subclass", "Item type (Arabic)", "Item type (English)", "Store", "Product", "Size", "First price (AED)", "Last price (AED)", "Change %", ...days.map((d) => `Price ${d}`), "Product URL", "Photo URL"], [14, 30, 30, 14, 50, 12, 12, 12, 10]);
    prodRows.forEach((r) => p.addRow(r));
    const buf = await wb.xlsx.writeBuffer();
    await downloads.save({ filename: `CPI_COICOP_tree_${days[days.length - 1]}.xlsx`, data: new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }) });
    toast(L(`${prodRows.length.toLocaleString("en")} products · ${days.length} days`, `${prodRows.length.toLocaleString("en")} منتجاً · ${days.length} يوماً`));
  } catch (e) { if (e?.code !== "cancelled" && e?.code !== "declined") toast(L("Could not prepare the file: ", "تعذّر تجهيز الملف: ") + (e?.message || e), true); }
  finally { btn.disabled = false; btn.innerHTML = old; }
}
