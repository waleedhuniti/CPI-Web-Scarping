
// ============================================================ Home: three project cards, other projects
const OTHER_IDS = () => Object.keys(projects).filter((id) => !["cpi", "sppi", "te", "hotels"].includes(id));
function pgHome(r, seq) {
  const fig = (id, label, v = "—") => `<div class="fig"><span>${esc(label)}</span><b id="${id}">${esc(v)}</b></div>`;
  const card = (key, title, sub, icon, figs) => `<a class="pcard" id="home-card-${key}" href="#${key}-dashboard">
      <span class="pc-top"><span class="tile">${ico(icon)}</span><span class="pc-name">${esc(title)}</span>${ico("chevr", "chev flip")}</span>
      <span class="pc-sub">${esc(sub)}</span><span class="figs">${figs}</span><span id="home-chip-${key}">${chip(L("Loading…", "يُحمَّل…"), "grey")}</span></a>`;
  $("#page").innerHTML = `${whereNote()}
    <h1 class="page-title">${esc(L("Projects", "المشاريع"))}</h1>
    <p class="home-intro">${esc(L("Prices collected from shops and websites, ready for checking and for Dataiku.", "أسعار تُجمع من المتاجر والمواقع، جاهزة للمراجعة ولـ Dataiku."))}</p>
    <div class="home-cards" id="home-cards">
      ${card("cpi", "CPI", L("Consumer price basket, Dubai shops, daily", "سلة أسعار المستهلك من متاجر دبي، يومياً"), "cart",
        fig("home-cpi-lines", L("Basket lines", "بنود السلة")) + fig("home-cpi-seen", L("Seen prices, latest run", "أسعار مرئية في آخر تشغيل")) + fig("home-cpi-date", L("Latest run (Dubai)", "آخر تشغيل (دبي)")))}
      ${card("sppi", "SPPI", L("Air tickets and holiday packages, monthly", "تذاكر الطيران وباقات العطلات، شهرياً"), "plane",
        fig("home-sppi-items", L("Items", "البنود")) + fig("home-sppi-weeks", L("Collections this month", "مرات الجمع هذا الشهر")) + fig("home-sppi-date", L("Last collection", "آخر جمع")))}
      ${card("trendx", "TrendX", L("Global commodity closing prices, daily", "أسعار إغلاق السلع العالمية، يومياً"), "trend",
        fig("home-te-n", L("Commodities", "السلع")) + fig("home-te-idx", L("TrendX Index", "مؤشر TrendX")) + fig("home-te-col", L("Collected", "جُمع")) + fig("home-te-q", L("Latest quote", "آخر تسعيرة")))}
    </div>
    <p class="home-foot"><a href="#other-projects" id="home-other">${esc(L(`Other projects (${OTHER_IDS().length})`, `مشاريع أخرى (${OTHER_IDS().length})`))}</a></p>
    <p class="home-foot muted">${esc(L("Internal tool", "أداة داخلية"))}</p>`;
  bindWhereNote();
  const set = (id, v, title) => { const e = document.getElementById(id); if (e && alive(seq)) { e.textContent = v; if (title) e.title = title; } };
  const setChip = (key, html) => { const e = document.getElementById("home-chip-" + key); if (e && alive(seq)) e.innerHTML = html; };
  const fail = (ids, key, e) => { for (const id of ids) set(id, "—", L("Could not read: ", "تعذّرت القراءة: ") + dbErr(e)); setChip(key, chip(L("Could not read", "تعذّرت القراءة"), "grey")); };
  // CPI
  (async () => {
    try {
      const [b, list] = await Promise.all([ensureBasket("cpi"), ensureRuns("cpi")]);
      set("home-cpi-lines", fmtN(b.length));
      const { days } = dayRunsOf(list), last = days[days.length - 1]?.run;
      if (!last) { set("home-cpi-seen", "—"); set("home-cpi-date", "—"); setChip("cpi", chip(L("No runs yet", "لا تشغيلات بعد"), "grey")); return; }
      set("home-cpi-seen", `${fmtN(cpiSeen(last))} / ${fmtN(last.count)} ${L("rows", "صف")}`, L(`${fmtN(cpiCarried(last))} carried rows of blocked outlets are not counted`, `لا تُحسب ${fmtN(cpiCarried(last))} صفوف منقولة لمنافذ محجوبة`));
      set("home-cpi-date", fmtDay(runDay(last)));
      const rs = runStatus("cpi", last), bl = [...cpiBlockedSet(last)];
      if (rs.code === "partial" && bl.length) { const since = cpiBlockedSince(days, bl[0]); setChip("cpi", chip(L(`Partial: ${outletEn(bl[0]).split(" ")[0]} blocked since ${fmtDay(since?.day)}`, `جزئي: ${outletEn(bl[0]).split(" ")[0]} محجوب منذ ${fmtDay(since?.day)}`), "warn")); }
      else setChip("cpi", runChip(rs));
    } catch (e) { fail(["home-cpi-lines", "home-cpi-seen", "home-cpi-date"], "cpi", e); }
  })();
  // SPPI
  (async () => {
    try {
      const d = await sppiLoad();
      if (!d.meta) { for (const id of ["home-sppi-items", "home-sppi-weeks", "home-sppi-date"]) set(id, "—"); setChip("sppi", chip(L("No data yet", "لا بيانات بعد"), "grey")); return; }
      const items = d.items.filter((i) => i.status !== "retired"), routes = items.filter((i) => i.kind === "route").length;
      set("home-sppi-items", fmtN(items.length), L(`${routes} routes · ${items.length - routes} hotels`, `${routes} مسار · ${items.length - routes} فندق`));
      const month = sppiCurrentMonth(d), ws = d.weeks.filter((w) => w.month === month);
      set("home-sppi-weeks", fmtN(ws.length));
      const lastC = d.weeks.map((w) => w.collected_on).filter(Boolean).sort().pop();
      set("home-sppi-date", fmtDay(lastC));
      const open = [...d.weeks].reverse().find((w) => w.status !== "complete") || d.weeks[d.weeks.length - 1];
      if (open) { const bl = sppiActiveRows(open.id).filter((r) => r.status === "blocked").length;
        setChip("sppi", chip(L(`${sppiWeekLabel(open)} (${fmtMonth(open.month)}) open · ${bl} blocked cells`, `${sppiWeekLabel(open)} (${fmtMonth(open.month)}) مفتوح · ${bl} خلية محجوبة`), bl ? "warn" : "blue")); }
      else setChip("sppi", chip(L("No collection yet", "لا جمع بعد"), "grey"));
    } catch (e) { fail(["home-sppi-items", "home-sppi-weeks", "home-sppi-date"], "sppi", e); }
  })();
  // TrendX
  (async () => {
    try {
      const days = await teDays();
      const last = days[days.length - 1];
      if (!last) { for (const id of ["home-te-n", "home-te-idx", "home-te-col", "home-te-q"]) set(id, "—"); setChip("trendx", chip(L("No runs yet", "لا تشغيلات بعد"), "grey")); return; }
      const n = last.rows.length, inIdx = last.rows.filter((r) => !TE_EXCL.includes(r.category)).length;
      set("home-te-n", L(`${fmtN(n)} commodities · ${fmtN(inIdx)} in index`, `${fmtN(n)} سلعة · ${fmtN(inIdx)} في المؤشر`));
      const idx = teIndex(days);
      set("home-te-idx", `${idx[idx.length - 1].y.toFixed(2)} · ${fmtDay(TE_DEFAULT_INDEX.base, { year: true })} = 100`);
      set("home-te-col", L(`${fmtDay(last.day)} ${fmtTimeDubai(last.run.startedAt)} Dubai`, `${fmtDay(last.day)} ${fmtTimeDubai(last.run.startedAt)} دبي`));
      const q = teQuoteDate(last.rows); set("home-te-q", fmtDay(q.mode), L(`the date most quotes carry; newest ${q.max}`, `التاريخ الذي تحمله أغلب التسعيرات؛ الأحدث ${q.max}`));
      const rs = runStatus("te", last.run), today = todayDubai();
      setChip("trendx", rs.code === "failed" ? runChip(rs) : n >= TE_BASKET_N && last.day >= dayAdd(today, -1) ? chip(L(`${n}/${TE_BASKET_N} rows`, `${n}/${TE_BASKET_N} صفاً`), "ok")
        : chip(n < TE_BASKET_N ? L(`Partial: ${n} of ${TE_BASKET_N} rows`, `جزئي: ${n} من ${TE_BASKET_N} صفاً`) : L(`${n}/${TE_BASKET_N} rows · no run today`, `${n}/${TE_BASKET_N} صفاً · لا تشغيل اليوم`), "warn"));
    } catch (e) { fail(["home-te-n", "home-te-idx", "home-te-col", "home-te-q"], "trendx", e); }
  })();
}
function teQuoteDate(rows) {
  const c = {}; for (const r of rows) if (r.price_date) c[r.price_date] = (c[r.price_date] || 0) + 1;
  const ds = Object.keys(c).sort();
  return { mode: Object.entries(c).sort((a, b) => b[1] - a[1] || b[0].localeCompare(a[0]))[0]?.[0] || "", max: ds[ds.length - 1] || "" };
}
function sppiCurrentMonth(d) {
  const t = todayDubai().slice(0, 7);
  return d.weeks.some((w) => w.month === t) ? t : d.weeks[d.weeks.length - 1]?.month || t;
}
// other projects (cci, rent): their own cards; each opens its basket editor and settings
function pgOthers(r, seq) {
  const ids = OTHER_IDS();
  $("#page").innerHTML = `<h1 class="page-title">${esc(L("Other projects", "مشاريع أخرى"))}</h1>
    <div class="home-cards">${ids.map((id) => { const p = projects[id];
      return `<a class="pcard" id="home-card-${esc(id)}" href="#other-${esc(id)}"><span class="pc-top"><span class="tile">${ico(id === "rent" ? "house" : "building")}</span><span class="pc-name" dir="auto">${esc(p.short || p.name || id)}</span>${ico("chevr", "chev flip")}</span>
        <span class="pc-sub" dir="auto">${esc(p.name || "")}</span><span class="pc-sub" dir="auto">${esc(p.description || "")}</span>
        <span>${chip(p.status === "planned" ? L("Planned", "قيد التخطيط") : L("Live", "فعّال"), p.status === "planned" ? "blue" : "ok")} ${chip(L(`${fmtN(p.itemCount ?? 0)} items`, `${fmtN(p.itemCount ?? 0)} عنصر`), "grey")}</span></a>`; }).join("") || emptyHtml("folder", L("No other projects", "لا مشاريع أخرى"), "")}</div>
    <p class="home-foot"><a href="#home">${esc(L("Back to Home", "العودة إلى الرئيسية"))}</a></p>`;
}
async function pgOther(r, seq) {
  const p = projects[r.id];
  $("#page").innerHTML = headCard(p.short || p.name || r.id, "#other-projects", "", `<p class="muted" dir="auto" style="margin:0">${esc(p.description || "")}</p>`)
    + `<div data-slot="basket"></div><h2>${esc(L("Project settings", "إعدادات المشروع"))}</h2><div data-slot="settings"></div>`;
  mount("basket", "blk-basket"); mount("settings", "blk-settings");
  renderSettings();
  await mountBasketLoad(r.id, seq);
}
