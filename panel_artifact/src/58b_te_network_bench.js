// ============================================================ TrendX: Network (dependency diagram, neural-network forecast) and Benchmarks
// Network: projects/te/network/latest {asset} → network.json built by scripts/trendx/network.py (nodes, edges, nn, examples).
// Benchmarks: projects/te/benchmarks/latest {asset} → benchmarks.json (GCC CPIs, world indices, our TrendX, refused sources).
// The Dubai PPI stays private: it is read from its own asset (tePpiLoad) and is never part of either file.
let teNet, teBench;                 // undefined = not read yet, null = no pointer, {error} = unreadable, else the file
async function teNetLoad(fresh) {
  if (teNet !== undefined && !fresh) return teNet;
  try { const ptr = await getDocStrict("projects/te/network/latest"); if (!ptr?.asset) { teNet = null; return null; }
    const r = await fetch("/_blob/" + ptr.asset); if (!r.ok) throw new Error("network file HTTP " + r.status);
    teNet = { ptr, ...(await r.json()) }; }
  catch (e) { teNet = { error: e?.message || String(e) }; }
  return teNet;
}
async function teBenchLoad(fresh) {
  if (teBench !== undefined && !fresh) return teBench;
  try { const ptr = await getDocStrict("projects/te/benchmarks/latest"); if (!ptr?.asset) { teBench = null; return null; }
    const r = await fetch("/_blob/" + ptr.asset); if (!r.ok) throw new Error("benchmarks file HTTP " + r.status);
    teBench = { ptr, ...(await r.json()) }; }
  catch (e) { teBench = { error: e?.message || String(e) }; }
  return teBench;
}
const nLabel = (n) => (n ? (LANG === "ar" ? n.label_ar || n.label_en : n.label_en || n.label_ar) || n.id : "—");
const nType = (t) => L({ commodity: "Commodity", cpi: "CPI division", ppi: "PPI activity" }[t] || t, { commodity: "سلعة", cpi: "قسم CPI", ppi: "نشاط PPI" }[t] || t);
const nTypeChip = (t) => chip(nType(t), t === "commodity" ? "blue" : t === "cpi" ? "ok" : "manual");
const nCat = (c) => (c === "CPI division" ? L("CPI divisions", "أقسام الرقم القياسي لأسعار المستهلك") : c === "PPI activity" ? L("PPI activities", "أنشطة الرقم القياسي لأسعار المنتجين") : teCatName(c));
const lagTxt = (lag) => (lag ? `t−${lag}` : "t");
const signCol = (s) => (s === "-" ? "#dc2626" : "#1a75b8");
const eNote = (e) => (LANG === "ar" ? e.note_ar || e.note_en : e.note_en || e.note_ar) || "";
let teNetUI = { id: null, min: 0.25, h: 1 };
const TE_NET_MIN = [0.25, 0.4, 0.6];

// ---------------- Network page
async function pgTeNetwork(r, seq) {
  $("#page").innerHTML = titleRow(L("Network", "الشبكة")) + `<div id="te-pg">${loadingHtml(L("Reading the network file…", "يُقرأ ملف الشبكة…"))}</div>`;
  const N = await teNetLoad(); if (!alive(seq)) return;
  if (N?.error) { $("#te-pg").innerHTML = errBox(L("The network file could not be read. ", "تعذّرت قراءة ملف الشبكة. ") + N.error, "tn-retry"); $("#tn-retry").onclick = () => { teNet = undefined; rerender(); }; return; }
  if (!N) { $("#te-pg").innerHTML = `<section class="card">${emptyHtml("hex", L("No network file yet", "لا ملف شبكة بعد"), L("Run scripts/trendx/network.py, upload its network.json as an asset and point projects/te/network/latest at it.", "شغّل scripts/trendx/network.py وارفع network.json كأصل واجعل projects/te/network/latest يشير إليه."))}</section>`; return; }
  let A = null; try { A = await teModel(); } catch (e) { A = null; }     // the store gives the history behind the NN chart; the page works without it
  const P0 = await tePpiLoad(); if (!alive(seq)) return; const P = P0 && !P0.error ? P0 : null;
  const nodes = N.nodes || [], edges = N.edges || [], byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
  const nn = N.nn || {};
  if (!teNetUI.id || !byId[teNetUI.id]) teNetUI.id = (N.examples || []).find((x) => byId[x]) || nodes[0]?.id;
  const groups = []; for (const n of nodes) { const g = n.type === "commodity" ? n.category : n.type === "cpi" ? "CPI division" : "PPI activity"; let x = groups.find((y) => y.g === g); if (!x) groups.push((x = { g, items: [] })); x.items.push(n); }
  groups.sort((a, b) => (a.g === "CPI division" ? 1 : a.g === "PPI activity" ? 2 : 0) - (b.g === "CPI division" ? 1 : b.g === "PPI activity" ? 2 : 0));
  $("#te-pg").innerHTML = `<section class="card filter-card"><div class="row">
      <label class="f" style="flex:1 1 280px"><span>${esc(L("Node", "العقدة"))}</span><select id="tn-id">${groups.map((g) => `<optgroup label="${esc(nCat(g.g))}">${g.items.map((n) => `<option value="${esc(n.id)}"${n.id === teNetUI.id ? " selected" : ""}>${esc(nLabel(n))}</option>`).join("")}</optgroup>`).join("")}</select></label>
      <label class="f"><span>${esc(L("Minimum score", "الحد الأدنى للدرجة"))}</span><select id="tn-min">${TE_NET_MIN.map((m) => `<option value="${m}"${m === teNetUI.min ? " selected" : ""}>${m}</option>`).join("")}</select></label>
      <label class="f"><span>${esc(L("Horizon (months)", "الأفق (أشهر)"))}</span>${segToggle("tn-h", [1, 2, 3].map((h) => [String(h), String(h)]), String(teNetUI.h), L("Horizon", "الأفق"))}</label>
      <span class="spacer"></span><span class="muted">${esc(L(`Built ${N.built} · window ${N.window?.from || "—"} to ${N.window?.to || "—"} · ${nodes.length} nodes · ${edges.length} edges`, `بُني ${N.built} · النافذة من ${N.window?.from || "—"} إلى ${N.window?.to || "—"} · ${nodes.length} عقدة · ${edges.length} رابطاً`))}</span></div></section>
    <div id="tn-body"></div>`;
  const draw = () => {
    const id = teNetUI.id, n = byId[id], min = teNetUI.min, H = teNetUI.h;
    const drv = edges.filter((e) => e.to === id && e.score >= min).sort((a, b) => b.score - a.score), imp = edges.filter((e) => e.from === id && e.score >= min).sort((a, b) => b.score - a.score);
    const all = edges.filter((e) => e.from === id || e.to === id).sort((a, b) => b.score - a.score);
    const our = nodes.filter((x) => x.type !== "commodity");
    $("#tn-body").innerHTML = `
      <section class="card"><div class="card-h"><h2>${esc(L(`Dependency diagram: ${nLabel(n)}`, `مخطط التبعية: ${nLabel(n)}`))}</h2>${nTypeChip(n.type)}<span class="spacer"></span><span class="muted">${esc(L(`${drv.length} drivers · ${imp.length} impacts at score ≥ ${min}`, `${drv.length} محركاً · ${imp.length} أثراً عند درجة ≥ ${min}`))}</span></div>
        ${teNetDiagram(byId, n, drv, imp)}
        <p class="chart-note" style="margin:8px 0 0">${esc(L("Drivers (inline start) move the node; impacts (inline end) are what it moves: other commodities, CPI divisions and PPI activities. Line thickness = score, blue = positive sign, red = negative; each label gives the lag (t−k) and the correlation r. Select a box for its details.", "المحركات (بداية السطر) تحرّك العقدة؛ والآثار (نهاية السطر) ما تحرّكه: سلع أخرى وأقسام CPI وأنشطة PPI. سمك الخط = الدرجة، الأزرق إشارة موجبة والأحمر سالبة؛ وكل وسم يعطي الإبطاء (t−k) ومعامل الارتباط r. اختر مربعاً لتفاصيله."))}</p></section>
      <section class="card"><div class="card-h"><h2>${esc(L("Neural-network forecast", "توقع الشبكة العصبية"))}</h2><span class="spacer"></span><span id="tn-nn-chip"></span></div><div id="tn-nn"></div></section>
      <section class="card"><div class="card-h"><h2>${esc(L(`Edges of ${nLabel(n)}`, `روابط ${nLabel(n)}`))}</h2><span class="spacer"></span><button type="button" class="ghost" id="tn-xlsx">${ico("file")}Excel</button><button type="button" class="ghost" id="tn-csv">CSV</button></div>
        <div class="tw tall"><table><caption class="sr-only">${esc(L("All edges of the selected node", "كل روابط العقدة المختارة"))}</caption><thead><tr><th scope="col">${esc(L("From", "من"))}</th><th scope="col">${esc(L("To", "إلى"))}</th><th scope="col" class="num">${esc(L("Lag", "الإبطاء"))}</th><th scope="col" class="num">r</th><th scope="col" class="num">β</th><th scope="col">${esc(L("Sign", "الإشارة"))}</th><th scope="col" class="num">${esc(L("Score", "الدرجة"))}</th><th scope="col">${esc(L("Note", "ملاحظة"))}</th></tr></thead><tbody>
        ${all.map((e) => `<tr${e.score < min ? ' class="muted-row"' : ""}><td><button type="button" class="link" data-tn="${esc(e.from)}">${esc(nLabel(byId[e.from]))}</button></td><td><button type="button" class="link" data-tn="${esc(e.to)}">${esc(nLabel(byId[e.to]))}</button></td><td class="num ltr">${esc(lagTxt(e.lag))}</td><td class="num">${sg(e.r, 2)}</td><td class="num">${sg(e.beta, 2)}</td><td>${chip(e.sign === "-" ? L("negative", "سالبة") : L("positive", "موجبة"), e.sign === "-" ? "bad" : "blue")} ${chip(e.kind === "driver" ? L("driver", "محرك") : L("impact", "أثر"), "grey")}</td><td class="num">${fmtN(e.score, 2)}</td><td class="note">${esc(eNote(e))}</td></tr>`).join("") || `<tr><td colspan="8" class="muted">${esc(L("No edges for this node.", "لا روابط لهذه العقدة."))}</td></tr>`}</tbody></table></div></section>
      <section class="card"><div class="card-h"><h2>${esc(L("Drivers of our numbers", "محركات أرقامنا"))}</h2><span class="spacer"></span><span class="muted">${esc(L("top 3 commodity drivers per CPI division and PPI activity", "أهم 3 سلع محرّكة لكل قسم CPI ونشاط PPI"))}</span></div>
        ${our.length ? `<div class="tw"><table><thead><tr><th scope="col">${esc(L("Node", "العقدة"))}</th><th scope="col">${esc(L("Type", "النوع"))}</th><th scope="col">${esc(L("Top drivers", "أهم المحركات"))}</th></tr></thead><tbody>
        ${our.map((x) => { const top = edges.filter((e) => e.to === x.id && byId[e.from]?.type === "commodity").sort((a, b) => b.score - a.score).slice(0, 3);
          return `<tr><td><button type="button" class="link" data-tn="${esc(x.id)}"><b>${esc(nLabel(x))}</b></button></td><td>${nTypeChip(x.type)}</td><td>${top.length ? top.map((e) => `<span class="chip ${e.sign === "-" ? "bad" : "blue"}" title="${esc(eNote(e))}">${esc(nLabel(byId[e.from]))} · ${esc(lagTxt(e.lag))} · r ${sg(e.r, 2)}</span>`).join(" ") : `<span class="muted">${esc(L("no commodity driver", "لا محرك سلعي"))}</span>`}</td></tr>`; }).join("")}</tbody></table></div>` : `<p class="muted" style="margin:0">${esc(L("The file has no CPI or PPI nodes.", "لا عقد CPI أو PPI في الملف."))}</p>`}</section>
      <section class="card"><div class="card-h"><h2>${esc(L("Methodology", "المنهجية"))}</h2></div><p style="margin:0;line-height:1.75">${esc((LANG === "ar" ? N.method_note_ar || N.method_note_en : N.method_note_en || N.method_note_ar) || "—")}</p>
        <p class="muted" style="margin:8px 0 0">${esc(L(`Built ${N.built}; window ${N.window?.from || "—"} to ${N.window?.to || "—"}. Commodity nodes are the TrendX store series; CPI nodes are UAE CPI divisions (GCC-Stat); PPI nodes are Dubai PPI activities (kept in this private portal).`, `بُني ${N.built}؛ النافذة من ${N.window?.from || "—"} إلى ${N.window?.to || "—"}. عقد السلع هي سلاسل مستودع TrendX؛ وعقد CPI أقسام الرقم القياسي لأسعار المستهلك في الإمارات (المركز الإحصائي الخليجي)؛ وعقد PPI أنشطة الرقم القياسي لأسعار المنتجين في دبي (تبقى في هذه البوابة الخاصة).`))}</p></section>`;
    teNetNN(byId, n, nn[id], H, A, P);
    $("#tn-body").onclick = (e) => { const b = e.target.closest("[data-tn]"); if (b && byId[b.dataset.tn]) teNodePanel(N, byId, b.dataset.tn, A, P); };
    const sheet = () => ({ title: `TrendX network edges: ${n.label_en || id}`, subtitle: `built ${N.built} • window ${N.window?.from}–${N.window?.to} • score threshold ${min}`, headers: ["From", "To", "Lag", "r", "beta", "Kind", "Sign", "Score", "Note"], widths: [22, 22, 6, 8, 8, 10, 6, 8, 60], priceCols: [],
      rows: all.map((e) => [byId[e.from]?.label_en || e.from, byId[e.to]?.label_en || e.to, e.lag, e.r, e.beta, e.kind, e.sign, e.score, e.note_en || ""]) });
    $("#tn-xlsx").onclick = () => offerXlsx(`TrendX network ${id}.xlsx`, sheet());
    $("#tn-csv").onclick = () => { const s = sheet(); offerFile(`trendx_network_${id}.csv`, toCsv(s.rows.map((row) => Object.fromEntries(s.headers.map((h, i) => [h, row[i]]))), s.headers)); };
  };
  $("#tn-id").onchange = (e) => { teNetUI.id = e.target.value; draw(); }; $("#tn-min").onchange = (e) => { teNetUI.min = +e.target.value; draw(); };
  bindSeg("tn-h", (v) => { teNetUI.h = +v; draw(); });
  draw();
}
// the dependency diagram: one horizontal SVG (wide screens) and one vertical SVG (phones); CSS shows one of them. Never mirrored:
// drivers are placed on the inline-start side by computing x from the page direction.
function teNetDiagram(byId, n, drv, imp) {
  const rtl = LANG === "ar", bw = 190, bh = 34, rh = 58;
  const box = (x, y, node, e, cls) => { const lbl = nLabel(node), t = lbl.length > 24 ? lbl.slice(0, 23) + "…" : lbl, col = node.type === "commodity" ? "#1a75b8" : node.type === "cpi" ? "#16a34a" : "#7c3aed";
    return `<g class="node ${cls}" data-tn="${esc(node.id)}" tabindex="0" role="button" aria-label="${esc(lbl)}"><rect x="${x - bw / 2}" y="${y - bh / 2}" width="${bw}" height="${bh}" rx="9" fill="#fff" stroke="${col}" stroke-width="${cls === "sel" ? 3 : 1.6}"/><text x="${x}" y="${y + 4.5}" text-anchor="middle">${esc(t)}</text>${e ? `<title>${esc(`${lbl} · ${lagTxt(e.lag)} · r ${sg(e.r, 2)} · β ${sg(e.beta, 2)} · ${L("score", "الدرجة")} ${fmtN(e.score, 2)}${eNote(e) ? " · " + eNote(e) : ""}`)}</title>` : ""}</g>`; };
  const edgeLbl = (x, y, e, anchor = "middle") => `<text class="lbl" x="${x}" y="${y}" text-anchor="${anchor}">${esc(`${lagTxt(e.lag)} · r ${sg(e.r, 2)}`)}</text>`;
  const sw = (e) => (1 + e.score * 5).toFixed(1);
  // horizontal
  const W = 860, rows = Math.max(drv.length, imp.length, 1), Hh = rows * rh + 32, cy = Hh / 2, xS = rtl ? W - 110 : 110, xE = rtl ? 110 : W - 110, xC = W / 2;
  const ys = (k, i) => 16 + bh / 2 + (rows - k) * rh / 2 + i * rh;
  const hPath = (x1, y1, x2, y2) => `M${x1},${y1} C${(x1 + x2) / 2},${y1} ${(x1 + x2) / 2},${y2} ${x2},${y2}`;
  let h = "";
  // each edge label sits beside its own box (own row), so labels never pile up at the centre
  drv.forEach((e, i) => { const y = ys(drv.length, i), x1 = xS + (rtl ? -bw / 2 : bw / 2), x2 = xC - (rtl ? -bw / 2 : bw / 2); h += `<path d="${hPath(x1, y, x2, cy)}" fill="none" stroke="${signCol(e.sign)}" stroke-width="${sw(e)}" opacity=".75"/>${edgeLbl(xS, y + bh / 2 + 12, e)}`; });
  imp.forEach((e, i) => { const y = ys(imp.length, i), x1 = xC + (rtl ? -bw / 2 : bw / 2), x2 = xE - (rtl ? -bw / 2 : bw / 2); h += `<path d="${hPath(x1, cy, x2, y)}" fill="none" stroke="${signCol(e.sign)}" stroke-width="${sw(e)}" opacity=".75"/>${edgeLbl(xE, y + bh / 2 + 12, e)}`; });
  drv.forEach((e, i) => { h += box(xS, ys(drv.length, i), byId[e.from] || { id: e.from, label_en: e.from, type: "commodity" }, e, "drv"); });
  imp.forEach((e, i) => { h += box(xE, ys(imp.length, i), byId[e.to] || { id: e.to, label_en: e.to, type: "commodity" }, e, "imp"); });
  h += box(xC, cy, n, null, "sel");
  const head = (x, t) => `<text class="lbl" x="${x}" y="10" text-anchor="middle" style="font-weight:800">${esc(t)}</text>`;
  if (!drv.length) h += `<text class="lbl" x="${xS}" y="${cy + 4}" text-anchor="middle">${esc(L("no driver at this score", "لا محرك عند هذه الدرجة"))}</text>`;
  if (!imp.length) h += `<text class="lbl" x="${xE}" y="${cy + 4}" text-anchor="middle">${esc(L("no impact at this score", "لا أثر عند هذه الدرجة"))}</text>`;
  const horiz = `<svg viewBox="0 -6 ${W} ${Hh + 10}" role="img" aria-label="${esc(L(`Dependency diagram of ${nLabel(n)}: ${drv.length} drivers, ${imp.length} impacts`, `مخطط تبعية ${nLabel(n)}: ${drv.length} محركاً و${imp.length} أثراً`))}">${head(xS, L("Drivers", "المحركات"))}${head(xE, L("Impacts", "الآثار"))}${h}</svg>`;
  // vertical (phones): drivers above, node, impacts below
  const Wv = 400, xv = Wv / 2, step = 52, yD0 = 46, yC = yD0 + Math.max(drv.length, 0) * step + 36, yI0 = yC + 84, Hv = yI0 + Math.max(imp.length, 0) * step + 8;
  let v = `<text class="lbl" x="${xv}" y="12" text-anchor="middle" style="font-weight:800">${esc(L("Drivers", "المحركات"))}</text>`;
  drv.forEach((e, i) => { const y = yD0 + i * step; v += `<path d="M${xv + (i % 2 ? 60 : -60)},${y + bh / 2} C${xv + (i % 2 ? 60 : -60)},${(y + yC) / 2} ${xv},${(y + yC) / 2} ${xv},${yC - bh / 2}" fill="none" stroke="${signCol(e.sign)}" stroke-width="${sw(e)}" opacity=".6"/>`; });
  imp.forEach((e, i) => { const y = yI0 + i * step; v += `<path d="M${xv},${yC + bh / 2} C${xv},${(y + yC) / 2} ${xv + (i % 2 ? 60 : -60)},${(y + yC) / 2} ${xv + (i % 2 ? 60 : -60)},${y - bh / 2}" fill="none" stroke="${signCol(e.sign)}" stroke-width="${sw(e)}" opacity=".6"/>`; });
  drv.forEach((e, i) => { const y = yD0 + i * step, x = xv + (i % 2 ? 60 : -60); v += box(x, y, byId[e.from] || { id: e.from, label_en: e.from, type: "commodity" }, e, "drv") + edgeLbl(x + (i % 2 ? -bw / 2 - 4 : bw / 2 + 4), y + 4, e, i % 2 ? "end" : "start"); });
  imp.forEach((e, i) => { const y = yI0 + i * step, x = xv + (i % 2 ? 60 : -60); v += box(x, y, byId[e.to] || { id: e.to, label_en: e.to, type: "commodity" }, e, "imp") + edgeLbl(x + (i % 2 ? -bw / 2 - 4 : bw / 2 + 4), y + 4, e, i % 2 ? "end" : "start"); });
  v += box(xv, yC, n, null, "sel");
  if (!drv.length) v += `<text class="lbl" x="${xv}" y="${yD0 + 4}" text-anchor="middle">${esc(L("no driver at this score", "لا محرك عند هذه الدرجة"))}</text>`;
  v += `<text class="lbl" x="${xv}" y="${yI0 - 30}" text-anchor="middle" style="font-weight:800">${esc(L("Impacts", "الآثار"))}</text>`;
  if (!imp.length) v += `<text class="lbl" x="${xv}" y="${yI0 + 4}" text-anchor="middle">${esc(L("no impact at this score", "لا أثر عند هذه الدرجة"))}</text>`;
  const vert = `<svg viewBox="0 0 ${Wv} ${Hv}" role="img" aria-hidden="true">${v}</svg>`;
  return `<div class="netdiag"><div class="chart netdiag-h">${horiz}</div><div class="chart netdiag-v">${vert}</div></div>`;
}
// history of a node for the NN chart: commodities from the store (2024 = 100), PPI activities from the private PPI file rebased
// to their own 2024 mean, CPI divisions have no history in the portal (forecast only)
function teNodeHistory(node, A, P) {
  if (node.type === "commodity" && A) { const s = teSid(A, node.id); if (s) return { months: A.M, v: s.v, last: A.last, base: L("2024 = 100", "2024 = 100") }; }
  if (node.type === "ppi" && P) { const code = node.id.replace(/^ppi_/, ""), s = P.S[code]; if (s) { const b = meanA(P.months.map((m, j) => (m.startsWith("2024") ? s.v[j] : null)).filter((x) => x != null)); return { months: P.months, v: s.v.map((x) => (x != null && b ? (x / b) * 100 : null)), last: P.last, base: L("rebased to its 2024 mean", "معاد قياسه إلى متوسط 2024") }; } }
  return null;
}
function teNetNN(byId, n, k, H, A, P) {
  const box = $("#tn-nn"), chipEl = $("#tn-nn-chip"); if (!box) return;
  if (!k) { chipEl.innerHTML = ""; box.innerHTML = `<p class="muted" style="margin:0">${esc(L("No neural-network target for this node in the file. Targets: ", "لا هدف للشبكة العصبية لهذه العقدة في الملف. الأهداف: "))}${Object.keys(teNet?.nn || {}).map((id) => `<button type="button" class="link" data-tn="${esc(id)}">${esc(nLabel(byId[id]))}</button>`).join(", ") || "—"}</p>`; return; }
  const bt = k.backtest || {}, hs = k.h || [1, 2, 3], hi = Math.max(0, hs.indexOf(H)), fc = k.forecast || [], f = fc[hi];
  const skill = bt.skill_vs_naive?.[hi];
  chipEl.innerHTML = skill == null ? "" : chip(L(`skill vs naive at h=${H}: ${sg(skill * 100, 0)}%`, `المهارة مقابل البسيط عند h=${H}: ${sg(skill * 100, 0)}%`), skill > 0 ? "ok" : "warn");
  const hist = teNodeHistory(n, A, P);
  let series = [];
  if (hist) { const pts = []; for (let i = Math.max(0, hist.last - 35); i <= hist.last; i++) if (hist.v[i] != null) pts.push({ x: hist.months[i], y: hist.v[i] }); series.push({ label: L("History", "التاريخ"), points: pts });
    const o = pts[pts.length - 1]; if (o && fc.length) series.push({ label: L("NN forecast (mean)", "توقع الشبكة (المتوسط)"), color: "#d97706", points: [o, ...fc.map((p) => ({ x: p.period, y: p.mean }))] }, { label: L("Lower 80%", "الحد الأدنى 80%"), color: "#cbd5e1", points: [o, ...fc.map((p) => ({ x: p.period, y: p.lo80 }))] }, { label: L("Upper 80%", "الحد الأعلى 80%"), color: "#cbd5e1", points: [o, ...fc.map((p) => ({ x: p.period, y: p.hi80 }))] }); }
  else if (fc.length) series = [{ label: L("NN forecast (mean)", "توقع الشبكة (المتوسط)"), color: "#d97706", points: fc.map((p) => ({ x: p.period, y: p.mean })) }, { label: L("Lower 80%", "الحد الأدنى 80%"), color: "#cbd5e1", points: fc.map((p) => ({ x: p.period, y: p.lo80 })) }, { label: L("Upper 80%", "الحد الأعلى 80%"), color: "#cbd5e1", points: fc.map((p) => ({ x: p.period, y: p.hi80 })) }];
  const feats = (k.features || []).map((x) => `${nLabel(byId[x.node])} (${(x.lags || []).map((l) => lagTxt(l)).join(", ")})`);
  box.innerHTML = `<div class="kpis four" style="margin-bottom:12px">
      ${kpiHtml({ id: "tn-k1", icon: "chart", tint: "amber", label: L(`NN forecast · h=${H}${f ? " · " + fmtYM(f.period) : ""}`, `توقع الشبكة · h=${H}${f ? " · " + fmtYM(f.period) : ""}`), value: f ? fmtN(f.mean, 1) : "—", sub: f ? L(`80% band ${fmtN(f.lo80, 1)}–${fmtN(f.hi80, 1)}`, `نطاق 80% ${fmtN(f.lo80, 1)}–${fmtN(f.hi80, 1)}`) : "" })}
      ${kpiHtml({ id: "tn-k2", icon: "check", tint: skill > 0 ? "green" : "red", label: L("NN MAE %", "خطأ الشبكة MAE %"), value: fmtN(bt.nn_mae_pct?.[hi], 2), sub: L(`naive ${fmtN(bt.naive_mae_pct?.[hi], 2)} · ridge ${fmtN(bt.ridge_mae_pct?.[hi], 2)}`, `البسيط ${fmtN(bt.naive_mae_pct?.[hi], 2)} · ريدج ${fmtN(bt.ridge_mae_pct?.[hi], 2)}`) })}
      ${kpiHtml({ id: "tn-k3", icon: "calendar", label: L("Backtest origins", "أصول الاختبار الرجعي"), value: fmtN(bt.origins), sub: L("rolling, out of sample", "متدحرجة، خارج العينة") })}
      ${kpiHtml({ id: "tn-k4", icon: "hex", label: L("Input features", "سمات الإدخال"), value: fmtN((k.features || []).reduce((s, x) => s + (x.lags || []).length, 0)), sub: L(`${(k.features || []).length} nodes`, `${(k.features || []).length} عقدة`) })}</div>
    ${lineChart({ height: 260, title: nLabel(n), xFmt: fmtYM, yFmt: (v) => v.toFixed(1), noArea: true, series, empty: L("No forecast in the file.", "لا توقع في الملف.") })}
    ${hist ? `<p class="chart-note" style="margin:6px 0 0">${esc(L(`History: ${hist.base}, last 36 months to ${fmtYM(hist.months[hist.last])}.`, `التاريخ: ${hist.base}، آخر 36 شهراً حتى ${fmtYM(hist.months[hist.last])}.`))}</p>` : `<p class="chart-note" style="margin:6px 0 0">${esc(L("The portal holds no history for this node; the chart shows the forecast only.", "لا تاريخ لهذه العقدة في البوابة؛ يعرض الرسم التوقع فقط."))}</p>`}
    <div class="grid two" style="margin-top:12px">
      <div><div class="tw"><table><caption class="sr-only">${esc(L("Backtest accuracy per horizon", "دقة الاختبار الرجعي لكل أفق"))}</caption><thead><tr><th scope="col">${esc(L("Horizon", "الأفق"))}</th><th scope="col" class="num">NN MAE %</th><th scope="col" class="num">${esc(L("Ridge MAE %", "ريدج MAE %"))}</th><th scope="col" class="num">${esc(L("Naive MAE %", "البسيط MAE %"))}</th><th scope="col" class="num">${esc(L("Skill vs naive", "المهارة مقابل البسيط"))}</th><th scope="col" class="num">${esc(L("Forecast", "التوقع"))}</th></tr></thead><tbody>
        ${hs.map((h, i) => `<tr${i === hi ? ' class="best"' : ""}><td>h+${h}${fc[i] ? ` <span class="muted">${esc(fmtYM(fc[i].period))}</span>` : ""}</td><td class="num">${fmtN(bt.nn_mae_pct?.[i], 2)}</td><td class="num">${fmtN(bt.ridge_mae_pct?.[i], 2)}</td><td class="num">${fmtN(bt.naive_mae_pct?.[i], 2)}</td><td class="num">${skillCell(bt.skill_vs_naive?.[i])}</td><td class="num">${fc[i] ? `<b>${fmtN(fc[i].mean, 1)}</b> <span class="muted">${fmtN(fc[i].lo80, 1)}–${fmtN(fc[i].hi80, 1)}</span>` : "—"}</td></tr>`).join("")}</tbody></table></div>
        <p class="muted" style="margin:6px 0 0">${esc(L("MAE %: mean absolute error in % of the level, over rolling origins. Skill = 1 − NN MAE / naive MAE (positive = better than persistence). Ridge: the linear benchmark on the same features.", "MAE %: متوسط الخطأ المطلق كنسبة من المستوى عبر أصول متدحرجة. المهارة = 1 − خطأ الشبكة / خطأ البسيط (الموجب أفضل من الاستمرارية). ريدج: المعيار الخطي على السمات نفسها."))}</p></div>
      <div><h3 style="margin:0 0 6px">${esc(L("Verdict", "الخلاصة"))}</h3><p style="margin:0 0 10px;line-height:1.7">${esc((LANG === "ar" ? k.verdict_ar || k.verdict_en : k.verdict_en || k.verdict_ar) || "—")}</p>
        <h3 style="margin:0 0 6px">${esc(L("Feature importance", "أهمية السمات"))}</h3>${(k.importance || []).length ? (k.importance || []).slice(0, 8).map((x) => `<div class="mov"><span class="nm" title="${esc(nLabel(byId[x.node]))}">${esc(nLabel(byId[x.node]))} <span class="muted ltr">${esc(lagTxt(x.lag))}</span></span><span class="bar"><i style="width:${(Math.max(0, Math.min(1, x.score)) * 100).toFixed(0)}%;background:#1a75b8"></i></span><span class="v">${fmtN(x.score, 2)}</span></div>`).join("") : `<p class="muted">—</p>`}
        <p class="muted" style="margin:8px 0 0">${esc(L("Inputs: ", "المدخلات: "))}${esc(feats.join("; ") || "—")}</p></div></div>`;
}
// skill cell: positive skill is good → green (the sign class is the inverse of a price change)
const skillCell = (x) => (x == null ? "—" : `<span class="${x > 0.005 ? "chg-dn" : x < -0.005 ? "chg-up" : ""}">${sg(x * 100, 0)}%</span>`);
function teNodePanel(N, byId, id, A, P) {
  const n = byId[id], edges = (N.edges || []).filter((e) => e.from === id || e.to === id).sort((a, b) => b.score - a.score), k = N.nn?.[id], hist = teNodeHistory(n, A, P);
  openSidePanel(nLabel(n), `<div class="stack">
    <div class="row">${nTypeChip(n.type)}${chip(nCat(n.category), "grey")}<span class="muted">n = ${fmtN(n.n_obs)}</span></div>
    <dl class="kv"><dt>${esc(L("Node id", "معرّف العقدة"))}</dt><dd class="mono">${esc(n.id)}</dd><dt>${esc(L("Source", "المصدر"))}</dt><dd>${esc(n.source || "—")}</dd>${k ? `<dt>${esc(L("NN target", "هدف الشبكة"))}</dt><dd>${esc(L(`yes · ${k.backtest?.origins ?? "—"} origins · skill h1 ${k.backtest?.skill_vs_naive?.[0] == null ? "—" : sg(k.backtest.skill_vs_naive[0] * 100, 0) + "%"}`, `نعم · ${k.backtest?.origins ?? "—"} أصلاً · المهارة h1 ${k.backtest?.skill_vs_naive?.[0] == null ? "—" : sg(k.backtest.skill_vs_naive[0] * 100, 0) + "%"}`))}</dd>` : ""}</dl>
    ${hist ? lineChart({ height: 200, title: nLabel(n), xFmt: fmtYM, yFmt: (v) => v.toFixed(1), series: [{ label: hist.base, points: hist.months.map((m, i) => ({ x: m, y: hist.v[i] })).filter((p) => p.y != null).slice(-36) }] }) : ""}
    <div class="tw tall"><table><caption class="sr-only">${esc(L("Edges", "الروابط"))}</caption><thead><tr><th scope="col">${esc(L("Edge", "الرابط"))}</th><th scope="col" class="num">${esc(L("Lag", "الإبطاء"))}</th><th scope="col" class="num">r</th><th scope="col" class="num">${esc(L("Score", "الدرجة"))}</th></tr></thead><tbody>
      ${edges.map((e) => `<tr><td>${e.to === id ? `<span class="muted">${esc(L("from", "من"))}</span> ${esc(nLabel(byId[e.from]))}` : `<span class="muted">${esc(L("to", "إلى"))}</span> ${esc(nLabel(byId[e.to]))}`} ${chip(e.sign === "-" ? "−" : "+", e.sign === "-" ? "bad" : "blue")}</td><td class="num ltr">${esc(lagTxt(e.lag))}</td><td class="num">${sg(e.r, 2)}</td><td class="num">${fmtN(e.score, 2)}</td></tr>`).join("") || `<tr><td colspan="4" class="muted">${esc(L("No edges.", "لا روابط."))}</td></tr>`}</tbody></table></div>
    ${id !== teNetUI.id ? `<button type="button" class="primary" id="tn-sel">${esc(L("Show this node", "اعرض هذه العقدة"))}</button>` : ""}</div>`, (box) => { const b = $("#tn-sel", box); if (b) b.onclick = () => { closeSidePanel(); teNetUI.id = id; const sel = $("#tn-id"); if (sel) sel.value = id; rerender(); }; });
}

// ---------------- Benchmarks page
let teBenchUI = { on1: null, on2: null, range: "all", ppi: false };
const bName = (s) => (LANG === "ar" ? s.name_ar || s.name_en : s.name_en || s.name_ar) || s.id;
const bGroup = (g) => L({ gcc: "GCC", world: "World", ours: "Ours" }[g] || g, { gcc: "الخليج", world: "العالم", ours: "لدينا" }[g] || g);
const bKind = (k) => L({ cpi: "CPI", commodity_index: "Commodity index", ppi: "PPI", trendx: "TrendX" }[k] || k, { cpi: "الرقم القياسي لأسعار المستهلك", commodity_index: "مؤشر سلع", ppi: "الرقم القياسي لأسعار المنتجين", trendx: "TrendX" }[k] || k);
const bBase = (B) => (!B.base || /^mean of 2024 = 100$/i.test(B.base) ? L("mean of 2024 = 100", "متوسط 2024 = 100") : B.base);
const bLast = (s, j = 2) => { const o = (s.obs || []).filter((x) => x[j] != null); return o.length ? o[o.length - 1] : null; };
const bAt = (s, ym, j = 2) => { const o = (s.obs || []).find((x) => x[0] === ym); return o ? o[j] : null; };
async function pgTeBenchmarks(r, seq) {
  $("#page").innerHTML = titleRow(L("Benchmarks", "المقارنات")) + `<div id="te-pg">${loadingHtml(L("Reading the benchmarks file…", "يُقرأ ملف المقارنات…"))}</div>`;
  const B = await teBenchLoad(); if (!alive(seq)) return;
  if (B?.error) { $("#te-pg").innerHTML = errBox(L("The benchmarks file could not be read. ", "تعذّرت قراءة ملف المقارنات. ") + B.error, "tb-retry"); $("#tb-retry").onclick = () => { teBench = undefined; rerender(); }; return; }
  if (!B) { $("#te-pg").innerHTML = `<section class="card">${emptyHtml("chart", L("No benchmarks file yet", "لا ملف مقارنات بعد"), L("Run scripts/trendx/benchmarks.py, upload its benchmarks.json as an asset and point projects/te/benchmarks/latest at it.", "شغّل scripts/trendx/benchmarks.py وارفع benchmarks.json كأصل واجعل projects/te/benchmarks/latest يشير إليه."))}</section>`; return; }
  const P0 = await tePpiLoad(); if (!alive(seq)) return; const P = P0 && !P0.error ? P0 : null;
  const S = B.series || [], gcc = S.filter((s) => s.group === "gcc"), world = S.filter((s) => s.group === "world"), ours = S.filter((s) => s.group === "ours"), tx = ours.find((s) => s.kind === "trendx") || ours[0];
  const refused = B.refused || [];
  // the private Dubai PPI general index, rebased to its own 2024 mean (never in the file)
  let ppiS = null; if (P?.S?.X) { const x = P.S.X, b = meanA(P.months.map((m, j) => (m.startsWith("2024") ? x.v[j] : null)).filter((v) => v != null)); if (b) ppiS = { id: "__ppi", group: "ours", country: "AE-DU", name_en: "Dubai PPI (X)", name_ar: "الرقم القياسي لأسعار المنتجين في دبي (X)", kind: "ppi", source: L("private portal asset", "أصل البوابة الخاصة"), native_base: P.meta?.base || "—", obs: P.months.map((m, j) => [m, x.v[j], x.v[j] != null ? (x.v[j] / b) * 100 : null]), priv: true }; }
  if (!teBenchUI.on1) teBenchUI.on1 = new Set([...(tx ? [tx.id] : []), ...gcc.filter((s) => s.kind === "cpi" && /^gcc_[a-z]{3}_cpi$/.test(s.id)).map((s) => s.id)]);   // all-items lines only; divisions, World Bank and IMF duplicates start off
  if (!teBenchUI.on2) teBenchUI.on2 = new Set([...(tx ? [tx.id] : []), ...world.map((s) => s.id)]);
  const lastTx = tx ? bLast(tx) : null, prevTx = tx && lastTx ? bAt(tx, ymAdd(lastTx[0], -1)) : null;
  $("#te-pg").innerHTML = `<div class="kpis four" style="margin-bottom:4px">
      ${kpiHtml({ id: "tb-k1", icon: "trend", label: L("TrendX index, latest", "مؤشر TrendX، الأحدث"), value: lastTx ? fmtN(lastTx[2], 1) : "—", sub: lastTx ? L(`${fmtYM(lastTx[0])} · m/m ${sg(pct(lastTx[2], prevTx), 1)}% · ${bBase(B)}`, `${fmtYM(lastTx[0])} · شهري ${sg(pct(lastTx[2], prevTx), 1)}% · ${bBase(B)}`) : L("no TrendX series in the file", "لا سلسلة TrendX في الملف") })}
      ${kpiHtml({ id: "tb-k2", icon: "list", tint: "green", label: L("GCC series", "سلاسل الخليج"), value: fmtN(gcc.length), sub: [...new Set(gcc.map((s) => s.country))].join(" · ") })}
      ${kpiHtml({ id: "tb-k3", icon: "hex", tint: "blue", label: L("World series", "السلاسل العالمية"), value: fmtN(world.length), sub: [...new Set(world.map((s) => s.source))].slice(0, 3).join(" · ") })}
      ${kpiHtml({ id: "tb-k4", icon: "ban", tint: refused.length ? "red" : "green", label: L("Refused sources", "مصادر مرفوضة"), value: fmtN(refused.length), sub: refused.length ? refused.map((x) => x.status).join(" · ") : L("every source answered", "استجابت كل المصادر") })}</div>
    <section class="card filter-card"><div class="row">${segToggle("tb-range", [["all", L("Since 2015", "منذ 2015")], ["5y", L("5 years", "5 سنوات")], ["2y", L("24 months", "24 شهراً")]], teBenchUI.range, L("Range", "المدى"))}<span class="spacer"></span><span class="muted">${esc(L(`Built ${B.built} · ${bBase(B)}`, `بُني ${B.built} · ${bBase(B)}`))}</span></div></section>
    <section class="card"><div class="card-h"><h2>${esc(L("TrendX vs GCC CPIs (2024 = 100)", "TrendX مقابل الأرقام القياسية لأسعار المستهلك في الخليج (2024 = 100)"))}</h2></div><div class="chips" id="tb-c1" role="group" aria-label="${esc(L("Series shown", "السلاسل المعروضة"))}"></div><div id="tb-ch1" style="margin-top:10px"></div></section>
    <section class="card"><div class="card-h"><h2>${esc(L("TrendX vs world commodity indices (2024 = 100)", "TrendX مقابل مؤشرات السلع العالمية (2024 = 100)"))}</h2></div><div class="chips" id="tb-c2" role="group" aria-label="${esc(L("Series shown", "السلاسل المعروضة"))}"></div><div id="tb-ch2" style="margin-top:10px"></div>
      ${ppiS ? `<p class="muted" style="margin:8px 0 0">${esc(L("Dubai PPI (X): read from the private PPI asset and rebased to its own 2024 mean; it is not part of the benchmarks file.", "الرقم القياسي لأسعار المنتجين في دبي (X): يُقرأ من أصل PPI الخاص ويُعاد قياسه إلى متوسط 2024 الخاص به؛ وليس جزءاً من ملف المقارنات."))}</p>` : ""}</section>
    <section class="card"><div class="card-h"><h2>${esc(L("Comparison", "المقارنة"))}</h2><span class="spacer"></span><button type="button" class="ghost" id="tb-xlsx">${ico("file")}Excel</button><button type="button" class="ghost" id="tb-csv">CSV</button></div><div id="tb-table"></div>
      <p class="muted" style="margin:0">${esc(L("2024 = 100 is computed only when all twelve months of 2024 exist on one base; otherwise the cell is empty and the lag note says why. m/m and y/y use native values. Change since Jan 2024 uses the rebased series.", "يُحسب 2024 = 100 فقط حين تتوفر أشهر 2024 الاثنا عشر على أساس واحد؛ وإلا تبقى الخلية فارغة وتوضح ملاحظة التأخر السبب. الشهري والسنوي بالقيم الأصلية، والتغير منذ يناير 2024 بالسلسلة المعاد قياسها."))}</p></section>
    <div class="grid two">
      <section class="card"><div class="card-h"><h2>${esc(L("Refused sources", "المصادر المرفوضة"))}</h2></div>${refused.length ? `<div class="tw"><table><thead><tr><th scope="col">${esc(L("Source", "المصدر"))}</th><th scope="col">${esc(L("Status", "الحالة"))}</th><th scope="col">${esc(L("Note", "ملاحظة"))}</th></tr></thead><tbody>${refused.map((x) => `<tr><td><b>${esc(x.source)}</b><br><a class="ltr" href="${esc(x.url)}" target="_blank" rel="noopener" style="font-size:12px;overflow-wrap:anywhere;word-break:break-all">${esc(x.url)}</a></td><td>${chip(x.status, "bad")}</td><td class="note">${esc(x.note || "")}</td></tr>`).join("")}</tbody></table></div><p class="muted" style="margin:8px 0 0">${esc(L("A refused page stays unread: nothing is retried from elsewhere and no value is invented.", "الصفحة المرفوضة تبقى غير مقروءة: لا إعادة محاولة من مكان آخر ولا اختلاق قيمة."))}</p>` : `<p class="muted" style="margin:0">${esc(L("No source refused the request in this build.", "لم يرفض أي مصدر الطلب في هذا البناء."))}</p>`}</section>
      <section class="card"><div class="card-h"><h2>${esc(L("Sources and licences", "المصادر والرخص"))}</h2></div><div class="tw tall"><table><thead><tr><th scope="col">${esc(L("Series", "السلسلة"))}</th><th scope="col">${esc(L("Source", "المصدر"))}</th><th scope="col">${esc(L("Licence", "الرخصة"))}</th></tr></thead><tbody>${S.map((s) => `<tr><td><b>${esc(bName(s))}</b><br><span class="muted">${esc(s.source_series || "")}</span></td><td>${s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.source)}</a>` : esc(s.source || "—")}</td><td>${esc(s.licence || "—")}</td></tr>`).join("")}</tbody></table></div>${B.note ? `<p class="muted" style="margin:8px 0 0">${esc(B.note)}</p>` : ""}</section>
    </div>`;
  const from = () => (teBenchUI.range === "all" ? "0000-00" : teBenchUI.range === "5y" ? ymAdd(todayDubai().slice(0, 7), -60) : ymAdd(todayDubai().slice(0, 7), -24));
  const chipsOf = (list, on, id) => `${list.map((s, i) => `<button type="button" class="chipbtn" data-id="${esc(s.id)}" aria-pressed="${on.has(s.id)}"${s.priv ? ` title="${esc(L("private: Dubai PPI asset", "خاص: أصل PPI دبي"))}"` : ""}><i class="sw" style="background:${s.id === tx?.id ? "#d97706" : PALETTE[i % PALETTE.length]}"></i>${esc(bName(s))}</button>`).join("")}`;
  const chartOf = (list, on, title) => { const f0 = from(); return lineChart({ height: 300, title, xFmt: fmtYM, yFmt: (v) => v.toFixed(0), noArea: true, empty: L("Pick at least one series.", "اختر سلسلة واحدة على الأقل."),
    series: list.filter((s) => on.has(s.id)).map((s, i0) => ({ label: bName(s), color: s.id === tx?.id ? "#d97706" : PALETTE[list.indexOf(s) % PALETTE.length], points: (s.obs || []).filter((o) => o[0] >= f0 && o[2] != null).map((o) => ({ x: o[0], y: o[2] })) })) }); };
  const list1 = [...(tx ? [tx] : []), ...gcc], list2 = [...(tx ? [tx] : []), ...world, ...(ppiS ? [ppiS] : [])];
  const draw = () => {
    $("#tb-c1").innerHTML = chipsOf(list1, teBenchUI.on1); $("#tb-ch1").innerHTML = chartOf(list1, teBenchUI.on1, L("TrendX vs GCC CPIs", "TrendX مقابل الخليج"));
    $("#tb-c2").innerHTML = chipsOf(list2, teBenchUI.on2); $("#tb-ch2").innerHTML = chartOf(list2, teBenchUI.on2, L("TrendX vs world indices", "TrendX مقابل المؤشرات العالمية"));
    const rows = [...S, ...(ppiS ? [ppiS] : [])].map((s) => { const ln = bLast(s, 1), l2 = bLast(s, 2), prev = ln ? bAt(s, ymAdd(ln[0], -1), 1) : null, ly = ln ? bAt(s, ymAdd(ln[0], -12), 1) : null, j24 = bAt(s, "2024-01", 2);
      return { s, ln, l2, mm: ln ? pct(ln[1], prev) : null, yy: ln ? pct(ln[1], ly) : null, since: l2 ? pct(l2[2], j24) : null }; });
    $("#tb-table").innerHTML = `<div class="tw tall"><table id="tb-cmp"><caption class="sr-only">${esc(L("Benchmark comparison", "مقارنة المعايير"))}</caption><thead><tr><th scope="col">${esc(L("Series", "السلسلة"))}</th><th scope="col">${esc(L("Group", "المجموعة"))}</th><th scope="col">${esc(L("Source", "المصدر"))}</th><th scope="col">${esc(L("Native base", "الأساس الأصلي"))}</th><th scope="col">${esc(L("Last period", "آخر فترة"))}</th><th scope="col" class="num">${esc(L("Last value (native)", "آخر قيمة (أصلية)"))}</th><th scope="col" class="num">2024 = 100</th><th scope="col" class="num">${esc(L("m/m %", "شهري %"))}</th><th scope="col" class="num">${esc(L("y/y %", "سنوي %"))}</th><th scope="col" class="num">${esc(L("Since Jan 2024 %", "منذ يناير 2024 %"))}</th><th scope="col">${esc(L("Lag note", "ملاحظة التأخر"))}</th></tr></thead><tbody>
      ${rows.map(({ s, ln, l2, mm, yy, since }) => `<tr${s.id === tx?.id ? ' class="agg"' : ""}><td><b>${esc(bName(s))}</b>${s.priv ? ` ${chip(L("private", "خاص"), "manual")}` : ""}<br><span class="muted">${esc(bKind(s.kind))} · <span class="ltr">${esc(s.country || "")}</span></span></td><td>${chip(bGroup(s.group), s.group === "ours" ? "blue" : s.group === "gcc" ? "ok" : "grey")}</td><td>${esc(s.source || "—")}</td><td><span class="ltr">${esc(s.native_base || "—")}</span></td><td>${ln ? esc(fmtYM(ln[0])) : "—"}</td><td class="num">${ln ? fmtN(ln[1], 2) : "—"}</td><td class="num">${l2 ? fmtN(l2[2], 1) : "—"}</td><td class="num">${pctCell(mm)}</td><td class="num">${pctCell(yy)}</td><td class="num">${pctCell(since)}</td><td class="note">${esc(s.lag_note || "")}</td></tr>`).join("")}</tbody></table></div>`;
    const sheet = () => ({ title: "TrendX benchmarks", subtitle: `built ${B.built} • ${B.base || "mean of 2024 = 100"} • native values and rebased levels`, headers: ["Series", "Group", "Country", "Kind", "Source", "Source series", "Native base", "Last period", "Last value (native)", "2024 = 100", "m/m %", "y/y %", "Since Jan 2024 %", "Lag note", "Licence"], widths: [30, 8, 8, 14, 22, 30, 18, 10, 14, 10, 8, 8, 12, 40, 24], priceCols: [],
      rows: rows.filter((x) => !x.s.priv).map(({ s, ln, l2, mm, yy, since }) => [s.name_en, s.group, s.country, s.kind, s.source, s.source_series, s.native_base, ln?.[0] ?? null, ln?.[1] ?? null, l2?.[2] ?? null, mm, yy, since, s.lag_note || "", s.licence || ""]) });
    $("#tb-xlsx").onclick = () => offerXlsx(`TrendX benchmarks ${B.built}.xlsx`, sheet());
    $("#tb-csv").onclick = () => { const sh = sheet(); offerFile(`trendx_benchmarks_${B.built}.csv`, toCsv(sh.rows.map((row) => Object.fromEntries(sh.headers.map((h, i) => [h, row[i]]))), sh.headers)); };
  };
  const tog = (set) => (e) => { const b = e.target.closest("[data-id]"); if (!b) return; if (set.has(b.dataset.id)) set.delete(b.dataset.id); else set.add(b.dataset.id); draw(); };
  $("#tb-c1").onclick = tog(teBenchUI.on1); $("#tb-c2").onclick = tog(teBenchUI.on2);
  bindSeg("tb-range", (v) => { teBenchUI.range = v; draw(); });
  draw();
}
