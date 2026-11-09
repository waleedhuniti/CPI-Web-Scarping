
// ============================================================ app: shared components (charts, side panel, toggles)
const PALETTE = ["#1a75b8", "#0f5f8f", "#16a34a", "#d97706", "#dc2626", "#1b2a52", "#7c3aed", "#0891b2", "#64748b"];
// LineChart: inline SVG (never mirrored), y grid, area under the first line, points with tooltips, a summary label and a hidden table
function lineChart(o) {
  const W = 860, H = o.height || 300, padL = 52, padR = 18, padT = 14, padB = 34;
  const series = (o.series || []).filter((s) => s.points.length);
  if (!series.length) return `<p class="muted">${esc(o.empty || L("No data to draw.", "لا بيانات للرسم."))}</p>`;
  const xs = [...new Set(series.flatMap((s) => s.points.map((p) => p.x)))].sort();
  const ys = series.flatMap((s) => s.points.map((p) => p.y)).filter((v) => v != null && isFinite(v));
  let lo = Math.min(...ys), hi = Math.max(...ys); if (hi - lo < 1e-9) { lo -= 1; hi += 1; }
  const padY = (hi - lo) * 0.08; lo -= padY; hi += padY;
  const X = (x) => padL + (xs.length === 1 ? (W - padL - padR) / 2 : (xs.indexOf(x) * (W - padL - padR)) / (xs.length - 1));
  const Y = (y) => padT + (1 - (y - lo) / (hi - lo)) * (H - padT - padB);
  const fy = o.yFmt || ((v) => v.toFixed(1));
  const ticks = 5, grid = [];
  for (let i = 0; i <= ticks; i++) { const v = lo + ((hi - lo) * i) / ticks; grid.push(`<line x1="${padL}" x2="${W - padR}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}" stroke="#e2e8f0"/><text class="axis" x="${padL - 8}" y="${(Y(v) + 4).toFixed(1)}" text-anchor="end">${esc(fy(v))}</text>`); }
  const step = Math.max(1, Math.ceil(xs.length / 8));
  const xl = xs.map((x, i) => (i % step === 0 || i === xs.length - 1 ? `<text class="axis" x="${X(x).toFixed(1)}" y="${H - 10}" text-anchor="middle">${esc(o.xFmt ? o.xFmt(x) : x)}</text>` : "")).join("");
  const lines = series.map((s, si) => {
    const pts = s.points.filter((p) => p.y != null && isFinite(p.y)); const col = s.color || PALETTE[si % PALETTE.length];
    const d = pts.map((p, i) => `${i ? "L" : "M"}${X(p.x).toFixed(1)},${Y(p.y).toFixed(1)}`).join(" ");
    const area = si === 0 && pts.length > 1 && !o.noArea ? `<path d="${d} L${X(pts[pts.length - 1].x).toFixed(1)},${Y(lo).toFixed(1)} L${X(pts[0].x).toFixed(1)},${Y(lo).toFixed(1)} Z" fill="${col}" opacity=".08"/>` : "";
    const dots = pts.map((p) => `<circle cx="${X(p.x).toFixed(1)}" cy="${Y(p.y).toFixed(1)}" r="3.4" fill="${col}"><title>${esc(`${s.label} · ${o.xFmt ? o.xFmt(p.x) : p.x}: ${fy(p.y)}${p.n != null ? ` · n=${p.n}` : ""}`)}</title></circle>`).join("");
    return `${area}<path d="${d}" fill="none" stroke="${col}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>${dots}`;
  }).join("");
  const first = series[0].points[0], last = series[0].points[series[0].points.length - 1];
  const summary = o.summary || `${o.title || ""}: ${series.map((s) => `${s.label} ${fy(s.points[0].y)} → ${fy(s.points[s.points.length - 1].y)}`).join("; ")} (${o.xFmt ? o.xFmt(first.x) : first.x} – ${o.xFmt ? o.xFmt(last.x) : last.x})`;
  const legend = series.length > 1 ? `<div class="legend">${series.map((s, si) => `<span><i class="sw" style="background:${s.color || PALETTE[si % PALETTE.length]}"></i>${esc(s.label)}</span>`).join("")}</div>` : "";
  const table = `<div class="sr-only"><table><caption>${esc(o.title || "")}</caption><thead><tr><th scope="col">${esc(L("Date", "التاريخ"))}</th>${series.map((s) => `<th scope="col">${esc(s.label)}</th>`).join("")}</tr></thead><tbody>${xs.map((x) => `<tr><th scope="row">${esc(x)}</th>${series.map((s) => { const p = s.points.find((q) => q.x === x); return `<td>${p ? esc(fy(p.y)) : "—"}</td>`; }).join("")}</tr>`).join("")}</tbody></table></div>`;
  return `<div class="chart" ${o.id ? `id="${esc(o.id)}-svg"` : ""}><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(summary)}">${grid.join("")}${xl}${lines}</svg></div>${legend}${table}`;
}
// Donut + legend with count and share
function donutChart(items, title) {
  const total = items.reduce((n, x) => n + x.value, 0);
  if (!total) return `<p class="muted">${esc(L("Nothing to show yet.", "لا شيء لعرضه بعد."))}</p>`;
  const R = 70, C = 2 * Math.PI * R; let off = 0;
  const segs = items.map((x, i) => {
    const len = (x.value / total) * C, col = x.muted ? "#cbd5e1" : x.color || PALETTE[i % PALETTE.length];
    const s = `<circle r="${R}" cx="100" cy="100" fill="none" stroke="${col}" stroke-width="34" stroke-dasharray="${len.toFixed(2)} ${(C - len).toFixed(2)}" stroke-dashoffset="${(-off).toFixed(2)}" transform="rotate(-90 100 100)"><title>${esc(`${x.label}: ${fmtN(x.value)} (${((100 * x.value) / total).toFixed(1)}%)`)}</title></circle>`;
    off += len; return s;
  }).join("");
  const label = `${title}: ` + items.map((x) => `${x.label} ${fmtN(x.value)} (${((100 * x.value) / total).toFixed(1)}%)`).join(", ");
  return `<div class="donut-wrap"><div class="chart"><svg viewBox="0 0 200 200" role="img" aria-label="${esc(label)}" style="max-width:300px;margin-inline:auto">${segs}<text x="100" y="98" text-anchor="middle" style="font:800 22px var(--sans);fill:var(--fg)">${esc(fmtN(total))}</text><text x="100" y="118" text-anchor="middle" class="axis">${esc(L("total", "المجموع"))}</text></svg></div>
    <div class="donut-legend">${items.map((x, i) => `<div class="${x.muted ? "muted-item" : ""}"><span><i class="sw legend" style="display:inline-block;width:12px;height:12px;border-radius:50%;background:${x.muted ? "#cbd5e1" : x.color || PALETTE[i % PALETTE.length]};margin-inline-end:8px;vertical-align:-1px"></i><span dir="auto">${esc(x.label)}</span>${x.note ? ` <span class="chip grey">${esc(x.note)}</span>` : ""}</span><b>${fmtN(x.value)} <span class="muted">(${((100 * x.value) / total).toFixed(1)}%)</span></b></div>`).join("")}</div></div>`;
}
function sparkline(vals, W = 120, H = 30) {
  const pts = vals.map((v, i) => [i, v]).filter((p) => p[1] != null && isFinite(p[1]));
  if (pts.length < 2) return `<span class="muted">—</span>`;
  const v = pts.map((p) => p[1]), lo = Math.min(...v), hi = Math.max(...v), sp = hi - lo || 1, n = vals.length;
  const xy = pts.map(([i, y]) => [4 + (i * (W - 8)) / Math.max(1, n - 1), H - 4 - ((y - lo) / sp) * (H - 8)]);
  const up = v[v.length - 1] > v[0], col = Math.abs(v[v.length - 1] - v[0]) < 1e-9 ? "#64748b" : up ? "#b42318" : "#1f7a3a";
  return `<svg class="ltr" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(L(`trend ${v[0]} to ${v[v.length - 1]}`, `الاتجاه من ${v[0]} إلى ${v[v.length - 1]}`))}"><polyline fill="none" stroke="${col}" stroke-width="2" points="${xy.map((p) => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ")}"/></svg>`;
}
function segToggle(id, opts, value, label) {
  return `<div class="seg-toggle" role="group" aria-label="${esc(label || "")}" id="${esc(id)}">${opts.map(([v, t, icon]) => `<button type="button" data-v="${esc(v)}" aria-pressed="${v === value}">${icon ? ico(icon) : ""}${esc(t)}</button>`).join("")}</div>`;
}
function bindSeg(id, fn) { const g = document.getElementById(id); if (!g) return; g.onclick = (e) => { const b = e.target.closest("[data-v]"); if (!b) return; $$("button", g).forEach((x) => x.setAttribute("aria-pressed", String(x === b))); fn(b.dataset.v); }; }
// a stacked status bar with text labels
function stackBar(parts) {
  const tot = parts.reduce((n, p) => n + p.n, 0);
  return `<div class="stackbar" role="img" aria-label="${esc(parts.filter((p) => p.n).map((p) => `${p.label} ${p.n}`).join(", "))}">${parts.map((p) => (p.n ? `<i style="width:${((100 * p.n) / Math.max(1, tot)).toFixed(1)}%;background:${p.color}" title="${esc(`${p.label}: ${p.n}`)}"></i>` : "")).join("")}</div>
    <div class="legend" style="font-size:12px">${parts.filter((p) => p.n).map((p) => `<span><i class="sw" style="background:${p.color}"></i>${esc(p.label)} ${fmtN(p.n)}</span>`).join("")}</div>`;
}
// SidePanel: a dialog-like panel on the inline end; focus moves in and returns on close
let spReturn = null;
function openSidePanel(title, bodyHtml, onReady) {
  spReturn = document.activeElement;
  $("#sp-root").innerHTML = `<div class="sidepanel-back" data-close></div><section class="sidepanel" role="dialog" aria-modal="true" aria-labelledby="sp-title"><header><h2 id="sp-title">${esc(title)}</h2><button type="button" class="sq" id="sp-close" aria-label="${esc(L("Close", "إغلاق"))}">${ico("close")}</button></header><div class="sp-body" id="sp-body">${bodyHtml}</div></section>`;
  $("#sp-root [data-close]").onclick = closeSidePanel; $("#sp-close").onclick = closeSidePanel;
  $("#sp-root .sidepanel").addEventListener("keydown", (e) => { if (e.key === "Escape") closeSidePanel(); });
  $("#sp-close").focus();
  if (onReady) onReady($("#sp-body"));
}
function closeSidePanel() { $("#sp-root").innerHTML = ""; try { spReturn?.focus(); } catch (e) {} spReturn = null; }
// a toast that announces politely (the #toast element is aria-live)
const say = (m, bad) => toast(m, bad);
// the one-time "Where did it go?" note
function whereNote() {
  let off = false; try { off = localStorage.getItem("where-note-off") === "1"; } catch (e) {}
  if (off) return "";
  const li = (LANG === "ar" ? [
    "نظرة عامة ← لوحة المتابعة (شجرة COICOP داخل بطاقة «داخلي» مطوية في CPI)",
    "التشغيل والجدولة وتشغيل Apify ← الجداول (Apify كقسم «قديم» مطوي)",
    "السلة والكتالوج وصور المنتجات وقائمة سلع TrendX ← سجل الأسعار التاريخي › السلع ☰",
    "الـ Actors ← الكاشطات › Apify actors",
    "النتائج وتنزيلات Excel/Dataiku ← سجل التشغيلات (وتنزيلات الجدول في سجل الأسعار التاريخي)",
    "إعدادات المشروع وحذفه ← «إعدادات المشروع» أسفل القائمة الجانبية",
    "الكاشطات المخصصة ← الكاشطات (قائمة ومساحة عمل لكل مشروع)",
  ] : [
    "Overview → Dashboard (the CPI COICOP tree sits in a collapsed “Internal” card)",
    "Run, daily schedule and the Apify run → Schedules (Apify as a collapsed “Legacy” section)",
    "Basket, catalogue browser, product photos and the TrendX commodity list → Price History › Commodities ☰",
    "Actors → Scrapers › Apify actors",
    "Results and the Excel/Dataiku downloads → Price Logs (and the grid downloads on Price History)",
    "Project settings and delete project → “Project settings” at the foot of the sidebar",
    "Custom scrapers → Scrapers (list and workspace, per project)",
  ]);
  return `<section class="card where-note" id="where-note" aria-labelledby="where-h"><div class="card-h"><h2 id="where-h">${esc(L("Where did it go?", "أين ذهب؟"))}</h2><span class="spacer"></span><button type="button" id="where-close">${esc(L("Dismiss", "إخفاء"))}</button></div><ul>${li.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></section>`;
}
function bindWhereNote() { const b = $("#where-close"); if (b) b.onclick = () => { try { localStorage.setItem("where-note-off", "1"); } catch (e) {} $("#where-note")?.remove(); $("#main").focus(); }; }
