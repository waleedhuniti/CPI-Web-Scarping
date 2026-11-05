"use strict";
const APIFY = "Apfiy";
// ------------------------------------------------------------ language: English LTR by default, Arabic RTL on the toggle
let LANG = "en";
const L = (en, ar) => (LANG === "ar" ? ar : en);
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function toast(msg, bad = false) {
  const t = $("#toast"); t.textContent = msg; t.className = bad ? "bad" : ""; t.hidden = false;
  clearTimeout(toast.t); toast.t = setTimeout(() => (t.hidden = true), bad ? 8000 : 3000);
}

let db = null, mcp = null, downloads = null;
let projects = {};            // id -> project doc
let current = null;           // project id
let basket = [], basketDirty = false, basketLoaded = false;   // basketLoaded: the basket of `current` was read; Save stays blocked until then
let job = null;

// ------------------------------------------------------------ quantity, barcode
const UNITS = [
  [/^(kg|kgs|kilo|kilos|kilogram|kilograms|كغ|كجم|كيلو|كيلوغرام|كيلوجرام|كلغ)$/, "g", 1000],
  [/^(g|gm|gms|gr|grm|gram|grams|غ|غم|غرام|جم|جرام|ج)$/, "g", 1],
  [/^(l|lt|ltr|ltrs|litre|litres|liter|liters|لتر|ل|ليتر)$/, "ml", 1000],
  [/^(ml|mls|millilitre|milliliter|مل|ملل|مليلتر)$/, "ml", 1],
  [/^(pc|pcs|piece|pieces|pack|eggs?|حبة|حبه|حبات|بيضة|بيضه|قطعة)$/, "pc", 1],
];
const AR_DIGITS = { "٠": 0, "١": 1, "٢": 2, "٣": 3, "٤": 4, "٥": 5, "٦": 6, "٧": 7, "٨": 8, "٩": 9 };
function unitOf(u) { u = u.toLowerCase(); for (const [re, base, f] of UNITS) if (re.test(u)) return [base, f]; return null; }
function parseQty(text) {
  if (!text) return null;
  let s = String(text).replace(/[٠-٩]/g, (d) => AR_DIGITS[d]).replace(/٫/g, ".").replace(/,(?=\d{3}\b)/g, "").toLowerCase();
  const N = "(\\d+(?:\\.\\d+)?)", U = "([a-z\\u0600-\\u06ff]+)";
  let m = s.match(new RegExp(N + "\\s*[x×*]\\s*" + N + "\\s*" + U));       // 4 x 1 litre
  if (m && unitOf(m[3])) { const [b, f] = unitOf(m[3]); return { unit: b, total: +m[1] * +m[2] * f }; }
  m = s.match(new RegExp(N + "\\s*" + U + "\\s*[x×*]\\s*" + N));           // 30g x 18
  if (m && unitOf(m[2])) { const [b, f] = unitOf(m[2]); return { unit: b, total: +m[1] * +m[3] * f }; }
  for (const mm of s.matchAll(new RegExp(N + "\\s*" + U, "g"))) {
    const u = unitOf(mm[2]); if (u) return { unit: u[0], total: +mm[1] * u[1] };
  }
  return null;
}
function digits(x) { return String(x ?? "").replace(/\D/g, ""); }
function searchForm(raw) { const d = digits(raw); return d.length === 11 ? "0" + d : d; }
function gtinValid(raw) {
  let d = digits(raw); if (d.length === 11) d = "0" + d;
  if (![8, 12, 13, 14].includes(d.length)) return false;
  const p = d.padStart(14, "0"); let sum = 0;
  for (let i = 0; i < 13; i++) sum += +p[i] * (i % 2 === 0 ? 3 : 1);
  return (10 - (sum % 10)) % 10 === +p[13];
}
function itemQty(it) { return it.qty_total && it.qty_unit ? { unit: it.qty_unit, total: +it.qty_total } : parseQty(it.qty_raw); }

// ------------------------------------------------------------ parsers: dataset items -> rows
function num(v) { if (v === null || v === undefined || v === "") return null; const n = parseFloat(String(v).replace(/[,%\s]/g, "")); return isNaN(n) ? null : n; }
const PARSERS = {
  carrefour_actor(items, batch) {
    const rows = items.filter((it) => digits(it.searchQuery).length >= 8).map((it) => ({
      code: digits(it.searchQuery), title: it.title || "", price: num(it.price), regular_price: num(it.regularPrice) ?? num(it.price),
      in_stock: it.in_stock ?? null, url: it.url || "" }));
    return { rows, searched: new Set(batch) };
  },
  lulu_search_markdown(items) {
    const card = /\[([^\]\n]+)\]\((https:\/\/gcc\.luluhypermarket\.com\/en-ae\/(?:[^)\s]*?\/)?p\/[^)\s]*?)\)\s*\n\s*\n([\d,]+(?:\.\d+)?)(?:\s*\n\s*\n([\d,]+(?:\.\d+)?))?(?:\s*\n\s*\n(\d+)% OFF)?/g;
    const rows = [], searched = new Set();
    for (const it of items) {
      let q = ""; try { q = new URL(it.url).searchParams.get("search_text") || ""; } catch (e) {}
      const md = it.markdown || it.text || "";
      if (!q || (!md.includes("All Products") && !md.includes("No results found"))) continue;
      searched.add(q);
      if (md.includes("No results found")) continue;
      for (const c of md.matchAll(card)) {
        const price = num(c[3]), other = num(c[4]);
        rows.push({ code: q, title: c[1].trim(), price, regular_price: other && other > price ? other : price, in_stock: null, url: c[2].split("?")[0] });
      }
    }
    return { rows, searched };
  },
  te_commodities(items) {
    const html = items[0] && (items[0].html || items[0].body);
    if (!html) throw new Error("the actor returned no html");
    const doc = new DOMParser().parseFromString(html, "text/html");
    const KEYS = { price: "price", chg: "change", "%chg": "pct", weekly: "weekly", monthly: "monthly", ytd: "ytd", yoy: "yoy", date: "price_date" };
    const rows = [];
    for (const t of doc.querySelectorAll("table")) {
      const h = [...t.querySelectorAll("thead th")].map((x) => x.textContent.trim());
      if (h.length < 2 || h[1] !== "Price") continue;
      for (const tr of t.querySelectorAll("tbody tr")) {
        const tds = tr.querySelectorAll("td"); const b = tds[0] && tds[0].querySelector("b");
        if (!b) continue;
        const r = { category: h[0], commodity: b.textContent.trim(), unit: tds[0].querySelector("div")?.textContent.trim() || "" };
        h.slice(1).forEach((x, i) => {
          const k = KEYS[x.toLowerCase()], td = tds[i + 1]; if (!k || !td) return;
          const txt = td.textContent.replace(/\s+/g, " ").trim();
          r[k] = k === "price_date" ? txt : num(td.getAttribute("data-value") ?? txt);
        });
        rows.push(r);
      }
    }
    if (rows.length < 20) throw new Error(`only ${rows.length} commodity rows found on the page`);
    return { rows, searched: null };
  },
  generic(items, batch, cfg) {
    const f = cfg.fields || {};
    const get = (o, p) => String(p || "").split(".").reduce((a, k) => (a && typeof a === "object" ? a[k] : undefined), o) ?? o[p];
    const rows = items.map((it) => {
      const r = {}; for (const [k, p] of Object.entries(f)) r[k] = get(it, p);
      if (r.code !== undefined) r.code = searchForm(r.code);
      if (r.price !== undefined) r.price = num(r.price);
      if (r.regular_price !== undefined) r.regular_price = num(r.regular_price);
      return Object.keys(f).length ? r : it;
    });
    return { rows, searched: batch ? new Set(batch) : null };
  },
};

// ------------------------------------------------------------ matchers: rows -> results
const STATUS = {
  barcode_match: ["Matched", "مطابق", "ok"], unit_label: ["Matched (unit written differently)", "مطابق (وحدة مكتوبة مختلفة)", "ok"], multiple_results: ["Several products", "أكثر من منتج", "warn"],
  size_unverified: ["Size not confirmed", "الحجم غير مؤكد", "warn"], qty_mismatch: ["Size differs", "الحجم مختلف", "bad"], not_found: ["Not found", "غير موجود", ""],
  not_searched: ["Not searched", "لم يُبحث", "warn"], service: ["Service (no online price)", "خدمة (لا سعر على الإنترنت)", ""], pending: ["Not priced yet", "لم يُسعَّر بعد", ""], error: ["Run error", "خطأ في التشغيل", "bad"], ok: ["Found", "موجود", "ok"], missing: ["Missing from the page", "غير موجود في الصفحة", "bad"], row: ["Row", "صف", ""],
  found: ["Found", "موجود", "ok"], match: ["Matched", "مطابق", "ok"], review_multiple: ["Several offers, different prices", "عدة عروض بأسعار مختلفة", "warn"], review_origin: ["Origin not stated", "المنشأ غير مذكور", "warn"],
  substitute_origin: ["Substitute origin", "منشأ بديل", "warn"], no_match: ["No match", "غير مطابق", ""], barcode_search_match: ["Matched", "مطابق", "ok"], barcode_match_unit_label: ["Matched (other unit)", "مطابق (وحدة مختلفة)", "ok"],
  qty_unit_differs: ["Quantity unit differs", "وحدة الكمية مختلفة", "warn"], qty_title_url_conflict: ["Size conflict", "تعارض الحجم", "warn"], barcode_match_qty_unverified: ["Size not confirmed", "الحجم غير مؤكد", "warn"],
};
const statusLabel = (s) => (STATUS[s] ? L(STATUS[s][0], STATUS[s][1]) : s);
function matchBarcode(actorKey, label, items, rows, searched, failed) {
  const byCode = new Map();
  for (const r of rows) { if (!byCode.has(r.code)) byCode.set(r.code, new Map()); byCode.get(r.code).set(r.url || r.title, r); }
  const out = [];
  for (const it of items) {
    if (!gtinValid(it.barcode_raw)) continue;
    const code = searchForm(it.barcode_raw);
    const base = { actor: label, item_code: it.item_code || "", name: it.name_ar || it.name || "", brand: it.brand_ar || "", basket_qty: it.qty_raw || "", barcode: code, title: "", price: "", regular_price: "", url: "", accepted: "no" };
    const hits = [...(byCode.get(code)?.values() || [])];
    if (!hits.length) { out.push({ ...base, status: failed.has(code) ? "error" : searched.has(code) ? "not_found" : "not_searched" }); continue; }
    const want = itemQty(it); let best = null;
    for (const h of hits) {
      const got = parseQty(h.title) || parseQty(decodeURIComponent(h.url || "").replace(/[-_/]/g, " "));
      let status;
      if (!want || !got) status = "size_unverified";
      else if (Math.abs(want.total - got.total) <= want.total * 0.005) status = want.unit === got.unit ? (hits.length === 1 ? "barcode_match" : "multiple_results") : (want.unit !== "pc" && got.unit !== "pc" && hits.length === 1 ? "unit_label" : "size_unverified");
      else status = "qty_mismatch";
      const rank = { barcode_match: 5, unit_label: 4, multiple_results: 3, size_unverified: 2, qty_mismatch: 1 }[status];
      if (!best || rank > best.rank) best = { h, status, rank };
    }
    out.push({ ...base, status: best.status, accepted: ["barcode_match", "unit_label"].includes(best.status) ? "yes" : "no",
      title: best.h.title, price: best.h.price ?? "", regular_price: best.h.regular_price ?? "", url: best.h.url });
  }
  return out;
}
function matchList(label, items, rows, key) {
  const want = items.filter((i) => i.enabled !== false && i.enabled !== "no");
  const norm = (s) => String(s ?? "").trim().toLowerCase();
  const byKey = new Map(rows.map((r) => [norm(r[key]), r]));
  const out = want.map((i) => { const r = byKey.get(norm(i[key])); return r ? { actor: label, ...r, status: "ok", accepted: "yes" } : { actor: label, [key]: i[key], category: i.category || "", status: "missing", accepted: "no" }; });
  return want.length ? out : rows.map((r) => ({ actor: label, ...r, status: "ok", accepted: "yes" }));
}

// ------------------------------------------------------------ Apify through the connector
function mcpErr(e) {
  const fix = { needs_reauth: L("Reconnect Apify in claude.ai Settings > Connectors", "أعد ربط Apify من إعدادات claude.ai ← Connectors"), server_not_connected: L("Add the Apify connector in claude.ai Settings > Connectors", "أضف موصل Apify من إعدادات claude.ai ← Connectors"),
    selection_required: L("Choose the Apify connector when claude.ai asks", "اختر موصل Apify الذي تريده عندما يطلب claude.ai ذلك"), not_in_manifest: L("This page may not use Apify; reopen it and allow the connector", "لم يُسمح لهذه الصفحة باستخدام Apify؛ أعد فتحها واسمح بالموصل"),
    blocked_by_policy: L("Your organization's policy blocks this tool", "سياسة المؤسسة تمنع هذه الأداة"), approval_required: L("The tool needs approval for each call", "الأداة تحتاج موافقة لكل استدعاء"), server_unavailable: L("Apify is not answering now; try again shortly", "Apify لا يستجيب الآن؛ حاول بعد قليل") }[e?.code];
  return fix ? `${fix} (${e.code})` : (e?.message || String(e));
}
async function apify(tool, input, read = false) {
  try { return (await mcp.callTool(APIFY, tool, input, { cache: false })).payload; }
  catch (e) {
    if (read && e?.retryable) { await sleep((e.retryAfterMs || 1500) + Math.random() * 1000); return (await mcp.callTool(APIFY, tool, input, { cache: false })).payload; }
    throw e;
  }
}
async function runActor(cfg, input, stopped, onStep = () => {}) {
  const args = { actor: cfg.actor, input, waitSecs: 0 };
  if (cfg.call_options && Object.keys(cfg.call_options).length) args.callOptions = cfg.call_options;
  const start = await apify("call-actor", args);
  const runId = start.runId; let status = start.status; let dsId = start.storages?.datasets?.default?.id;
  if (!runId) throw new Error("Apify did not return a run id");
  onStep("started", runId, status);
  while (!["SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"].includes(status)) {
    if (stopped()) throw new Error("stopped");
    const r = await apify("get-actor-run", { runId, waitSecs: 30 }, true);
    status = r.status; dsId = r.storages?.datasets?.default?.id || dsId;
    onStep("status", runId, status);
  }
  if (status !== "SUCCEEDED") throw new Error(`run ${runId} ended ${status}`);
  const items = []; const limit = 500;
  for (let offset = 0; ; offset += limit) {
    const q = { datasetId: dsId, clean: true, limit, offset }; if (cfg.dataset_fields) q.fields = cfg.dataset_fields;
    const p = await apify("get-dataset-items", q, true);
    const page = p.items || []; items.push(...page); onStep("items", runId, items.length);
    if (page.length < limit || (p.totalItemCount && items.length >= p.totalItemCount)) break;
  }
  return { runId, items };
}
function fill(v, subs) {
  if (Array.isArray(v)) return v.map((x) => fill(x, subs));
  if (v && typeof v === "object") return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, fill(x, subs)]));
  if (typeof v === "string") { const m = v.match(/^\{(\w+)\}$/); if (m && m[1] in subs) return subs[m[1]]; }
  return v;
}
function buildRuns(cfg, items) {
  if (cfg.mode === "single") return [{ batch: null, input: cfg.input }];
  const codes = [...new Set(items.filter((i) => gtinValid(i.barcode_raw)).map((i) => searchForm(i.barcode_raw)))];
  const size = Math.max(1, +cfg.batch_size || 10), runs = [];
  for (let k = 0; k < codes.length; k += size) {
    const batch = codes.slice(k, k + size);
    const urls = batch.map((c) => String(cfg.url_template || "").replace("{barcode}", c));
    runs.push({ batch, input: fill(JSON.parse(JSON.stringify(cfg.input)), {
      barcodes: batch, barcodes_json: JSON.stringify(batch), barcodes_text: batch.join("\n"),
      start_urls: batch.map((c, i) => ({ url: urls[i], userData: { ean: c } })), urls }) });
  }
  return runs;
}

// ------------------------------------------------------------ db helpers
const P = () => projects[current];
async function loadProjects() {
  const snap = await db.collection("projects").get();
  projects = {}; snap.docs.forEach((d) => (projects[d.id] = { ...plain(d) }));
}
async function loadBasket(pid) {
  const snap = await db.collection(`projects/${pid}/basket`).get();
  return [...snap.docs].sort((a, b) => a.id.localeCompare(b.id)).flatMap((d) => plain(d).items || []);
}
async function saveChunks(coll, key, list, old) {
  const chunks = []; let cur = [], size = 0;
  for (const x of list) { const s = JSON.stringify(x).length; if (size + s > 40000 && cur.length) { chunks.push(cur); cur = []; size = 0; } cur.push(x); size += s; }
  if (cur.length || !chunks.length) chunks.push(cur);
  for (let i = 0; i < chunks.length; i++) await db.doc(`${coll}/c${String(i).padStart(3, "0")}`).set({ [key]: chunks[i], i });
  const prev = old ?? (await db.collection(coll).get()).docs.map((d) => d.id);
  for (const id of prev) if (+id.slice(1) >= chunks.length) await db.doc(`${coll}/${id}`).delete();
  return chunks.length;
}
async function saveProject(patch) {
  const p = { ...P(), ...patch, updatedAt: new Date().toISOString() };
  await db.doc(`projects/${current}`).set(p); projects[current] = p;
}
// the store hands back frozen data; work on a plain copy
const plain = (snap) => JSON.parse(JSON.stringify(snap.data() ?? {}));
// rows of a run: one document at a time (a whole-collection read of large chunks can fail), in chunk order
async function rowDocs(pid, run) {
  const base = `projects/${pid}/runs/${run.id}/rows`;
  if (Number.isInteger(run.chunks) && run.chunks > 0) {
    const out = [];
    for (let i = 0; i < run.chunks; i++) {
      const snap = await db.doc(`${base}/c${String(i).padStart(3, "0")}`).get();
      if (snap.exists) out.push(snap);
    }
    if (out.length) return out;
  }
  return [...(await db.collection(base).limit(200).get()).docs].sort((a, b) => a.id.localeCompare(b.id));
}
// product thumbnails saved with each run (projects/<p>/runs/<id>/thumbs/tNNN: {pairs: [[photo url, base64 jpeg]]})
const thumbs = new Map(); const thumbRuns = new Set();
async function loadThumbs(pid, run) {
  if (!run || thumbRuns.has(pid + "/" + run.id)) return;
  if (run.thumbs_asset) {          // the run's pictures as one uploaded file
    thumbRuns.add(pid + "/" + run.id);
    try { for (const [u, b] of (await (await fetch("/_blob/" + run.thumbs_asset)).json()).pairs || []) thumbs.set(u, b); } catch (e) {}
    return;
  }
  if (!run.thumbs) return;
  thumbRuns.add(pid + "/" + run.id);
  for (let i = 0; i < run.thumbs; i++) {
    try {
      const snap = await db.doc(`projects/${pid}/runs/${run.id}/thumbs/t${String(i).padStart(3, "0")}`).get();
      if (snap.exists) for (const [u, b] of plain(snap).pairs || []) thumbs.set(u, b);
    } catch (e) { /* a missing thumbnail only leaves the photo cell empty */ }
  }
}
const photoSrc = (u) => (thumbs.has(u) ? "data:image/jpeg;base64," + thumbs.get(u) : u);
function dbErr(e) { return e?.code === "quota_exceeded" ? L("The database is full (quota_exceeded): delete old runs, then try again", "امتلأت قاعدة البيانات (quota_exceeded)؛ احذف تشغيلات قديمة ثم حاول") : e?.code === "revoked" ? L("You no longer have access to this page", "لم تعد لديك صلاحية على هذه الصفحة") : (e?.message || String(e)); }
