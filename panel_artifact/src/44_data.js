
// ============================================================ app: shared page data (one source for a KPI and the page it links to)
const DIV_EN = { "01": "Food and non-alcoholic beverages", "03": "Clothing and footwear", "04": "Housing, water, electricity, gas", "05": "Furnishings and household equipment", "08": "Information and communication", "09": "Recreation, sport and culture", "11": "Restaurants and accommodation", "13": "Personal care and miscellaneous" };
const MODE_LABEL = () => ({ barcode: L("Barcode", "باركود"), spec: L("Category crawl", "مسح الأقسام"), name: L("Name/model (catalogue)", "اسم/موديل (كتالوج)"), service: L("Service", "خدمة"), market: L("Market price", "سعر سوق") });
// saved outlets (Create outlet) merge into each project's list
async function savedOutlets(pid) {
  const s = st(pid);
  if (s.saved) return s.saved;
  try { s.saved = (await db.collection(`projects/${pid}/outlets`).get()).docs.map((d) => ({ code: d.id, ...plain(d), saved: true })); } catch (e) { s.saved = []; }
  return s.saved;
}
async function catalogueLatest() { const s = st("cpi"); if (s.cat === undefined) s.cat = await getDoc("projects/cpi/catalogue/latest"); return s.cat; }
// the latest CPI daily run with its rows (the only run whose rows a page reads on open)
async function cpiLatest() {
  const list = await ensureRuns("cpi"), { days, dup } = dayRunsOf(list);
  const last = days[days.length - 1]?.run || null;
  const rows = last ? annotateRows("cpi", last, await runRows("cpi", last)) : [];
  return { list, days, dup, last, rows };
}
/* Outlet rows per project: code, names, status, working state (+ since), prices in the latest run, last price seen, last read,
   required items, extra columns. The Outlets page lists them; the Dashboard KPI counts them. */
async function outletRows(pid, opts = {}) {
  const saved = await savedOutlets(pid);
  if (pid === "cpi") {
    const [{ days, last, rows }, cat, b] = await Promise.all([cpiLatest(), catalogueLatest(), ensureBasket("cpi")]);
    const ls = last ? cpiLogStates(last) : {};
    const nBarcode = b.filter((i) => i.match_mode === "barcode").length;
    const out = CPI_OUTLETS.map((o) => {
      const rws = rows.filter((r) => r.retailer === o.code);
      const seen = rws.filter((r) => r.accepted === "yes" && r.obs_state !== "blocked_carried").length;
      let state, reason = "", since = "";
      if (o.daily) {
        const x = ls[o.code]; state = x?.state || "notread"; reason = cpiReason(x, o.code);
        if (state === "blocked") { const s = cpiBlockedSince(days, o.code); if (s) since = L(`since ${fmtDay(s.day)}`, `منذ ${fmtDay(s.day)}`); }
      } else {
        const n = o.stores.reduce((a, s) => a + (cat?.stores?.[s] || 0), 0);
        state = !cat ? "notread" : n > 0 ? "ok" : "blocked";
        reason = cat ? L(`catalogue ${fmtDay(cat.date)}: ${fmtN(n)} products`, `الكتالوج ${fmtDay(cat.date)}: ${fmtN(n)} منتج`) : L("no catalogue yet", "لا كتالوج بعد");
      }
      // last price seen / last read: walk back through the daily runs (log and summary only, no rows)
      let lastSeen = null, lastRead = null;
      for (let i = days.length - 1; i >= 0 && (!lastSeen || !lastRead) && o.daily; i--) {
        const r = days[i].run, x = cpiLogStates(r)[o.code], blocked = x?.state === "blocked";
        const acc = (r.summary?.[`${o.code}_barcode`]?.accepted || 0) + (blocked ? 0 : r.summary?.[`${o.code}_category`]?.accepted || 0);
        if (!lastSeen && acc > 0) lastSeen = days[i].day;
        if (!lastRead && (x?.state === "ok" || x?.state === "partial")) lastRead = days[i].day;
      }
      if (!o.daily) { lastSeen = seen && last ? runDay(last) : null; lastRead = state === "ok" ? cat?.date : null; }
      const required = o.daily ? nBarcode : new Set(rws.filter((r) => r.source === "catalogue").map((r) => r.item_code)).size;
      return { code: o.code, en: o.en, ar: o.ar, status: "active", state, reason, since, prices: last ? seen : null, lastSeen, lastRead, required,
        sources: o.daily ? L("daily barcode + category, catalogue", "يومي باركود + أقسام، كتالوج") : L("catalogue", "الكتالوج"),
        children: (o.children || []).map(([en, ar, store]) => ({ en, ar, n: cat?.stores?.[store] ?? null })), log: last ? (last.log || []).filter((l) => new RegExp(o.en.split(" ")[0], "i").test(l)) : [] };
    });
    return [...out, ...saved.filter((s) => !out.some((o) => o.code === s.code)).map(savedRow)];
  }
  if (pid === "te") {
    const days = await teDays(), lastD = days[days.length - 1], prev = days[days.length - 2];
    const n = lastD?.rows.length ?? null, missing = prev ? prev.rows.filter((r) => !lastD.rows.some((x) => teKey(x) === teKey(r))).map((r) => r.commodity) : [];
    const rs = lastD ? runStatus("te", lastD.run) : null;
    const state = !lastD ? "notread" : rs.code === "failed" ? "failed" : n >= TE_BASKET_N && !missing.length ? "ok" : "partial";
    const row = { code: "te", en: "Trading Economics", ar: "تريدنغ إيكونوميكس", status: "active", state, reason: lastD ? L(`${n} of ${TE_BASKET_N} rows`, `${n} من ${TE_BASKET_N} صفاً`) : "",
      prices: n, lastSeen: lastD?.day, lastRead: lastD?.day, required: TE_BASKET_N, method: L("direct fetch, apify/web-fetch fallback", "جلب مباشر، والبديل apify/web-fetch"), missing, log: lastD?.run.log || [] };
    return [row, ...saved.filter((s) => s.code !== "te").map(savedRow)];
  }
  if (pid === "sppi") {
    const d = await sppiLoad();
    if (!d.meta) return saved.map(savedRow);
    const wid = opts.week || d.weeks[d.weeks.length - 1]?.id;
    const out = d.outlets.filter((o) => o.status !== "retired").map((o) => {
      const s = wid ? sppiOutletState(wid, o.code) : { state: "notread", reason: "" };
      const priced = wid ? sppiActiveRows(wid).filter((r) => r.outlet === o.code && (r.status === "ok" || r.source === "manual") && hasPrice(r)).length : null;
      let lastSeen = null, lastRead = null;
      for (const w of [...d.weeks].reverse()) { const rs = sppiActiveRows(w.id).filter((r) => r.outlet === o.code); if (!lastSeen && rs.some((r) => hasPrice(r) && r.status !== "blocked")) lastSeen = w.collected_on || w.tickets?.out; if (!lastRead && rs.some((r) => r.status === "ok")) lastRead = w.collected_on || w.tickets?.out; }
      return { code: o.code, en: o.name_en || o.code, ar: o.name_ar || "", status: o.status || "active", state: s.state, reason: s.reason, prices: priced, lastSeen, lastRead,
        required: d.sample.filter((x) => x.outlet === o.code && x.status !== "retired").length, kind: o.kind, market: o.market, access: o.access, url: o.url, log: [] };
    });
    return [...out, ...saved.filter((s) => !out.some((o) => o.code === s.code)).map(savedRow)];
  }
  return saved.map(savedRow);
}
const savedRow = (s) => ({ code: s.code, en: s.name_en || s.code, ar: s.name_ar || "", status: s.status || "active", state: "notread", reason: L("added here; not scraped", "أُضيف هنا؛ لا يُسحب"), prices: null, lastSeen: null, lastRead: null, required: 0, kind: s.kind, saved: true, log: [] });
// rows of the Scrapers page that are not custom scrapers: the project's routine collectors (read-only)
function routineRows(pid) {
  if (pid === "cpi") {
    const s = S.cpi, list = s?.runs || [], { days } = dayRunsOf(list), last = days[days.length - 1]?.run, ls = last ? cpiLogStates(last) : {}, b = s?.basket || [];
    const n = (m) => s?.basket ? b.filter((i) => i.match_mode === m).length : null;   // null = basket not read: the KPI shows "—"
    const one = (k, kind, label) => { const x = ls[k], sum = last?.summary?.[`${k}_${kind}`];
      const st2 = kind === "category" && x?.state === "blocked" ? "blocked" : x?.state || "notread";
      const cats = (x?.cats || []).reduce((a, c) => [a[0] + c.products, a[1] + c.pages], [0, 0]);
      return { label, outlet: outletEn(k), method: L("Routine · Scrapling (cpi_daily)", "مهمة مجدولة · Scrapling (cpi_daily)"), active: true, target: kind === "barcode" ? n("barcode") : n("spec"),
        chip: last ? stateChip(st2) : "—", last: last ? (kind === "barcode" && x ? L(`${fmtN(x.read)} pages read, ${fmtN(x.failed)} failed · ${fmtN(sum?.accepted)}/${fmtN(sum?.lines)}`, `قُرئت ${fmtN(x.read)} صفحة، فشلت ${fmtN(x.failed)} · ${fmtN(sum?.accepted)}/${fmtN(sum?.lines)}`) : L(`${fmtN(cats[0])} products from ${fmtN(cats[1])} pages · ${fmtN(sum?.accepted)}/${fmtN(sum?.lines)}`, `${fmtN(cats[0])} منتج من ${fmtN(cats[1])} صفحة · ${fmtN(sum?.accepted)}/${fmtN(sum?.lines)}`)) + " · " + fmtDay(runDay(last)) : "—" }; };
    return [one("carrefour", "barcode", "Carrefour barcode"), one("carrefour", "category", "Carrefour category"), one("lulu", "barcode", "Lulu barcode"), one("lulu", "category", "Lulu category"),
      { label: L("Catalogue stores", "متاجر الكتالوج"), outlet: "Sharaf DG, Zara, Max, Centrepoint, Carrefour, Lulu", method: L("Routine · catalogue crawl", "مهمة مجدولة · مسح الكتالوج"), active: true, target: n("name"), chip: s?.cat ? stateChip("ok") : "—", last: s?.cat ? L(`catalogue ${fmtDay(s.cat.date)}: ${fmtN(s.cat.rows)} products`, `الكتالوج ${fmtDay(s.cat.date)}: ${fmtN(s.cat.rows)} منتج`) : "—" },
      { label: L("Name search", "البحث بالاسم"), outlet: "Carrefour, Lulu", method: L("Routine · name search fallback", "مهمة مجدولة · بحث بالاسم"), active: true, target: 0, chip: last ? stateChip("ok") : "—", last: last ? L(`run of ${fmtDay(runDay(last))}`, `تشغيل ${fmtDay(runDay(last))}`) : "—" }];
  }
  if (pid === "te") {
    const d = S.te?.teDays, last = d?.[d.length - 1];
    return [{ label: "Trading Economics", outlet: "Trading Economics (TE)", method: L("Routine · direct fetch, apify/web-fetch fallback · parser te_commodities", "مهمة مجدولة · جلب مباشر، والبديل apify/web-fetch · المحلل te_commodities"), active: true, target: TE_BASKET_N,
      chip: last ? runChip(runStatus("te", last.run)) : "—", last: last ? L(`${last.rows.length}/${TE_BASKET_N} rows · ${fmtDay(last.day)}`, `${last.rows.length}/${TE_BASKET_N} صفاً · ${fmtDay(last.day)}`) : "—", note: L("The parser fails below 20 rows", "المحلل يفشل تحت 20 صفاً") }];
  }
  if (pid === "sppi") {
    const c = sppiCache?.collectors || [];
    return c.map((x) => ({ label: `${sppiName(sppiOutlet(x.outlet)) || x.outlet} · ${x.survey === "packages" ? L("packages", "باقات") : L("tickets", "تذاكر")}`, outlet: sppiName(sppiOutlet(x.outlet)) || x.outlet,
      method: `${x.script || ""} · ${{ cloud: L("cloud", "سحابي"), pc: L("PC run", "تشغيل على الحاسوب"), manual: L("manual", "يدوي") }[x.run_location] || x.run_location || ""}`, active: x.run_location !== "manual", target: (sppiCache.sample || []).filter((s) => s.outlet === x.outlet && s.survey === x.survey).length,
      chip: chip(x.run_location === "cloud" ? "Auto" : x.run_location === "pc" ? "PC run" : "Manual", x.run_location === "cloud" ? "blue" : x.run_location === "pc" ? "warn" : "manual"), last: "—", note: L("Economy, 1 adult, direct own-carrier, cheapest fare, next day if none; packages B&B else cheapest, 4 nights", "سياحية، بالغ واحد، مباشر على الناقل نفسه، أرخص سعر، اليوم التالي إن لم يوجد؛ الباقات مع الإفطار وإلا الأرخص، 4 ليالٍ") }));
  }
  return [];
}
function outletOptions(pid) {
  if (pid === "cpi") return CPI_OUTLETS.map((o) => [o.code, o.en]);
  if (pid === "te") return [["te", "Trading Economics"]];
  if (pid === "sppi") return (sppiCache?.outlets || []).map((o) => [o.code, sppiName(o)]);
  return [];
}
function outletName(pid, code) { if (!code) return ""; return (outletOptions(pid).find(([c]) => c === code) || [code, code])[1]; }
async function activeScraperCount(pid) {
  if (!scLoaded) await scLoad();
  if (pid === "cpi") { await Promise.all([ensureRuns("cpi"), ensureBasket("cpi"), catalogueLatest()]); }
  if (pid === "te") await teDays();
  if (pid === "sppi") await sppiLoad();
  const r = routineRows(pid).filter((x) => x.active !== false).length;
  return r + Object.values(scrapers).filter((s) => s.project === pid && s.active).length;
}
