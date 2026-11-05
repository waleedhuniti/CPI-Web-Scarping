let ovRows = [];
const BAR_COLORS = { accepted: "#1a75b8", review: "#d9a43a", other: "#e2e8f0" };   // review stays for runs saved before the yes/no rule
const REVIEW_RE = /review|substitute|multiple|unverified|differs|conflict|mismatch|size_|unit_label_x/;
const isCat = (label) => /category|\(category\)/i.test(label || "");

/* The latest result per source (retailer x barcode/category), taken from the newest run that has it: a daily run
   holds both parts, the runs saved by hand hold one part each. Also the size of the latest bulk catalogue. */
function latestBySource(list) {
  const seen = new Map(); let products = 0, categories = 0, catRun = null;
  for (const r of [...list].sort((a, b) => String(b.startedAt).localeCompare(String(a.startedAt)))) {
    for (const [k, v] of Object.entries(r.summary || {})) {
      const kind = isCat(v.label) || /_category$/.test(k) ? "category" : "barcode";
      const key = kind + "|" + String(v.label).replace(/\s*\((category|barcode)\)\s*/i, "");
      if (!seen.has(key)) seen.set(key, { ...v, kind, runId: r.id, startedAt: r.startedAt });
    }
    if (!catRun && (r.log || []).some((l) => / products from \d+ pages/.test(l))) {
      catRun = r;
      for (const l of r.log) { const m = l.match(/:\s*(\d+) products from/); if (m) { products += +m[1]; categories++; } }
    }
  }
  return { sources: [...seen.values()], products, categories };
}
function dubaiDay(iso) {
  if (!iso) return "";
  try { return new Date(iso).toLocaleDateString("en-CA", { timeZone: "Asia/Dubai" }); } catch (e) { return String(iso).slice(0, 10); }
}
function drawGlobalRows() {
  const sel = $("#ov-date"); if (!sel) return;
  const days = [...new Set(ovRows.map((r) => r.run_date).filter(Boolean))].sort().reverse();
  if (sel.options.length !== days.length + 1) {
    const keep = sel.value || days[0] || "";
    sel.innerHTML = days.map((d) => `<option value="${esc(d)}">${esc(d)}</option>`).join("") + `<option value="">${L("All days", "كل الأيام")} (${days.length})</option>`;
    sel.value = keep;
  }
  const q = ($("#ov-q")?.value || "").trim().toLowerCase(), day = sel.value;
  // one row per commodity; its chart follows the price over every saved day (up to the chosen day)
  const by = new Map();
  for (const r of ovRows) {
    const name = r.commodity || r.name || ""; if (!name) continue;
    const k = (r.category || "") + "|" + name + "|" + (r.unit || "");
    if (!by.has(k)) by.set(k, { k, name, category: r.category || "", unit: r.unit || "", pts: new Map() });
    const price = Number(r.price); if (Number.isFinite(price) && r.run_date) by.get(k).pts.set(r.run_date, { price, pct: r.pct, ytd: r.ytd });
  }
  gcSeries = [...by.values()].map((c) => ({ ...c, series: [...c.pts.entries()].filter(([d]) => !day || d <= day).sort((x, y) => x[0].localeCompare(y[0])) }))
    .filter((c) => c.series.length && (!q || [c.name, c.category].join(" ").toLowerCase().includes(q)))
    .sort((a, b) => a.category.localeCompare(b.category) || a.name.localeCompare(b.name));
  gcOpen = gcOpen && gcSeries.some((c) => c.k === gcOpen) ? gcOpen : null;
  $("#ov-rows").innerHTML = gcSeries.slice(0, 400).map((c, i) => `<tr class="gc-row" data-i="${i}" style="cursor:pointer">
    <td><b dir="auto">${esc(c.name)}</b></td><td>${esc(c.category)}</td><td class="ltr">${esc(c.unit)}</td>${gcSpark(c)}<td>${TE_EXCL.includes(c.category) ? `<span class="chip grey">${L("Not in index", "خارج المؤشر")}</span>` : `<span class="chip ok">${L("In index", "في المؤشر")}</span>`}</td></tr>`).join("") || `<tr><td colspan="6" class="empty">${L("No matching prices.", "لا أسعار مطابقة.")}</td></tr>`;
  $("#ov-rows").onclick = (e) => { const tr = e.target.closest(".gc-row"); if (tr) gcToggle(Number(tr.dataset.i), tr); };
  $("#ov-count").textContent = L(`${gcSeries.length.toLocaleString("en")} commodities · ${days.length} saved days (${days[days.length - 1] || ""} to ${days[0] || ""}) · select a commodity to open its full chart`, `${gcSeries.length.toLocaleString("en")} سلعة · ${days.length} يوماً محفوظاً (${days[days.length - 1] || ""} إلى ${days[0] || ""}) · انقر سلعة لفتح الرسم الكامل`) + (gcSeries.length > 400 ? L(" · first 400 shown", " · يظهر أول 400") : "");
}
let gcSeries = [], gcOpen = null, gcChart = null;
function gcSpark(c) {
  const v = c.series.map((x) => x[1].price), n = v.length, last = v[n - 1], first = v[0];
  const pct = n > 1 && first ? (last / first - 1) * 100 : 0;
  const col = n < 2 ? "var(--muted)" : pct > 0 ? "#1a8f4e" : pct < 0 ? "#c0392b" : "var(--muted)";
  const W = 180, H = 34, lo = Math.min(...v), hi = Math.max(...v), span = hi - lo || 1;
  const xy = v.map((y, i) => [n === 1 ? W / 2 : 4 + (i * (W - 8)) / (n - 1), H - 4 - ((y - lo) / span) * (H - 8)]);
  const line = n > 1 ? `<polyline fill="none" stroke="${col}" stroke-width="2" stroke-linejoin="round" points="${xy.map((p) => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ")}"/>` : "";
  const tip = c.series.map(([d, o]) => `${d}: ${o.price}`).join("\n");
  return `<td class="num" style="white-space:nowrap"><b>${last}</b><br><span style="color:${col};font-size:11px">${n > 1 ? (pct > 0 ? "▲ " : pct < 0 ? "▼ " : "") + pct.toFixed(2) + "%" : L("one day", "يوم واحد")}</span></td>
    <td class="ltr"><svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(c.name)}"><title>${esc(tip)}</title>${line}<circle cx="${xy[n - 1][0].toFixed(1)}" cy="${xy[n - 1][1].toFixed(1)}" r="3.2" fill="${col}"/></svg></td>`;
}
async function gcToggle(i, tr) {
  const c = gcSeries[i]; if (!c) return;
  const open = tr.nextElementSibling?.classList.contains("gc-detail");
  document.querySelectorAll(".gc-detail").forEach((x) => x.remove()); if (gcChart) { gcChart.destroy(); gcChart = null; }
  if (open) { gcOpen = null; return; }
  gcOpen = c.k;
  const d = document.createElement("tr"); d.className = "gc-detail";
  d.innerHTML = `<td colspan="6"><div class="ltr" style="position:relative;height:300px"><canvas id="gc-canvas"></canvas></div><p class="muted" style="margin:6px 0 0">${esc(c.name)} · ${esc(c.category)} · ${esc(c.unit)} · ${c.series.length} ${L("days", "يوماً")}</p></td>`;
  tr.after(d);
  try { await loadChartLib(); } catch (e) { d.querySelector("p").textContent = L("Could not load the chart library: ", "تعذّر تحميل مكتبة الرسم: ") + (e?.message || e); return; }
  gcChart = new window.Chart(d.querySelector("#gc-canvas"), { type: "line",
    data: { labels: c.series.map((x) => x[0]), datasets: [{ label: `${c.name} (${c.unit})`, data: c.series.map((x) => x[1].price), borderColor: "#1678be", backgroundColor: "rgba(22,120,190,.12)", fill: true, tension: 0.25, pointRadius: 4, borderWidth: 2 }] },
    options: { responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      plugins: { legend: { display: false }, tooltip: { callbacks: { afterLabel: (ctx) => { const o = c.series[ctx.dataIndex][1]; return L(`Daily change: ${o.pct ?? "-"}  ·  year to date: ${o.ytd ?? "-"}`, `التغير اليومي: ${o.pct ?? "-"}  ·  منذ بداية السنة: ${o.ytd ?? "-"}`); } } } },
      scales: { y: { title: { display: true, text: c.unit } } } } });
}
