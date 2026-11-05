// ------------------------------------------------------------ scrapers (collection "scrapers", document id = the unique map name)
/* A scraper reads a site's listing pages (and optional detail pages) with the user's own scripts, on one of two engines with
   the same inputs: Apify (run from this page through the Apify connector) or Scrapling (on Claude's servers: "Run now" leaves
   run_request on the document for the scheduled routine, and fires that routine at once when system/scrapers_routine holds
   its trigger id). Runs: scrapers/<id>/runs/<run id>, rows in .../rows/cNNN (saveChunks). Each project lists the scrapers
   whose `project` is its id, on #<p>-scrapers; the workspace is #<p>-scrapers/new and #<p>-scrapers/<map name>. */
const SC_PROJECTS = ["cpi", "te", "sppi", "hotels", "cci", "rent"];
const SC_TZ = ["Asia/Dubai", "Asia/Muscat", "Asia/Riyadh", "Asia/Qatar", "Asia/Kuwait", "Asia/Bahrain", "Asia/Amman", "Africa/Cairo", "Asia/Karachi", "Asia/Kolkata", "Europe/London", "Europe/Paris", "America/New_York", "UTC"];
const SC_ENGINE = { apify: "Apify", scrapling: "Scrapling" };
const scStatus = (s) => ({ done: L("Completed", "انتهى"), error: L("Failed", "خطأ"), running: L("Running", "يعمل") }[s] || s);
const SC_WAIT_APIFY = { load: "load", domcontentloaded: "domcontentloaded", networkidle: "networkidle2" };
const SC_FIELDS = ["sc-name", "sc-engine", "sc-map", "sc-urls", "sc-list-script", "sc-details-script", "sc-target", "sc-run-at", "sc-actor", "sc-input"];
const SC_KEYS = ["name", "engine", "project", "outlet", "map_name", "browser_type", "wait_until", "link_selector", "target_urls", "list_script", "details_script", "target_items", "active", "auto", "payload", "apify"];
const scSteps = () => (LANG === "ar" ? ["يبدأ على Apify", "يعمل على Apify", "تُجلب العناصر", "تُحفظ النتائج"] : ["Starting on Apify", "Running on Apify", "Fetching the items", "Saving the results"]);
const scMapHint = (mode) => (mode === "new"
  ? L("The scraper's id: lowercase English letters, digits, <code>_</code> and <code>-</code>. Unique; it cannot change after saving.", "معرّف الكاشطة: أحرف إنجليزية صغيرة وأرقام و <code>_</code> و <code>-</code>. لا يتكرر، ولا يتغيّر بعد الحفظ.")
  : L("It cannot change after saving, because the scraper's runs are stored under it. For another name use Duplicate and save the copy.", "لا يتغيّر بعد الحفظ لأن تشغيلات الكاشطة تُحفظ تحته. لاسم آخر استخدم «نسخ» واحفظ النسخة."));
const scAutoHint = () => L("Scrapers run on demand (Run now). The custom-scrapers routine has no daily time (docs/routines/custom_scrapers.md), so this section stays off.", "الكاشطات تعمل عند الطلب («شغّل الآن»). مهمة الكاشطات المخصصة بلا موعد يومي، لذلك يبقى هذا القسم متوقفاً.");
let scrapers = {}, scLoaded = false, scLoadErr = "";
let scRoute = null;              // null while another page is open; "list" | "new" | a scraper id
let scProj = "cpi";              // the project whose Scrapers page is open
let scId = null, scDraft = null, scBase = "", scDirty = false, scShowAll = false, scMapEdited = false;
const scTouched = new Set(), scFired = {};
let scJob = null, scRuns = [], scShownRun = null, scShownRows = [];

function tzOffset(tz) {
  try {
    const v = new Intl.DateTimeFormat("en-US", { timeZone: tz, timeZoneName: "longOffset" }).formatToParts(new Date()).find((x) => x.type === "timeZoneName")?.value || "";
    return v === "GMT" ? "+00:00" : v.replace("GMT", "");
  } catch (e) { return ""; }
}
const tzLabel = (tz) => (tzOffset(tz) ? `(GMT${tzOffset(tz)}) ${tz}` : String(tz || ""));
function scBlank() {
  return { name: "", engine: "scrapling", project: scProj || "", outlet: "", map_name: "", browser_type: "http", wait_until: "load", link_selector: "",
    target_urls: [], list_script: "", details_script: "", target_items: 0, active: true,
    auto: { enabled: false, run_at: "06:30", tz: "Asia/Dubai" }, payload: "", apify: { actor_id: "apify/web-scraper", input: "" },
    run_request: null, last_run: null, last_scraped: 0, created_at: null, updated_at: null };
}
function scNorm(d) {
  const b = scBlank(), x = d || {};
  return { ...b, project: "", ...x, engine: x.engine === "apify" ? "apify" : "scrapling", target_urls: Array.isArray(x.target_urls) ? x.target_urls.map(String) : [],
    target_items: Number.isFinite(+x.target_items) ? +x.target_items : 0, active: x.active !== false,
    auto: { ...b.auto, ...(x.auto || {}) }, apify: { ...b.apify, ...(x.apify || {}) },
    payload: typeof x.payload === "string" ? x.payload : x.payload == null ? "" : JSON.stringify(x.payload, null, 2) };
}
const scStored = (d) => Object.fromEntries(SC_KEYS.map((k) => [k, d[k] ?? ""]));
const scKey = (d) => JSON.stringify(scStored(d));
const scPending = (s) => !!s?.run_request?.at && (!s.last_run?.at || String(s.run_request.at) > String(s.last_run.at));
const scEngineChip = (e) => `<span class="chip eng-${e === "apify" ? "apify" : "scrapling"}">${esc(SC_ENGINE[e] || "Scrapling")}</span>`;
const scProjName = (p) => projLabel(p);
const scHash = (r) => `${routeOf(scProj)}-scrapers${r === "list" ? "" : r === "new" ? "/new" : "/" + r}`;
function scParse(h) { const m = /^([a-z]+)-scrapers(?:\/([a-z0-9_-]+))?$/.exec(h || ""); if (!m) return null; return m[2] ? (m[2] === "new" ? "new" : m[2]) : "list"; }
const scMotion = () => (matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth");
function scDur(r) {
  const s = (Date.parse(r.finishedAt) - Date.parse(r.startedAt)) / 1000;
  if (!Number.isFinite(s) || s < 0) return "—";
  return s < 60 ? L(`${Math.round(s)} s`, `${Math.round(s)} ث`) : s < 3600 ? L(`${Math.floor(s / 60)} min ${Math.round(s % 60)} s`, `${Math.floor(s / 60)} د ${Math.round(s % 60)} ث`) : L(`${Math.floor(s / 3600)} h ${Math.floor((s % 3600) / 60)} min`, `${Math.floor(s / 3600)} س ${Math.floor((s % 3600) / 60)} د`);
}
// an in-page confirmation in `box` (text is already escaped by the caller); no confirm(). Focus goes to the confirm button
// (the cancel button for a delete) and returns to `returnTo` when it closes.
function askInline(box, html, yes, onYes, danger = false, returnTo = null) {
  const back = returnTo || (document.activeElement !== document.body ? document.activeElement : null);
  box.innerHTML = `<div class="confirm"><span>${html}</span><button type="button" class="${danger ? "danger" : "primary"}" data-yes>${esc(yes)}</button><button type="button" data-no>${esc(L("Cancel", "إلغاء"))}</button></div>`;
  const done = () => { box.innerHTML = ""; try { if (back && back.isConnected) back.focus(); } catch (e) {} };
  $("[data-no]", box).onclick = done;
  $("[data-yes]", box).onclick = () => { done(); onYes(); };
  $(danger ? "[data-no]" : "[data-yes]", box).focus();
}

async function scLoad() {
  try {
    const snap = await db.collection("scrapers").get();
    scrapers = {}; snap.docs.forEach((d) => (scrapers[d.id] = scNorm(plain(d))));
    scLoadErr = "";
  } catch (e) { scLoadErr = dbErr(e); }
  scLoaded = true;
}

// ---------------- routing
function scLeave() { if (!scRoute) return; scRoute = null; scDirty = false; $("#sc-leave-confirm").hidden = true; }
// unsaved form edits: ask in the save bar instead of leaving; `then` continues the navigation after "discard"
function scCanLeave(then) {
  if (!scDirty) return true;
  scSwitchTab("setup");
  const box = $("#sc-leave-confirm"); box.hidden = false;
  box.innerHTML = `<div class="confirm"><span>${esc(L("This scraper has unsaved changes. Save or discard them before leaving.", "في الكاشطة تعديلات غير محفوظة. احفظها أو تجاهلها قبل الانتقال."))}</span><button type="button" class="danger" data-yes>${esc(L("Discard changes", "تجاهل التعديلات"))}</button><button type="button" data-no>${esc(L("Keep editing", "متابعة التحرير"))}</button></div>`;
  $("[data-no]", box).onclick = () => { box.hidden = true; box.innerHTML = ""; $("#sc-save").focus(); };
  $("[data-yes]", box).onclick = () => { box.hidden = true; box.innerHTML = ""; scDirty = false; then(); };
  $("[data-no]", box).focus();
  return false;
}
async function scGo(route, opts = {}) {
  if (basketDirty && current) { toast(L("Save the basket changes first, or reload the page to drop them", "احفظ تعديلات السلة أولاً أو أعد تحميل الصفحة لتجاهلها"), true); return false; }
  if (scRoute && !opts.force && (scRoute !== route || opts.draft) && !scCanLeave(() => scGo(route, { ...opts, force: true }))) return false;
  const fresh = scRoute !== route;
  scRoute = route;
  showScraperFrame(route);                       // the app draws the list page, or mounts the workspace block
  if (fresh) try { window.scrollTo(0, 0); } catch (e) {}
  if (!scLoaded) {
    if (route === "list") scRenderList();
    await scLoad();
    if (scRoute !== route) return true;
  }
  if (route === "list") scRenderList(); else if (route === "new") scOpenForm(opts.draft || null); else scOpenScraper(route, opts.tab);
  if (fresh && route !== "new") scRefresh(route);
  return true;
}
// re-read from the database after the page is shown (the routine and other viewers change run state)
async function scRefresh(route) {
  if (route === "list") { await scLoad(); if (scRoute === "list") scRenderList(); return; }
  try { const snap = await db.doc(`scrapers/${route}`).get(); if (!snap.exists || scRoute !== route) return;
    const d = scNorm(plain(snap)); scrapers[route] = scDirty ? { ...scrapers[route], run_request: d.run_request, last_run: d.last_run, last_scraped: d.last_scraped } : d;
    scRenderPending(); scRenderSummary(scCollect()); } catch (e) {}
}
function scHead(mode, s) {
  const isNew = mode === "new";
  $("#sc-title").textContent = isNew ? L("New scraper", "كاشطة جديدة") : s?.name || s?.map_name || L("Scraper workspace", "مساحة عمل الكاشطة");
  $("#sc-eyebrow").textContent = L("Update the scraper profile, fine-tune extraction settings, and review operational metadata.", "حدّث بيانات الكاشطة، واضبط إعدادات الاستخراج، وراجع بيانات التشغيل.");
  $("#sc-run-now").hidden = isNew; $("#sc-save-top").hidden = false;
  $("#sc-tabs-box").hidden = isNew;
  $("#sc-head-confirm").innerHTML = ""; $("#sc-del-confirm").innerHTML = "";
  $("#sc-sum-actions").hidden = isNew;
  $("#sc-banner").hidden = true;
  if (isNew) { $("#sc-runs").hidden = true; $("#sc-setup").hidden = false; }
}
function scSwitchTab(t) {
  $$("#sc-tabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.sctab === t)));
  $("#sc-setup").hidden = t !== "setup"; $("#sc-runs").hidden = t !== "runs";
}

// ---------------- list (#<p>-scrapers): the app draws the page frame (KPIs, filters, table); this fills it
function scRenderList() {
  scId = null;
  const body = $("#sc-list"); if (!body) return;
  const routine = routineRows(scProj);
  const own = Object.entries(scrapers).filter(([, s]) => (s.project || "") === scProj).sort((a, b) => String(a[1].name || a[0]).localeCompare(String(b[1].name || b[0])));
  const all = [...routine.map((r) => ({ routine: true, ...r })), ...own.map(([id, s]) => ({ id, s }))];
  const active = all.filter((x) => (x.routine ? x.active !== false : x.s.active)).length;
  const target = all.some((x) => x.routine && x.target == null) ? null : all.reduce((n, x) => n + (x.routine ? x.target || 0 : x.s.target_items || 0), 0);
  const setK = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
  const noData = scProj === "sppi" && !all.length && !sppiCache?.meta;
  if (scLoaded && noData) { for (const k of ["total", "active", "inactive", "target"]) setK("sc-k-" + k, "—"); }
  else if (scLoaded) { setK("sc-k-total", all.length.toLocaleString("en")); setK("sc-k-active", active.toLocaleString("en")); setK("sc-k-inactive", (all.length - active).toLocaleString("en")); setK("sc-k-target", target == null ? "—" : target.toLocaleString("en")); }
  if (!scLoaded) { body.innerHTML = `<tr><td colspan="6"><div class="loading">${esc(L("Loading scrapers…", "تُحمَّل الكاشطات…"))}</div></td></tr>`; return; }
  // the project's routine data (SPPI meta) failed to read: pink box with Retry above the table, never "No data yet"
  const rtBox = (() => { let eb = $("#sc-rt-err"); if (!eb && $("#sc-table")) { eb = document.createElement("div"); eb.id = "sc-rt-err"; $("#sc-table").closest(".tw").before(eb); } return eb; })();
  const rtErr = typeof scRoutineErr !== "undefined" && scRoutineErr?.pid === scProj ? scRoutineErr.e : null;
  if (rtBox) { rtBox.innerHTML = rtErr ? errBox(L("Unable to load this project's data right now. ", "تعذّر تحميل بيانات هذا المشروع الآن. ") + dbErr(rtErr), "sc-rt-retry") : ""; if (rtErr) $("#sc-rt-retry").onclick = async () => { await scRoutineData(scProj, true); if (scRoute === "list") scRenderList(); }; }
  if (scLoadErr) { body.innerHTML = `<tr><td colspan="6">${errBox(L("Unable to load scrapers right now.", "تعذّر تحميل الكاشطات الآن.") + " " + scLoadErr, "sc-retry")}</td></tr>`; return; }
  const q = ($("#sc-q")?.value || "").trim().toLowerCase(), f = $("#sc-filter")?.value || "", st = $("#sc-state")?.value || "";
  const list = all.filter((x) => {
    const type = x.routine ? "routine" : x.s.engine, on = x.routine ? x.active !== false : x.s.active;
    const text = x.routine ? [x.label, x.outlet, x.method].join(" ") : [x.s.name, x.id, x.s.outlet, x.s.apify?.actor_id].join(" ");
    return (!f || f === type) && (!st || (st === "active") === on) && (!q || text.toLowerCase().includes(q));
  });
  $("#sc-count").textContent = list.length === all.length ? L(`${all.length} scrapers`, `${all.length} كاشطة`) : L(`${list.length} of ${all.length} scrapers`, `${list.length} من ${all.length} كاشطة`);
  if (noData) $("#sc-count").textContent = rtErr ? "—" : L("No data yet", "لا بيانات بعد");
  if (!list.length) { body.innerHTML = `<tr><td colspan="6"><div class="empty-state"><span class="es-ico">${ico("scraper")}</span><h3>${esc(all.length ? L("No scraper matches the filters", "لا توجد كاشطة تطابق البحث") : L("No scrapers yet", "لا توجد كاشطات بعد"))}</h3>${all.length ? `<button type="button" data-act="clear">${esc(L("Clear the filters", "مسح البحث"))}</button>` : `<button type="button" class="primary" data-act="new">${ico("plus")}${esc(L("Create scraper", "أنشئ كاشطة"))}</button>`}</div></td></tr>`; return; }
  body.innerHTML = list.map((x) => {
    if (x.routine) return `<tr class="routine"><td><b>${esc(x.label)}</b><br><span class="muted">${esc(x.method || "")}</span></td><td dir="auto">${esc(x.outlet)}</td>
      <td><span class="chip grey">${esc(L("Routine", "مهمة مجدولة"))}</span></td><td>${x.chip || ""}</td><td>${x.last || "—"}</td>
      <td><span class="muted">${esc(x.note || L("Runs from Schedules", "يعمل من الجداول"))}</span></td></tr>`;
    const { id, s } = x, lr = s.last_run, running = scJob?.running && scJob.sid === id;
    return `<tr data-sc="${esc(id)}"><td><button type="button" class="link-btn" style="font-size:15px;min-height:0;padding:0" data-act="open">${esc(s.name || id)}</button><br><span class="mono muted">${esc(id)}</span></td>
      <td dir="auto">${esc(outletName(scProj, s.outlet) || "—")}</td><td>${scEngineChip(s.engine)}</td>
      <td>${s.active ? `<span class="chip ok">${esc(L("Active", "مفعّلة"))}</span>` : `<span class="chip grey">${esc(L("Inactive", "متوقفة"))}</span>`}${running ? ` <span class="chip warn">${esc(L("Running now", "يعمل الآن"))}</span>` : scPending(s) ? ` <span class="chip warn">${esc(L("Waiting", "في الانتظار"))}</span>` : ""}</td>
      <td>${lr ? `<span class="chip ${lr.status === "done" ? "ok" : lr.status === "error" ? "bad" : "warn"}">${esc(scStatus(lr.status))}</span> ${esc((lr.items ?? s.last_scraped ?? 0).toLocaleString("en"))} ${esc(L("items", "عنصر"))} · <span class="muted">${esc(relTime(lr.at))}</span>` : `<span class="muted">${esc(L("Not run yet", "لم تُشغّل بعد"))}</span>`}</td>
      <td><div class="row" style="gap:6px;flex-wrap:nowrap"><button type="button" data-act="run" title="${esc(L("Run now", "شغّل الآن"))}">${ico("play", "fill")}<span>${esc(L("Run now", "شغّل الآن"))}</span></button><button type="button" data-act="open">${ico("edit")}<span>${esc(L("Edit", "تعديل"))}</span></button><button type="button" data-act="dup">${ico("copy")}<span>${esc(L("Duplicate", "نسخ"))}</span></button><button type="button" class="danger" data-act="del">${ico("trash")}<span>${esc(L("Delete", "حذف"))}</span></button></div><div data-confirm></div></td></tr>`;
  }).join("");
}
function scListClick(e) {
  const b = e.target.closest("[data-act]"); if (!b) return;
  const act = b.dataset.act, card = b.closest("[data-sc]"), id = card?.dataset.sc;
  if (act === "new") return go("#" + scHash("new"));
  if (act === "clear") { $("#sc-q").value = ""; $("#sc-filter").value = ""; $("#sc-state").value = ""; return scRenderList(); }
  if (!id || !scrapers[id]) return;
  const box = $("[data-confirm]", card);
  if (act === "open") go("#" + scHash(id));
  else if (act === "run") scRunNow(id, box);
  else if (act === "dup") scDuplicate(id);
  else if (act === "del") scAskDelete(id, box);
}

// ---------------- form
function scFillForm(d) {
  $("#sc-name").value = d.name || "";
  $("#sc-engine-apify").checked = d.engine === "apify"; $("#sc-engine-scrapling").checked = d.engine !== "apify";
  const projs = [...SC_PROJECTS, ...(d.project && !SC_PROJECTS.includes(d.project) ? [d.project] : [])];
  $("#sc-project").innerHTML = `<option value="">${esc(L("No project", "بدون مشروع"))}</option>` + projs.map((p) => `<option value="${esc(p)}">${esc(scProjName(p))}</option>`).join("");
  $("#sc-project").value = d.project || "";
  const outs = outletOptions(d.project || scProj);
  $("#sc-outlet").innerHTML = `<option value="">${esc(L("Select an outlet", "اختر منفذاً"))}</option>` + outs.map(([c, n]) => `<option value="${esc(c)}">${esc(n)}</option>`).join("") + (d.outlet && !outs.some(([c]) => c === d.outlet) ? `<option value="${esc(d.outlet)}">${esc(d.outlet)}</option>` : "");
  $("#sc-outlet").value = d.outlet || "";
  $("#sc-map").value = d.map_name || ""; $("#sc-map").readOnly = scId !== null;
  $("#sc-map-hint").innerHTML = scMapHint(scId === null ? "new" : "edit");
  $("#sc-browser").value = d.browser_type === "chromium" ? "chromium" : "http";
  $("#sc-wait").value = SC_WAIT_APIFY[d.wait_until] ? d.wait_until : "load";
  $("#sc-link").value = d.link_selector || "";
  $("#sc-urls").value = (d.target_urls || []).join("\n");
  $("#sc-list-script").value = d.list_script || ""; $("#sc-details-script").value = d.details_script || "";
  $("#sc-target").value = String(d.target_items ?? 0);
  $("#sc-active").checked = d.active !== false;
  $("#sc-auto").checked = !!d.auto?.enabled; $("#sc-run-at").value = d.auto?.run_at || "06:30";
  const tzs = [...SC_TZ, ...(d.auto?.tz && !SC_TZ.includes(d.auto.tz) ? [d.auto.tz] : [])];
  $("#sc-tz").innerHTML = tzs.map((t) => `<option value="${esc(t)}">${esc(tzLabel(t))}</option>`).join("");
  $("#sc-tz").value = d.auto?.tz || "Asia/Dubai";
  $("#sc-actor").value = d.apify?.actor_id || ""; $("#sc-input").value = d.apify?.input || "";
  $("#sc-payload").value = d.payload || "";
}
function scCollect() {
  const v = (s) => $(s).value, tgt = v("#sc-target").trim();
  return { ...scDraft, name: v("#sc-name").trim(), engine: $("#sc-engine-apify").checked ? "apify" : "scrapling", project: v("#sc-project"), outlet: v("#sc-outlet"),
    map_name: v("#sc-map").trim(), browser_type: v("#sc-browser"), wait_until: v("#sc-wait"), link_selector: v("#sc-link").trim(),
    target_urls: v("#sc-urls").split(/\r?\n/).map((x) => x.trim()).filter(Boolean),
    list_script: v("#sc-list-script").replace(/\s+$/, ""), details_script: v("#sc-details-script").replace(/\s+$/, ""),
    target_items: tgt === "" ? 0 : /^\d+$/.test(tgt) ? parseInt(tgt, 10) : NaN, active: $("#sc-active").checked,
    auto: { enabled: $("#sc-auto").checked, run_at: v("#sc-run-at"), tz: v("#sc-tz") }, payload: v("#sc-payload"),
    apify: { actor_id: v("#sc-actor").trim(), input: v("#sc-input").trim() } };
}
const AsyncFn = Object.getPrototypeOf(async function () {}).constructor;
// syntax check of a script body (it is never run here); a page that forbids eval just skips the check
function jsSyntax(src) { if (!String(src || "").trim()) return ""; try { new AsyncFn(src); return ""; } catch (e) { return e instanceof SyntaxError ? e.message : ""; } }
function isHttpUrl(u) { try { const x = new URL(u); return (x.protocol === "http:" || x.protocol === "https:") && !!x.hostname && !/\s/.test(u); } catch (e) { return false; } }
function scValidate(d) {
  const e = {};
  if (!d.name) e["sc-name"] = L("Write a label for the scraper.", "اكتب اسماً للكاشطة.");
  if (!d.map_name) e["sc-map"] = L("Write a unique English name, such as carrefour_milk.", "اكتب اسماً فريداً بالإنجليزية، مثل carrefour_milk.");
  else if (/^[A-Za-z0-9_-]+$/.test(d.map_name) && /[A-Z]/.test(d.map_name)) e["sc-map"] = L(`Use lowercase letters only: ${d.map_name.toLowerCase()}`, `استخدم أحرفاً صغيرة فقط: ${d.map_name.toLowerCase()}`);
  else if (!/^[a-z0-9_-]+$/.test(d.map_name)) e["sc-map"] = L("Lowercase English letters (a-z), digits, _ and - only, no spaces.", "أحرف إنجليزية صغيرة (a-z) وأرقام و _ و - فقط، بدون مسافات.");
  else if (d.map_name === "new") e["sc-map"] = L("“new” is reserved for the create page address; choose another name.", "«new» محجوز لعنوان صفحة الإنشاء؛ اختر اسماً آخر.");
  else if (scId === null && scrapers[d.map_name]) e["sc-map"] = L(`“${d.map_name}” is used by another scraper (“${scrapers[d.map_name].name || d.map_name}”). Choose another name.`, `«${d.map_name}» مستخدم لكاشطة أخرى («${scrapers[d.map_name].name || d.map_name}»). اختر اسماً آخر.`);
  const bad = $("#sc-urls").value.split(/\r?\n/).map((u, i) => [u.trim(), i + 1]).filter(([u]) => u && !isHttpUrl(u));
  if (bad.length) e["sc-urls"] = L(`Line${bad.length === 1 ? "" : "s"} ${bad.slice(0, 3).map(([, n]) => n).join(", ")}${bad.length > 3 ? "…" : ""}: not a valid http or https URL: ${bad[0][0].slice(0, 60)}`, `${bad.length === 1 ? "السطر" : "الأسطر"} ${bad.slice(0, 3).map(([, n]) => n).join("، ")}${bad.length > 3 ? "…" : ""} ليس رابط http أو https صحيحاً: ${bad[0][0].slice(0, 60)}`);
  else if (!d.target_urls.length) e["sc-urls"] = L("Add at least one URL, one per line.", "أضف رابطاً واحداً على الأقل، رابطاً في كل سطر.");
  const ls = jsSyntax(d.list_script), ds = jsSyntax(d.details_script);
  if (ls) e["sc-list-script"] = L("JavaScript syntax error: ", "خطأ في صياغة JavaScript: ") + ls;
  if (ds) e["sc-details-script"] = L("JavaScript syntax error: ", "خطأ في صياغة JavaScript: ") + ds;
  const ownInput = d.engine === "apify" && d.apify.input;
  if (!ls && !ownInput && !d.list_script.trim() && !d.link_selector && !d.details_script.trim())
    e["sc-list-script"] = L("Write a list script, a link selector, or a details script on its own, so that data is extracted.", "اكتب سكربت القائمة، أو محدد روابط المنتجات، أو سكربت التفاصيل وحده، حتى تُستخرج بيانات.");
  if (!Number.isInteger(d.target_items) || d.target_items < 0) e["sc-target"] = L("A whole number, 0 or more (0 = no limit).", "رقم صحيح 0 أو أكبر (0 = بلا حد).");
  else if (d.target_items > 1000000) e["sc-target"] = L("The largest allowed value is 1,000,000.", "أكبر عدد مسموح 1,000,000.");
  if (d.auto.enabled && !/^([01]\d|2[0-3]):[0-5]\d$/.test(d.auto.run_at)) e["sc-run-at"] = L("Choose the daily run time (hh:mm).", "اختر وقت التشغيل اليومي (ساعة:دقيقة).");
  if (d.engine === "apify") {
    if (!d.apify.actor_id) e["sc-actor"] = L("An Actor ID is needed for Apify, e.g. apify/web-scraper.", "Actor ID مطلوب لمحرك Apify، مثل apify/web-scraper.");
    else if (!/^[\w.-]+[/~][\w.-]+$/.test(d.apify.actor_id)) e["sc-actor"] = L("Write it as username/actor-name or username~actor-name.", "اكتبه بصيغة username/actor-name أو username~actor-name.");
    if (d.apify.input) {
      try { const v = JSON.parse(d.apify.input); if (!v || typeof v !== "object" || Array.isArray(v)) e["sc-input"] = L("It must be a JSON object in { }.", "يجب أن يكون كائن JSON بين { }."); }
      catch (x) { e["sc-input"] = L("Not valid JSON: ", "ليس JSON صحيحاً: ") + x.message; }
    }
  }
  return e;
}
function scRenderErrors(errs) {
  for (const id of SC_FIELDS) {
    const msg = scShowAll || scTouched.has(id) ? errs[id] || "" : "";
    const box = document.getElementById(id + "-err"); if (!box) continue;
    box.textContent = msg; box.hidden = !msg;
    const el = id === "sc-engine" ? null : document.getElementById(id);
    if (el) { if (msg) el.setAttribute("aria-invalid", "true"); else el.removeAttribute("aria-invalid"); }
  }
}
// everything that follows the form's values: errors, dirty state, engine/browser/auto dependent parts, save bar, summary
function scSync() {
  if (!scRoute || scRoute === "list") return;
  const d = scCollect(), errs = scValidate(d), n = Object.keys(errs).length;
  scDirty = scKey(d) !== scBase;
  scRenderErrors(errs);
  $("#sc-apify-sec").hidden = d.engine !== "apify";
  $("#sc-wait").disabled = d.browser_type !== "chromium";
  $("#sc-browser-apify").hidden = d.engine !== "apify";
  $("#sc-run-at").disabled = $("#sc-tz").disabled = true;
  $("#sc-auto-hint").textContent = scAutoHint();
  if ($("#sc-preview-box").open && d.engine === "apify") scPreview(d);
  const st = $("#sc-save-state");
  if (scShowAll && n) { st.textContent = n === 1 ? L("One field needs correcting before saving", "حقل واحد يحتاج تصحيحاً قبل الحفظ") : L(`${n} fields need correcting before saving`, `${n} حقول تحتاج تصحيحاً قبل الحفظ`); st.className = "state bad"; }
  else if (scId === null) { st.textContent = scDirty ? L("New scraper: not saved yet", "كاشطة جديدة: لم تُحفظ بعد") : L("Fill the required fields (*), then save", "املأ الحقول المطلوبة (*) ثم احفظ"); st.className = "state" + (scDirty ? " dirty" : ""); }
  else { st.textContent = scDirty ? L("Unsaved changes", "تعديلات غير محفوظة") : L("All changes saved", "كل التعديلات محفوظة"); st.className = "state " + (scDirty ? "dirty" : "ok"); }
  $("#sc-save").disabled = scId !== null && !scDirty;
  const top = $("#sc-save-top"); top.setAttribute("aria-disabled", String(!scDirty)); top.className = scDirty ? "primary" : "secondary";   // pale until the form is dirty (new or saved scraper)
  $("#sc-banner").hidden = !(scShowAll && n); $("#sc-banner-msg").textContent = st.textContent;
  // nothing to save on a saved scraper: the bar stays at the end of the form instead of floating over it
  $("#sc-savebar").classList.toggle("idle", scId !== null && !scDirty && !(scShowAll && n));
  if (scId === null) $("#sc-title").textContent = d.name || L("New scraper", "كاشطة جديدة");
  if (!scDirty) { $("#sc-leave-confirm").hidden = true; $("#sc-leave-confirm").innerHTML = ""; }
  scRenderSummary(d);
}
function scAfterFill() {
  scTouched.clear(); scShowAll = false;
  $("#sc-leave-confirm").hidden = true; $("#sc-leave-confirm").innerHTML = ""; $("#sc-preview-box").open = false;
  scSync();
}
function scOpenForm(draft) {
  scId = null; scDraft = scNorm(scBlank()); scHead("new");
  scFillForm(scDraft); scBase = scKey(scCollect());
  if (draft) { scDraft = scNorm(draft); scFillForm(scDraft); }
  scMapEdited = !!draft;
  scAfterFill();
  try { $("#sc-name").focus({ preventScroll: true }); } catch (e) {}
}
async function scOpenScraper(id, tab) {
  let s = scrapers[id];
  if (!s) {          // created by the routine or another viewer since the list was read
    try { const snap = await db.doc(`scrapers/${id}`).get(); if (snap.exists) s = scrapers[id] = scNorm(plain(snap)); } catch (e) {}
    if (scRoute !== id) return;
  }
  if (!s) {
    $("#sc-title").textContent = L("Scraper workspace", "مساحة عمل الكاشطة"); $("#sc-save-top").hidden = true;
    $("#sc-banner").hidden = false; $("#sc-banner-msg").textContent = L(`The requested scraper route is invalid: no scraper named “${id}”.`, `عنوان الكاشطة المطلوب غير صالح: لا توجد كاشطة باسم «${id}».`);
    $("#sc-setup").hidden = true; $("#sc-runs").hidden = true; $("#sc-tabs-box").hidden = true; $("#sc-run-now").hidden = true;
    return;
  }
  scId = id; scDraft = scNorm(s); scHead("edit", s);
  scFillForm(scDraft); scBase = scKey(scCollect()); scMapEdited = true;
  scAfterFill();
  $("#sc-run-view").hidden = true; scShownRun = null; scShownRows = []; $("#sc-run-q").value = "";
  scSwitchTab(tab || "setup"); scRenderPending(); scRenderJob(); scLoadRuns();
}
const scSlug = (s) => String(s).toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 40);
$("#sc-form").addEventListener("input", (e) => {
  if (e.target.id === "sc-name" && scId === null && !scMapEdited) $("#sc-map").value = scSlug(e.target.value);
  if (e.target.id === "sc-map") scMapEdited = !!e.target.value;
  scSync();
});
$("#sc-form").addEventListener("change", scSync);
// an error shows once the field was left with something in it, or after a save attempt
$("#sc-form").addEventListener("focusout", (e) => {
  const id = e.target.name === "sc-engine" ? "sc-engine" : e.target.id;
  if (SC_FIELDS.includes(id) && String(e.target.value || "").trim()) { scTouched.add(id); scSync(); }
});
$("#sc-form").addEventListener("submit", (e) => { e.preventDefault(); scSave(); });
$("#sc-preview-box").addEventListener("toggle", () => { if ($("#sc-preview-box").open) scPreview(scCollect()); });
$("#sc-cancel").addEventListener("click", () => go("#" + scHash("list")));
$("#sc-back").addEventListener("click", () => go("#" + scHash("list")));
$("#sc-save-top").addEventListener("click", () => { if ($("#sc-save-top").getAttribute("aria-disabled") === "true") return toast(scId === null ? L("Fill the required fields (*), then save", "املأ الحقول المطلوبة (*) ثم احفظ") : L("Nothing to save yet", "لا تعديلات للحفظ")); scSave(); });
$("#sc-run-now").addEventListener("click", () => scRunNow(scId, $("#sc-head-confirm")));
$("#sc-tabs").addEventListener("click", (e) => { const b = e.target.closest("[data-sctab]"); if (b) scSwitchTab(b.dataset.sctab); });
$("#sc-dup").addEventListener("click", () => scDuplicate(scId));
$("#sc-del").addEventListener("click", () => scAskDelete(scId, $("#sc-del-confirm")));

async function scSave() {
  const d = scCollect(), errs = scValidate(d);
  scShowAll = true; scSync();
  const first = SC_FIELDS.find((id) => errs[id]);
  if (first) {
    const el = first === "sc-engine" ? $("#sc-engine-scrapling") : document.getElementById(first);
    if (el) { el.focus({ preventScroll: true }); el.scrollIntoView({ block: "center", behavior: scMotion() }); }
    return;
  }
  const isNew = scId === null, id = isNew ? d.map_name : scId, btn = $("#sc-save");
  btn.disabled = true; btn.textContent = L("Saving…", "يُحفظ…");
  try {
    const ref = db.doc(`scrapers/${id}`), snap = await ref.get();
    if (isNew && snap.exists) {          // created meanwhile (another tab or viewer): the name is taken
      scrapers[id] = scNorm(plain(snap)); scSync(); $("#sc-map").focus(); return;
    }
    const prev = snap.exists ? plain(snap) : {}, now = new Date().toISOString();
    // run state is owned by the runs and the routine: keep what the database has
    const doc = { ...prev, ...scStored(d), map_name: id, run_request: prev.run_request ?? null, last_run: prev.last_run ?? null,
      last_scraped: prev.last_scraped ?? 0, created_at: prev.created_at || now, updated_at: now };
    await ref.set(doc);
    scrapers[id] = scNorm(doc); scDirty = false;
    toast(isNew ? L(`Scraper “${d.name}” created`, `أُنشئت الكاشطة «${d.name}»`) : L("Scraper saved", "حُفظت الكاشطة"));
    if (isNew) { scRoute = id; try { history.replaceState(null, "", "#" + scHash(id)); routeKey = scHash(id); } catch (e) {} scOpenScraper(id); }
    else { scDraft = scNorm(doc); scBase = scKey(scCollect()); scShowAll = false; scTouched.clear(); scHead("edit", scrapers[id]); scRenderPending(); }
  } catch (e) { toast(dbErr(e), true); }
  finally { btn.textContent = L("Save scraper", "حفظ الكاشطة"); btn.disabled = false; scSync(); }
}
function scDuplicate(id) {
  const s = scrapers[id]; if (!s) return;
  let m = `${id}_copy`.slice(0, 64), k = 2;
  while (scrapers[m]) m = `${id}_copy${k++}`.slice(-64);
  const draft = { ...scNorm(s), name: `${s.name || id} (${L("copy", "نسخة")})`, map_name: m, run_request: null, last_run: null, last_scraped: 0, created_at: null, updated_at: null };
  pendingDraft = draft; go("#" + scHash("new")); toast(L("An unsaved copy: check the label and unique name, then save", "نسخة لم تُحفظ بعد: راجع الاسم والاسم الفريد ثم احفظ"));
}
async function scDeleteRunDocs(sid, rid) {
  for (const d of (await db.collection(`scrapers/${sid}/runs/${rid}/rows`).get()).docs) await db.doc(`scrapers/${sid}/runs/${rid}/rows/${d.id}`).delete();
  await db.doc(`scrapers/${sid}/runs/${rid}`).delete();
}
function scAskDelete(id, box) {
  const s = scrapers[id]; if (!s) return;
  if (scJob?.running && scJob.sid === id) return toast(L("The scraper is running; stop the run first, then delete it", "الكاشطة تعمل الآن؛ أوقف التشغيل أولاً ثم احذفها"), true);
  askInline(box, esc(L(`Delete the scraper “${s.name || id}” for good, with all its runs and results?`, `حذف الكاشطة «${s.name || id}» نهائياً مع كل تشغيلاتها ونتائجها؟`)), L("Delete scraper", "حذف الكاشطة"), async () => {
    try {
      for (const r of (await db.collection(`scrapers/${id}/runs`).get()).docs) await scDeleteRunDocs(id, r.id);
      await db.doc(`scrapers/${id}`).delete(); delete scrapers[id];
      toast(L(`Scraper “${s.name || id}” deleted`, `حُذفت الكاشطة «${s.name || id}»`));
      if (scRoute === id) { scDirty = false; go("#" + scHash("list")); } else if (scRoute === "list") scRenderList();
    } catch (e) { toast(dbErr(e), true); }
  }, true);
}

// ---------------- side summary (like the platform's card)
function scRenderSummary(d) {
  const s = scId ? scrapers[scId] : null, lr = s?.last_run;
  const row = (t, val) => `<div><dt>${esc(t)}</dt><dd>${val}</dd></div>`;
  $("#sc-sum").innerHTML = [
    row(L("Status", "الحالة"), (d.active ? `<span class="chip ok">${esc(L("Active", "مفعّلة"))}</span>` : `<span class="chip grey">${esc(L("Inactive", "متوقفة"))}</span>`) + scEngineChip(d.engine)),
    row(L("Auto Trigger", "التشغيل التلقائي"), `<span class="chip grey">${esc(L("Off: runs on demand", "متوقف: يعمل عند الطلب"))}</span>`),
    row(L("Auto Trigger Time", "وقت التشغيل التلقائي"), "—"),
    row(L("Auto Trigger TZ", "منطقة التشغيل التلقائي"), "—"),
    row(L("Last Scraped", "آخر سحب"), s ? `${esc((s.last_scraped ?? 0).toLocaleString("en"))} ${esc(L("items", "عنصر"))}` : "—"),
    row(L("Last Run", "آخر تشغيل"), lr ? `<span class="chip ${lr.status === "done" ? "ok" : lr.status === "error" ? "bad" : "warn"}">${esc(scStatus(lr.status))}</span> ${esc(fmtWhen(lr.at))}${lr.items != null ? ` · ${esc(lr.items)} ${esc(L("items", "عنصر"))}` : ""}` : "—"),
    row(L("Created At", "تاريخ الإنشاء"), s?.created_at ? esc(fmtWhen(s.created_at)) : "—"),
    ...(s && s.engine === "scrapling" && scPending(s) ? [row(L("Run request", "طلب تشغيل"), `<span class="chip warn">${esc(L("Waiting", "في الانتظار"))}</span> ${esc(fmtWhen(s.run_request.at))}`)] : []),
  ].join("");
  $("#sc-sum-note").textContent = s ? (s.updated_at ? L(`Last edited ${fmtWhen(s.updated_at)}`, `آخر تعديل ${fmtWhen(s.updated_at)}`) : "") : L("Run data appears here after saving and the first run.", "تظهر بيانات التشغيل هنا بعد الحفظ وأول تشغيل.");
}

// ---------------- run now
function scRunNow(id, box) {
  const s = scrapers[id]; if (!s) return;
  if (scRoute === id && scDirty) return toast(L("Save the scraper changes first; the run uses the saved version", "احفظ تعديلات الكاشطة أولاً؛ التشغيل يستخدم النسخة المحفوظة"), true);
  if (!s.active) return toast(L("The scraper is inactive. Turn it on under Behavior, save, then run it.", "الكاشطة متوقفة. فعّلها من قسم «السلوك» واحفظ، ثم شغّلها."), true);
  const name = esc(s.name || id);
  if (s.engine === "apify") {
    if (!mcp) return toast(L("Apify is not available in this view; open the page in claude.ai with the Apify connector", "Apify غير متاح في هذا العرض؛ افتح الصفحة داخل claude.ai مع موصل Apify"), true);
    if (scJob?.running) return toast(scJob.sid === id ? L("This scraper is running now", "هذه الكاشطة تعمل الآن") : L(`The scraper “${scrapers[scJob.sid]?.name || scJob.sid}” is running; wait until it ends`, `الكاشطة «${scrapers[scJob.sid]?.name || scJob.sid}» تعمل الآن؛ انتظر حتى تنتهي`), true);
    askInline(box, L(`Run “${name}” now on Apify (<code>${esc(s.apify.actor_id)}</code>)? It uses Apify credit; keep the page open until it ends.`, `تشغيل «${name}» الآن عبر Apify (<code>${esc(s.apify.actor_id)}</code>)؟ يستهلك رصيد Apify، وأبقِ الصفحة مفتوحة حتى ينتهي.`), L("Run", "شغّل"),
      async () => { if (await scGo(id, { tab: "runs" })) scStartApify(id); });
  } else {
    if (scPending(s)) { toast(L("A run request is already waiting for the routine", "طلب التشغيل موجود وينتظر المهمة المجدولة")); if (scRoute === id) scSwitchTab("runs"); return; }
    askInline(box, L(`Request a run of “${name}” now on Claude's servers (Scrapling)? The routine runs it and saves the result here.`, `طلب تشغيل «${name}» الآن على خوادم Claude (Scrapling)؟ تنفّذه المهمة المجدولة وتحفظ النتيجة هنا.`), L("Request the run", "اطلب التشغيل"), () => scRequestRun(id));
  }
}
async function scRequestRun(id) {
  const at = new Date().toISOString();
  try { await db.doc(`scrapers/${id}`).update({ run_request: { at } }); scrapers[id] = { ...scrapers[id], run_request: { at } }; }
  catch (e) { return toast(dbErr(e), true); }
  let fired = false;
  if (mcp) {
    try {
      const r = await db.doc("system/scrapers_routine").get(), tid = r.exists ? plain(r).trigger_id : "";
      if (tid) { await ccr("fire_trigger", { trigger_id: tid }); fired = true; scFired[id] = at; }
    } catch (e) { /* the request stays on the document; the routine picks it up on its next hourly run */ }
  }
  toast(fired ? L("The run started on Claude's servers; the result appears under Runs when it ends", "بدأ التشغيل الآن على خوادم Claude؛ تظهر النتيجة في «التشغيلات» عند انتهائه") : L("The request is saved, but the run could not start now; press Run now again", "الطلب محفوظ، لكن تعذّر بدء التشغيل الآن؛ اضغط «شغّل الآن» مرة أخرى"));
  scAfterRunChange(id);
  if (scRoute === id) scSwitchTab("runs");
}
function scAfterRunChange(id) {
  if (scRoute === "list") scRenderList();
  else if (scRoute === id) { scRenderPending(); scRenderSummary(scCollect()); }
}
function scRenderPending() {
  const s = scId && scrapers[scId], box = $("#sc-pending");
  if (!s || s.engine !== "scrapling" || !scPending(s)) { box.hidden = true; box.innerHTML = ""; return; }
  const fired = scFired[scId] === s.run_request.at;
  box.hidden = false;
  box.innerHTML = `<div class="notice wait" role="status"><b>${fired ? esc(L("The run started on Claude's servers", "بدأ التشغيل على خوادم Claude")) : esc(L("The request is saved, but the run could not start now", "الطلب محفوظ، لكن تعذّر بدء التشغيل الآن"))}</b>
    <span>${esc(L(`Requested ${fmtWhen(s.run_request.at)}. The result appears under Runs below when it ends.`, `طُلب التشغيل ${fmtWhen(s.run_request.at)}. تظهر النتيجة في «التشغيلات» أدناه عند انتهائه.`))}</span>
    <div class="row"><button type="button" data-act="refresh">${esc(L("Refresh status", "تحديث الحالة"))}</button><button type="button" class="danger" data-act="cancel">${esc(L("Cancel the request", "إلغاء الطلب"))}</button></div></div>`;
}
$("#sc-pending").addEventListener("click", async (e) => {
  const b = e.target.closest("[data-act]"); if (!b || !scId) return;
  const id = scId;
  if (b.dataset.act === "refresh") {
    try { const snap = await db.doc(`scrapers/${id}`).get(); if (snap.exists) scrapers[id] = scNorm(plain(snap)); } catch (x) { return toast(dbErr(x), true); }
    if (scRoute === id) { scAfterRunChange(id); scLoadRuns(); }
  } else if (b.dataset.act === "cancel") {
    try { await db.doc(`scrapers/${id}`).update({ run_request: null }); scrapers[id] = { ...scrapers[id], run_request: null }; toast(L("Run request cancelled", "أُلغي طلب التشغيل")); }
    catch (x) { return toast(dbErr(x), true); }
    scAfterRunChange(id);
  }
});

// Apify input: the scraper's own Input JSON, or web-scraper style input built from its fields
function scApifyInput(s) {
  if (String(s.apify?.input || "").trim()) {
    const v = JSON.parse(s.apify.input);
    if (!v || typeof v !== "object" || Array.isArray(v)) throw new Error(L("The input must be a JSON object", "الإدخال يجب أن يكون كائن JSON"));
    return v;
  }
  const n = Math.max(0, parseInt(s.target_items, 10) || 0), urls = s.target_urls || [];
  // listing pages plus up to n detail pages; results are also capped at n
  // no proxy and one request at a time, like the Scrapling engine
  const input = { startUrls: urls.map((url) => ({ url })), pageFunction: scPageFunction(s), injectJQuery: false,
    proxyConfiguration: { useApifyProxy: false }, maxConcurrency: 1, maxPagesPerCrawl: n ? n + urls.length : 0 };
  if (n) input.maxResultsPerCrawl = n;
  if (s.browser_type === "chromium") input.waitUntil = [SC_WAIT_APIFY[s.wait_until] || "load"];
  return input;
}
/* the scripts run as function bodies in each page, with the same rules as scripts/custom_scrape.py: a list item's url is
   opened as a detail page when there is a details script; when the list gives no url, the links matched by the link
   selector are detail pages (with a details script) or items {url} (without one); with only a details script, each
   target URL is one item */
function scPageFunction(s) {
  const lst = String(s.list_script || "").trim(), list = lst || "return [];", det = String(s.details_script || "").trim();
  return [
    "async function pageFunction(context) {",
    "  // built by the price portal from the scraper's List Script, Details Script and Link Selector",
    "  const { request, log } = context;",
    "  const listScript = async () => {", list, "  };",
    "  const detailsScript = async () => {", det || "return {};", "  };",
    `  const hasDetails = ${det ? "true" : "false"};`,
    `  const linkSelector = ${JSON.stringify(s.link_selector || "")};`,
    `  const hasList = ${lst ? "true" : "false"};`,
    "  if (request.userData && request.userData.label === \"DETAIL\") {",
    "    let extra = {};",
    "    try { extra = (await detailsScript()) || {}; } catch (e) { log.warning(\"details script failed on \" + request.url + \": \" + e.message); }",
    "    return Object.assign({}, request.userData.item || {}, extra, { source_url: request.url });",
    "  }",
    "  if (!hasList && !linkSelector) {   // only a details script: the target page is the item",
    "    let one = {};",
    "    try { one = (await detailsScript()) || {}; } catch (e) { log.warning(\"details script failed on \" + request.url + \": \" + e.message); }",
    "    return [Object.assign({}, one, { source_url: request.url })];",
    "  }",
    "  let items = [];",
    "  try { const out = await listScript(); items = Array.isArray(out) ? out : []; } catch (e) { log.warning(\"list script failed on \" + request.url + \": \" + e.message); }",
    "  const rows = [];",
    "  for (const it of items) {",
    "    if (hasDetails && it && it.url) await context.enqueueRequest({ url: new URL(it.url, request.url).href, userData: { label: \"DETAIL\", item: it } });",
    "    else rows.push(Object.assign({}, it, { source_url: request.url }));",
    "  }",
    "  if (linkSelector && !items.some((it) => it && it.url)) {",
    "    // one row per product page, as the Scrapling engine: no #fragment, no duplicates (image and title links)",
    "    const links = [...new Set([...document.querySelectorAll(linkSelector)].map((a) => String(a.href || \"\").split(\"#\")[0]).filter((h) => /^https?:/.test(h)))];",
    "    for (const href of links) {",
    "      if (hasDetails) await context.enqueueRequest({ url: href, userData: { label: \"DETAIL\", item: { url: href } } });",
    "      else rows.push({ url: href, source_url: request.url });",
    "    }",
    "  }",
    "  return rows;",
    "}",
  ].join("\n");
}
function scPreview(d) {
  const box = $("#sc-preview");
  try {
    const input = { ...scApifyInput(d) }, pf = input.pageFunction;
    if (pf) input.pageFunction = "(see below)";
    box.textContent = JSON.stringify(input, null, 2) + (pf ? "\n\n// pageFunction\n" + pf : "");
  } catch (e) { box.textContent = L("The input is not valid JSON: ", "الإدخال المكتوب ليس JSON صحيحاً: ") + e.message; }
}

function scLog(m) { if (!scJob) return; scJob.log.push(`${new Date().toLocaleTimeString("en-GB")}  ${m}`); scRenderJob(); }
function scRenderJob() {
  const box = $("#sc-job");
  if (!scJob || scJob.sid !== scId) { box.hidden = true; return; }
  box.hidden = false;
  const st = scJob.running ? [L("Running", "يعمل"), "warn"] : scJob.status === "done" ? [L("Completed", "انتهى"), "ok"] : scJob.stopped ? [L("Stopped", "أُوقف"), "warn"] : [L("Failed", "خطأ"), "bad"];
  $("#sc-job-state").textContent = st[0]; $("#sc-job-state").className = "chip " + st[1];
  $("#sc-job-steps").innerHTML = scSteps().map((t, i) => `<li class="${i < scJob.phase ? "done" : i === scJob.phase && scJob.running ? "on" : ""}">${i < scJob.phase ? "✓ " : ""}${esc(t)}${i === 2 && scJob.items ? ` (${esc(scJob.items)})` : ""}</li>`).join("");
  const pct = scJob.status === "done" && !scJob.running ? 100 : Math.round(((scJob.phase + (scJob.running ? 0.5 : 0)) / scSteps().length) * 100);
  $("#sc-job-bar i").style.width = pct + "%"; $("#sc-job-bar").setAttribute("aria-valuenow", String(pct));
  const l = $("#sc-job-log"); l.textContent = scJob.log.join("\n"); l.scrollTop = l.scrollHeight;
  $("#sc-job-stop").disabled = !scJob.running || scJob.stop; $("#sc-job-stop").hidden = !scJob.running;
}
async function scStartApify(id) {
  const s = scrapers[id];
  let input; try { input = scApifyInput(s); } catch (e) { return toast(L("Apify input: ", "إدخال Apify: ") + e.message, true); }
  const runId = new Date().toISOString().replace(/[-:]/g, "").slice(0, 13) + "-" + Math.random().toString(36).slice(2, 6);
  const startedAt = new Date().toISOString();
  scJob = { sid: id, runId, running: true, stop: false, stopped: false, status: "running", phase: 0, items: 0, apifyRun: "", lastStatus: "", log: [] };
  scLog(`${s.name}: ${s.apify.actor_id}, ${s.target_urls.length} start URL(s)${s.apify.input ? ", own input JSON" : ""}`);
  let rows = [], status = "done";
  try {
    const res = await runActor({ actor: s.apify.actor_id }, input, () => scJob.stop, (what, rid, x) => {
      if (what === "started") { scJob.apifyRun = rid; scJob.phase = 1; scLog(`Apify run ${rid} ${x || ""}`); }
      else if (what === "status") { if (x !== scJob.lastStatus) { scJob.lastStatus = x; scLog(`status ${x}`); } }
      else if (what === "items") { scJob.phase = 2; scJob.items = x; scRenderJob(); }
    });
    const at = new Date().toISOString();
    rows = res.items.map((it) => (it && typeof it === "object" ? { ...it, source_url: it.source_url ?? it.url ?? "", scraped_at: it.scraped_at || at } : { value: it, source_url: "", scraped_at: at }));
    if (s.target_items > 0 && rows.length > s.target_items) { scLog(`kept the first ${s.target_items} of ${rows.length} items (Target Items)`); rows = rows.slice(0, s.target_items); }
    scLog(`${rows.length} items`);
  } catch (e) {
    status = "error";
    if (scJob.stop) { scJob.stopped = true; scLog("stopped"); } else scLog("ERROR: " + mcpErr(e));
  }
  scJob.phase = 3; scRenderJob();
  try {
    const n = await saveChunks(`scrapers/${id}/runs/${runId}/rows`, "rows", rows, []);
    await db.doc(`scrapers/${id}/runs/${runId}`).set({ startedAt, finishedAt: new Date().toISOString(), status, count: rows.length, chunks: n, log: scJob.log.slice(-200),
      engine: "apify", actor_id: s.apify.actor_id, apify_run_id: scJob.apifyRun || null, ...(scJob.stopped ? { stopped: true } : {}) });
    const last_run = { at: startedAt, status, items: rows.length, run_id: runId };
    const patch = status === "done" ? { last_run, last_scraped: rows.length } : { last_run };
    await db.doc(`scrapers/${id}`).update(patch);
    scrapers[id] = { ...scrapers[id], ...patch };
    scLog(`saved run ${runId}`);
    toast(status === "done" ? L(`The run ended; ${rows.length.toLocaleString("en")} items saved`, `انتهى التشغيل وحُفظ ${rows.length.toLocaleString("en")} عنصر`) : scJob.stopped ? L("The run was stopped; its log is saved", "أُوقف التشغيل وحُفظ سجله") : L("The run ended with an error; its log is under Runs", "انتهى التشغيل بخطأ؛ السجل محفوظ في «التشغيلات»"), status === "error" && !scJob.stopped);
  } catch (e) { scLog("could not save the run: " + dbErr(e)); toast(dbErr(e), true); }
  scJob.status = status; scJob.running = false; if (status === "done") scJob.phase = scSteps().length; scRenderJob();
  if (scRoute === id) { scRenderSummary(scCollect()); scLoadRuns(runId); } else if (scRoute === "list") scRenderList();
}
$("#sc-job-stop").addEventListener("click", async () => {
  if (!scJob?.running) return;
  scJob.stop = true; scLog("stop requested: the page stops following the run");
  if (scJob.apifyRun) try { await apify("abort-actor-run", { runId: scJob.apifyRun }); scLog(`abort sent to Apify for ${scJob.apifyRun}`); } catch (e) { scLog("abort on Apify failed: " + mcpErr(e)); }
});

// ---------------- runs and their rows
async function scRowsOf(sid, run) {
  const base = `scrapers/${sid}/runs/${run.id}/rows`, out = [];
  if (Number.isInteger(run.chunks) && run.chunks > 0) {
    for (let i = 0; i < run.chunks; i++) { const snap = await db.doc(`${base}/c${String(i).padStart(3, "0")}`).get(); if (snap.exists) out.push(...(plain(snap).rows || [])); }
    if (out.length) return out;
  }
  for (const d of [...(await db.collection(base).limit(200).get()).docs].sort((a, b) => a.id.localeCompare(b.id))) out.push(...(plain(d).rows || []));
  return out;
}
async function scLoadRuns(openId) {
  const sid = scId; if (!sid) return;
  $("#sc-run-list").innerHTML = `<div class="loading">${esc(L("Loading runs…", "تُحمَّل التشغيلات…"))}</div>`;
  try { scRuns = (await db.collection(`scrapers/${sid}/runs`).orderBy("startedAt", "desc").limit(50).get()).docs.map((d) => ({ id: d.id, ...plain(d) })); }
  catch (e) { if (scId === sid) $("#sc-run-list").innerHTML = errBox(L("Unable to load the runs right now. ", "تعذّر تحميل التشغيلات الآن. ") + dbErr(e)); return; }
  if (scId !== sid) return;
  $("#sc-export-all").disabled = !scRuns.length;
  $("#sc-run-list").innerHTML = scRuns.length ? `<div class="tw"><table><thead><tr><th>${esc(L("Started", "البداية"))}</th><th>${esc(L("Type", "النوع"))}</th><th>${esc(L("Status", "الحالة"))}</th><th class="num">${esc(L("Items", "العناصر"))}</th><th>${esc(L("Duration", "المدة"))}</th><th></th></tr></thead><tbody>${scRuns.map((r) => {
    const st = r.status === "done" ? [L("Completed", "انتهى"), "ok"] : r.status === "running" ? [L("Running", "يعمل"), "warn"] : r.stopped ? [L("Stopped", "أُوقف"), "warn"] : [L("Failed", "خطأ"), "bad"];
    return `<tr><td>${esc(fmtWhen(r.startedAt))}</td><td>${scEngineChip(r.engine)}</td><td><span class="chip ${st[1]}">${st[0]}</span></td><td class="num"><b>${esc((r.count ?? 0).toLocaleString("en"))}</b></td><td>${esc(scDur(r))}</td><td><button class="ghost" type="button" data-scrun="${esc(r.id)}">${esc(L("View", "عرض"))}</button></td></tr>`;
  }).join("")}</tbody></table></div>`
    : `<div class="empty">${esc(L("No runs yet. Press Run now at the top of the page.", "لا توجد تشغيلات بعد. اضغط «شغّل الآن» أعلى الصفحة."))}</div>`;
  if (openId) scShowRun(openId);
  else if (scShownRun && !scRuns.some((r) => r.id === scShownRun.id)) { scShownRun = null; $("#sc-run-view").hidden = true; }
}
$("#sc-run-list").addEventListener("click", (e) => { const b = e.target.closest("[data-scrun]"); if (b) scShowRun(b.dataset.scrun); });
async function scShowRun(id) {
  const sid = scId, run = scRuns.find((r) => r.id === id); if (!run) return;
  scShownRun = run; scShownRows = [];
  $("#sc-run-view").hidden = false; $("#sc-run-confirm").innerHTML = "";
  $("#sc-run-title").textContent = L("Run ", "تشغيل ") + fmtWhen(run.startedAt);
  const st = run.status === "done" ? L("Completed", "انتهى") : run.status === "running" ? L("Running", "يعمل") : run.stopped ? L("Stopped", "أُوقف") : L("Failed", "خطأ");
  $("#sc-run-stats").innerHTML = [[(run.count ?? 0).toLocaleString("en"), L("items", "عنصر")], [st, L("status", "الحالة")], [SC_ENGINE[run.engine] || run.engine || "—", L("type", "النوع")], [scDur(run), L("duration", "المدة")]]
    .map(([v, l]) => `<div class="stat"><b>${esc(v)}</b><span class="muted">${esc(l)}</span></div>`).join("");
  $("#sc-run-log").textContent = (run.log || []).join("\n") || L("No log for this run.", "لا يوجد سجل لهذا التشغيل.");
  $("#sc-run-table thead").innerHTML = ""; $("#sc-run-table tbody").innerHTML = ""; $("#sc-run-more").textContent = L("Reading the items…", "تُحمَّل العناصر…");
  try { scShownRows = await scRowsOf(sid, run); }
  catch (e) { $("#sc-run-more").textContent = ""; return toast(L("Could not read the run items: ", "تعذّر تحميل عناصر التشغيل: ") + dbErr(e), true); }
  if (scId !== sid || scShownRun?.id !== id) return;
  scDrawRun(); $("#sc-run-view").scrollIntoView({ behavior: scMotion(), block: "start" });
}
function scColumns(rows) {
  const seen = new Set(), tail = ["source_url", "scraped_at"];
  rows.forEach((r) => Object.keys(r || {}).forEach((k) => seen.add(k)));
  return [...[...seen].filter((k) => !tail.includes(k)), ...tail.filter((k) => seen.has(k))];
}
const scCellText = (v) => (v === null || v === undefined ? "" : typeof v === "object" ? JSON.stringify(v) : String(v));
function scDrawRun() {
  const q = $("#sc-run-q").value.trim().toLowerCase(), cols = scColumns(scShownRows);
  const rows = q ? scShownRows.filter((r) => cols.map((c) => scCellText(r[c])).join(" ").toLowerCase().includes(q)) : scShownRows;
  const cell = (v) => {
    const t = scCellText(v);
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(t) && !isNaN(Date.parse(t))) return `<td class="sc-cell" title="${esc(t)}">${esc(fmtWhen(t))}</td>`;
    if (/^https?:\/\//i.test(t)) { const short = t.replace(/^https?:\/\//i, ""); return `<td class="sc-cell"><a href="${esc(t)}" target="_blank" rel="noopener" dir="ltr" title="${esc(t)}">${esc(short.length > 48 ? short.slice(0, 47) + "…" : short)}</a></td>`; }
    return `<td class="sc-cell${typeof v === "number" ? " num" : ""}">${esc(t.length > 300 ? t.slice(0, 299) + "…" : t)}</td>`;
  };
  $("#sc-run-table thead").innerHTML = cols.length ? `<tr>${cols.map((c) => `<th>${esc(c)}</th>`).join("")}</tr>` : "";
  $("#sc-run-table tbody").innerHTML = rows.slice(0, 400).map((r) => `<tr>${cols.map((c) => cell(r[c])).join("")}</tr>`).join("")
    || `<tr><td class="empty" colspan="${Math.max(1, cols.length)}">${scShownRows.length ? esc(L("No items match the search.", "لا عناصر تطابق البحث.")) : esc(L("No items were saved in this run.", "لم يُحفظ أي عنصر في هذا التشغيل."))}</td></tr>`;
  $("#sc-run-more").textContent = rows.length > 400 ? L(`First 400 of ${rows.length.toLocaleString("en")} shown; download Excel for all.`, `يظهر أول 400 من ${rows.length.toLocaleString("en")}؛ نزّل Excel لرؤية الكل.`)
    : `${rows.length.toLocaleString("en")} ${L("items", "عنصر")}${q ? ` / ${scShownRows.length.toLocaleString("en")}` : ""}`;
}
$("#sc-run-q").addEventListener("input", scDrawRun);
function scSheet(s, rows, subtitle) {
  const cols = scColumns(rows);
  const priceCols = cols.map((c, i) => [c, i]).filter(([c]) => /price|سعر/i.test(c) && rows.some((r) => typeof r[c] === "number")).map(([, i]) => i + 1);
  return { title: `${s.name || s.map_name} (${s.map_name})`, subtitle, headers: cols, widths: cols.map((c) => Math.min(48, Math.max(12, c.length + 4))), priceCols,
    rows: rows.map((r) => cols.map((c) => (typeof r[c] === "number" ? r[c] : scCellText(r[c])))) };
}
async function scExcelBtn(btn, work) {
  const old = btn.textContent; btn.disabled = true; btn.textContent = L("Preparing…", "يُجهَّز…");
  try { await work(); } catch (e) { toast(e?.code ? dbErr(e) : e?.message || String(e), true); }
  finally { btn.disabled = false; btn.textContent = old; }
}
$("#sc-run-export").addEventListener("click", () => {
  const s = scrapers[scId], run = scShownRun; if (!s || !run) return;
  if (!scShownRows.length) return toast(L("No items to download in this run", "لا توجد عناصر للتنزيل في هذا التشغيل"), true);
  scExcelBtn($("#sc-run-export"), () => offerXlsx(`${s.map_name} ${run.id}.xlsx`,
    scSheet(s, scShownRows, `${scShownRows.length} items • run ${run.id} • ${SC_ENGINE[run.engine] || run.engine || ""} • ${dubaiDay(run.startedAt)}`)));
});
$("#sc-export-all").addEventListener("click", () => {
  const sid = scId, s = scrapers[sid]; if (!s) return;
  scExcelBtn($("#sc-export-all"), async () => {
    const all = (await db.collection(`scrapers/${sid}/runs`).get()).docs.map((d) => ({ id: d.id, ...plain(d) })).sort((a, b) => String(a.startedAt).localeCompare(String(b.startedAt)));
    const rows = [];
    for (const r of all) for (const x of await scRowsOf(sid, r)) rows.push({ run_id: r.id, run_date: dubaiDay(r.startedAt), ...x });
    if (!rows.length) return toast(L("No saved items yet", "لا توجد عناصر محفوظة بعد"), true);
    await offerXlsx(`${s.map_name} - all runs.xlsx`, scSheet(s, rows, `${rows.length} items • ${all.length} runs`));
  });
});
$("#sc-run-delete").addEventListener("click", () => {
  const sid = scId, run = scShownRun; if (!run) return;
  askInline($("#sc-run-confirm"), esc(L(`Delete the run of ${fmtWhen(run.startedAt)} and its items for good?`, `حذف تشغيل ${fmtWhen(run.startedAt)} وعناصره نهائياً؟`)), L("Delete run", "حذف التشغيل"), async () => {
    try { await scDeleteRunDocs(sid, run.id); $("#sc-run-view").hidden = true; scShownRun = null; toast(L("Run deleted", "حُذف التشغيل")); if (scId === sid) scLoadRuns(); }
    catch (e) { toast(dbErr(e), true); }
  }, true);
});
