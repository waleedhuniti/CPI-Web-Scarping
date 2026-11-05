
// ============================================================ boot
(async function boot() {
  let saved = null; try { saved = localStorage.getItem("lang"); } catch (e) {}
  LANG = saved === "ar" ? "ar" : "en";
  applyStatic();
  try { if (localStorage.getItem("side-collapsed") === "1") setSideCollapsed(true, false); } catch (e) {}
  const C = window.claude;
  if (!C?.use) { setConn("bad", "Open this page in claude.ai", "افتح الصفحة من claude.ai"); $("#page").innerHTML = errBox(L("This page works inside claude.ai only, where the projects are stored.", "هذه اللوحة تعمل داخل claude.ai فقط، حيث تُحفظ المشاريع.")); return; }
  [db, mcp, downloads] = await Promise.all([C.use("db"), C.use("mcp"), C.use("downloads")]);
  if (!db) { setConn("bad", "Storage unavailable", "التخزين غير متاح"); $("#page").innerHTML = errBox(L("The projects cannot be read in this view. Open the page from claude.ai while signed in.", "لا يمكن قراءة المشاريع في هذا العرض. افتح الصفحة من claude.ai وأنت مسجّل الدخول.")); return; }
  if (!mcp) setConn("warn", "Connected · runs off", "متصل · التشغيل غير متاح");
  else {
    setConn("ok", "Connected", "متصل");
    mcp.listTools(APIFY).then((l) => { const s = l?.servers?.find((x) => x.server === APIFY); if (!s || s.authStatus === "needs_reauth") $("#conn").title = L("Connected; Apify needs reconnecting in claude.ai settings", "متصل؛ Apify يحتاج إعادة ربط"); }).catch(() => {});
  }
  C.use("user").then(async (u) => { viewer = u || null; try { const me = await u?.me?.(); viewerCache = me?.name || ""; } catch (e) {} }).catch(() => {});
  try { await loadProjects(); } catch (e) { $("#page").innerHTML = errBox(L("Could not read the projects: ", "تعذّر تحميل المشاريع: ") + dbErr(e), "boot-retry"); $("#boot-retry").onclick = () => location.reload(); return; }
  scLoad().then(() => { if (scRoute === "list") scRenderList(); });
  route();
  window.addEventListener("beforeunload", (e) => { if (basketDirty || job?.running || scDirty || scJob?.running) e.preventDefault(); });
})();
