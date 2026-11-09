
// ============================================================ app: shell (language, band, sidebar, router, legacy block mounting)
ICONS.chevr = '<path d="m9.5 6 6 6-6 6"/>';
ICONS.back = '<path d="m14.5 6-6 6 6 6"/>';
const BLOCKS = ["blk-basket", "blk-actors", "r-export-all", "r-view", "quick", "apify-run", "blk-settings", "blk-sc-ws"];
function unmountAll() { const h = $("#hold"); for (const id of BLOCKS) { const el = document.getElementById(id); if (el && el.parentElement !== h) h.appendChild(el); } }
function mount(slot, id) { const s = $(`[data-slot="${slot}"]`), el = document.getElementById(id); if (s && el) s.appendChild(el); return !!(s && el); }

// ---------------- language
function applyStatic() {
  const ar = LANG === "ar";
  document.documentElement.lang = LANG; document.documentElement.dir = ar ? "rtl" : "ltr";
  for (const el of $$("[data-ar]")) { if (el.dataset.en == null) el.dataset.en = el.textContent; el.textContent = ar ? el.dataset.ar : el.dataset.en; }
  for (const el of $$("[data-ar-html]")) { if (el.dataset.enHtml == null) el.dataset.enHtml = el.innerHTML; el.innerHTML = ar ? el.dataset.arHtml : el.dataset.enHtml; }
  for (const [attr, k] of [["placeholder", "arPh"], ["aria-label", "arAl"], ["title", "arTitle"]]) {
    const ek = k.replace("ar", "en");
    for (const el of $$(`[data-${k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase())}]`)) { if (el.dataset[ek] == null) el.dataset[ek] = el.getAttribute(attr) || ""; el.setAttribute(attr, ar ? el.dataset[k] : el.dataset[ek]); }
  }
  const t = $("#lang-toggle"); t.textContent = ar ? "English" : "العربية"; t.lang = ar ? "en" : "ar";
  t.setAttribute("aria-label", ar ? "Switch to English" : "التبديل إلى العربية");
  $("#side-toggle").setAttribute("aria-label", $("#shell").classList.contains("collapsed") ? L("Expand menu", "توسيع القائمة") : L("Collapse menu", "طيّ القائمة"));
  $("#side-toggle").title = $("#side-toggle").getAttribute("aria-label");
  $("#skip-link").textContent = L("Skip to main content", "تخطَّ إلى المحتوى");
}
function setLang(l) {
  LANG = l === "ar" ? "ar" : "en";
  try { localStorage.setItem("lang", LANG); } catch (e) {}
  applyStatic(); setConnText(); rerender();
}

// ---------------- band
function refreshBand() {
  const r = curRoute, pill = $("#band-proj");
  const pid = r?.kind === "page" ? r.pid : r?.kind === "other" ? r.id : null;
  pill.hidden = !pid; pill.textContent = pid ? projLabel(pid) : "";
  $("#band-title").textContent = L("Price Collection Platform", "منصة جمع الأسعار");
  document.title = (r?.kind === "page" ? `${pageName(r.page === "settings" ? "settings" : r.page)} · ${projLabel(r.pid)} · ` : "") + L("Price Collection Platform", "منصة جمع الأسعار");
}
let connState = ["", L("Connecting…", "جارٍ الاتصال…"), "Connecting…", "جارٍ الاتصال…"];
function setConn(state, en, ar) { connState = [state, null, en, ar ?? en]; setConnText(); }
function setConnText() { const [s, , en, ar] = connState; $("#conn-dot").className = "dot " + s; $("#conn-text").textContent = L(en, ar); $("#conn").title = L(en, ar); }

// ---------------- sidebar: 7 pages per project, collapsible rail, strip under 900px
function renderSide() {
  const r = curRoute, side = $("#side"), shell = $("#shell");
  if (!r || r.kind !== "page") { side.hidden = true; shell.classList.add("no-side"); $("#side-nav").innerHTML = ""; return; }
  side.hidden = false; shell.classList.remove("no-side");
  const p = routeOf(r.pid);
  $("#side-nav").innerHTML = PAGES.filter(([pg]) => pg !== "manual" || r.pid !== "te").map(([pg, icon, en, ar]) => { const lbl = L(en, ar);
    return `<a class="nav-item" href="#${p}-${pg}" data-pg="${pg}"${r.page === pg ? ' aria-current="page"' : ""} title="${esc(lbl)}" aria-label="${esc(lbl)}"><span class="tile">${ico(icon)}</span><span class="lbl">${esc(lbl)}</span>${ico("chevr", "chev flip")}</a>`; }).join("");
  const set = $("#side-settings"); set.href = `#${p}-settings`;
  if (r.page === "settings") set.setAttribute("aria-current", "page"); else set.removeAttribute("aria-current");
  $(".lbl", set).textContent = L("Project settings", "إعدادات المشروع");
  const on = $("#side-nav [aria-current]");
  if (on && matchMedia("(max-width: 899px)").matches) try { on.scrollIntoView({ inline: "center", block: "nearest" }); } catch (e) {}
}
function setSideCollapsed(on, persist = true) {
  $("#shell").classList.toggle("collapsed", on);
  const b = $("#side-toggle"), t = on ? L("Expand menu", "توسيع القائمة") : L("Collapse menu", "طيّ القائمة");
  b.setAttribute("aria-expanded", String(!on)); b.setAttribute("aria-label", t); b.title = t;
  if (persist) try { localStorage.setItem("side-collapsed", on ? "1" : ""); } catch (e) {}
}
$("#side-toggle").addEventListener("click", () => setSideCollapsed(!$("#shell").classList.contains("collapsed")));
$("#lang-toggle").addEventListener("click", () => setLang(LANG === "ar" ? "en" : "ar"));

// ---------------- router: #home, #<p>-<page>[/sub], #<p>-settings, #other-projects, #other-<id>
let routeKey = null, curRoute = null, renderSeq = 0, pendingDraft = null;
const SUBS = { "price-history": ["commodities"] };
function parseRoute(h) {
  h = String(h || "").replace(/^#/, "");
  try { h = decodeURIComponent(h); } catch (e) {}
  if (!h || h === "home") return { kind: "home", key: "home" };
  if (h === "other-projects") return { kind: "others", key: h };
  let m = /^other-([\w.~-]+)$/.exec(h);
  if (m && projects[m[1]] && !["cpi", "sppi", "te"].includes(m[1])) return { kind: "other", id: m[1], key: h };
  m = /^(cpi|sppi|trendx)-(dashboard|outlets|price-history|schedules|years-months|scrapers|price-logs|manual|settings)(?:\/(.+))?$/.exec(h);
  if (m) {
    const sub = m[3] || "";
    if (sub && !(SUBS[m[2]] || []).includes(sub) && !(m[2] === "scrapers" && /^[a-z0-9_-]+$/.test(sub))) return { kind: "unknown", pid: ROUTE2ID[m[1]], key: h };
    if (m[2] === "manual" && m[1] === "trendx") return { kind: "unknown", pid: "te", key: h };
    return { kind: "page", pid: ROUTE2ID[m[1]], page: m[2], sub, key: h };
  }
  // addresses of the previous layout
  if (["cpi", "sppi", "te", "trendx"].includes(h)) return { redirect: `#${routeOf(h === "trendx" ? "te" : h)}-dashboard` };
  if (h === "scrapers") return { redirect: "#cpi-scrapers" };
  m = /^scraper-([a-z0-9_-]+)$/.exec(h);
  if (m) { const s = scrapers[m[1]]; return { redirect: `#${routeOf(["cpi", "sppi", "te"].includes(s?.project) ? s.project : "cpi")}-scrapers/${m[1] === "new" ? "new" : m[1]}` }; }
  if (projects[h]) return { redirect: `#other-${h}` };
  m = /^(cpi|sppi|trendx)[-/]/.exec(h);
  if (m) return { kind: "unknown", pid: ROUTE2ID[m[1]], key: h };   // e.g. #cpi-nope: back to that project's dashboard
  return { kind: "unknown", key: h };
}
function go(hash) {
  if ((location.hash || "#home") === hash) { routeKey = null; route(); }
  else location.hash = hash;
}
function rerender() { routeKey = null; route(); }
function route() {
  const h = (location.hash || "").slice(1) || "home";
  if (h === routeKey) return;
  const r = parseRoute(h);
  if (r.redirect) { try { history.replaceState(null, "", r.redirect); } catch (e) {} return route(); }
  if (routeKey !== null) {
    if (basketDirty && curRoute && r.key !== curRoute.key) {
      toast(L("Save the basket changes first, or reload the page to drop them", "احفظ تعديلات السلة أولاً أو أعد تحميل الصفحة لتجاهلها"), true);
      try { history.replaceState(null, "", "#" + routeKey); } catch (e) {} return;
    }
    const toSc = r.kind === "page" && r.page === "scrapers" ? (r.sub ? (r.sub === "new" ? "new" : r.sub) : "list") : null;
    if (scRoute && scDirty && toSc !== scRoute) {
      try { history.replaceState(null, "", "#" + routeKey); } catch (e) {}
      scCanLeave(() => { scDirty = false; location.hash = h; });
      return;
    }
  }
  routeKey = h; curRoute = r;
  if (!(r.kind === "page" && r.page === "scrapers")) scLeave();
  renderPage(r);
}
window.addEventListener("hashchange", route);
const alive = (seq) => seq === renderSeq;
function renderPage(r) {
  const seq = ++renderSeq;
  unmountAll(); if ($("#sp-root").innerHTML) closeSidePanel();
  if (r.kind === "unknown" && !r.pid) r.backPid = ["cpi", "sppi", "te"].includes(current) ? current : "cpi";
  const pid = r.kind === "page" || r.kind === "unknown" && r.pid ? r.pid : r.kind === "other" ? r.id : null;
  if (pid !== current) { current = pid; bPage = 0; basket = pid && S[pid]?.basket ? S[pid].basket : []; basketLoaded = !!(pid && S[pid]?.basket); runs = pid && S[pid]?.runs ? S[pid].runs : []; basketDirty = false; }
  refreshBand(); renderSide();
  if (!(r.kind === "page" && r.page === "price-history" && !r.sub)) { try { const keep = localStorage.getItem("side-collapsed") === "1"; if ($("#shell").classList.contains("collapsed") !== keep) setSideCollapsed(keep, false); } catch (e) {} }
  const fn = r.kind === "home" ? pgHome : r.kind === "others" ? pgOthers : r.kind === "other" ? pgOther : r.kind === "unknown" ? pgUnknown
    : { dashboard: pgDashboard, outlets: pgOutlets, "price-history": r.sub === "commodities" ? pgCommodities : pgHistory, schedules: pgSchedules,
        "years-months": pgYears, scrapers: pgScrapers, "price-logs": pgLogs, manual: pgManual, settings: pgSettings }[r.page];
  try { fn(r, seq); }
  catch (e) { $("#page").innerHTML = errBox(L("This page could not be drawn: ", "تعذّر رسم هذه الصفحة: ") + (e?.message || e)); }
  bindRetry();
  if (!(r.kind === "page" && r.page === "scrapers" && r.sub)) { try { window.scrollTo(0, 0); } catch (e) {} }
}
// any Retry button in an error box re-renders the page with fresh data
function bindRetry() { for (const b of $$("#page [data-retry]")) if (!b.onclick) b.onclick = () => { for (const k of Object.keys(S)) delete S[k]; sppiCache = null; rerender(); }; }
function pgUnknown(r) {
  const back = `#${routeOf(r.pid || r.backPid || "cpi")}-dashboard`;
  $("#page").innerHTML = `<h1 class="page-title">${esc(L("Page not found", "الصفحة غير موجودة"))}</h1>
    <div class="errbox" role="alert" id="unknown-route"><span class="bang" aria-hidden="true">!</span><span class="msg">${esc(L("This page does not exist", "هذه الصفحة غير موجودة"))}: <code>#${esc(r.key)}</code></span><a class="btn primary" href="${back}" id="unknown-back">${esc(L("Back to Dashboard", "العودة إلى لوحة المتابعة"))}</a></div>`;
}
// the page title row: centred title, actions on the inline end
function titleRow(title, actions = "", lead = "") {
  return `<h1 class="page-title">${esc(title)}</h1>${actions || lead ? `<div class="page-actions${lead ? " split" : ""}">${lead}${lead ? `<div class="row">${actions}</div>` : actions}</div>` : ""}`;
}
// the page-head card: back button, centred title, a link on the inline end
function headCard(title, back, right = "", body = "") {
  return `<section class="card phc"><div class="phc-top"><a class="btn sq" href="${esc(back)}" id="ph-back" aria-label="${esc(L("Back", "رجوع"))}" title="${esc(L("Back", "رجوع"))}">${ico("back", "flip")}</a><h1>${esc(title)}</h1><div class="end">${right}</div></div>${body ? `<div class="phc-body">${body}</div>` : ""}</section>`;
}
