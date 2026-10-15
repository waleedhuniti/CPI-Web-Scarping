// CPI portal front end: tabs for scrape, basket, actors, settings.
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function api(path, opts = {}) {
  const init = { ...opts };
  if (opts.json !== undefined) {
    init.body = JSON.stringify(opts.json);
    init.headers = { "Content-Type": "application/json" };
  }
  const r = await fetch(path, init);
  const data = await r.json().catch(() => ({}));
  if (!r.ok || data.ok === false) throw new Error(data.error || `HTTP ${r.status}`);
  return data;
}

function toast(msg, bad = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = bad ? "bad" : "";
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (t.hidden = true), bad ? 7000 : 3000);
}

// ---------------------------------------------------------------- tabs
$$("nav button").forEach((b) =>
  b.addEventListener("click", () => {
    $$("nav button").forEach((x) => x.classList.toggle("on", x === b));
    $$(".tab").forEach((t) => t.classList.toggle("on", t.id === "tab-" + b.dataset.tab));
  })
);

// ---------------------------------------------------------------- state
let basket = [];
let basketDirty = false;
let actors = {};
let parsers = [];
let modes = [];

const STATUS_AR = {
  barcode_match: "مطابق بالباركود", barcode_search_match: "مطابق (بحث الباركود)", barcode_match_name_changed: "مطابق (الاسم تغيّر)",
  barcode_match_unit_label: "مطابق (وحدة مختلفة)", fuzzy_match: "مطابق بالاسم", qty_mismatch: "الكمية مختلفة",
  qty_unit_differs: "وحدة الكمية مختلفة", qty_title_url_conflict: "تعارض الحجم", barcode_match_qty_unverified: "الحجم غير مؤكد",
  review: "للمراجعة", no_match: "غير مطابق", not_found: "غير موجود", not_searched: "لم يُبحث", error: "خطأ",
};

// ---------------------------------------------------------------- scrape tab
function groupsOf(items) {
  const g = new Map();
  items.forEach((i) => g.set(i.group_code, i.group_name || i.group_code));
  return [...g].sort();
}

function renderScrapePicks() {
  $("#retailer-picks").innerHTML = Object.entries(actors)
    .map(([k, a]) => `<label><input type="checkbox" value="${esc(k)}" ${a.enabled ? "checked" : ""}>${esc(a.label || k)}</label>`)
    .join("");
  $("#group-picks").innerHTML = groupsOf(basket)
    .map(([c, n]) => `<label><input type="checkbox" value="${esc(c)}">${esc(n)}</label>`)
    .join("");
  $$("#retailer-picks input, #group-picks input").forEach((i) => i.addEventListener("change", updateCount));
  updateCount();
}

function selection() {
  const groups = $$("#group-picks input:checked").map((i) => i.value);
  const codes = $("#item-codes").value.split(/[\s,،]+/).filter(Boolean);
  const retailers = $$("#retailer-picks input:checked").map((i) => i.value);
  return { groups, item_codes: codes, retailers };
}

function updateCount() {
  const s = selection();
  let items = basket.filter((i) => i.barcode_kind === "gtin");
  if (s.groups.length) items = items.filter((i) => s.groups.includes(i.group_code));
  if (s.item_codes.length) items = items.filter((i) => s.item_codes.includes(i.item_code));
  $("#scrape-count").textContent = `${items.length} صنف بباركود سيتم البحث عنه في ${s.retailers.length} متجر. (الأصناف بدون باركود، مثل الطازج، لا يشملها هذا التشغيل.)`;
}
$("#item-codes").addEventListener("input", updateCount);

$("#btn-scrape").addEventListener("click", async () => {
  if (basketDirty && !confirm("في تعديلات على السلة لم تُحفظ. التشغيل سيستخدم السلة المحفوظة. متابعة؟")) return;
  try {
    await api("/api/scrape", { method: "POST", json: selection() });
    toast("بدأ السكراب");
    pollJob();
  } catch (e) {
    toast(e.message, true);
  }
});
$("#btn-stop").addEventListener("click", () => api("/api/scrape/stop", { method: "POST" }).then(() => toast("تم طلب الإيقاف")));

let pollTimer;
async function pollJob() {
  clearTimeout(pollTimer);
  const s = await api("/api/scrape/status");
  if (s.status === "idle") return;
  $("#job-card").hidden = false;
  const label = { running: ["يعمل", "warn"], done: ["انتهى", "ok"], error: ["خطأ", "bad"], stopped: ["أُوقف", "bad"] }[s.status] || [s.status, ""];
  $("#job-status").textContent = label[0];
  $("#job-status").className = "pill " + label[1];
  $("#job-progress").innerHTML = Object.entries(s.progress)
    .map(([k, p]) => `<div>${esc(actors[k]?.label || k)}: ${p.done} / ${p.total} تشغيل${p.failed ? ` (${p.failed} فشل)` : ""}</div>
      <div class="bar"><div style="width:${p.total ? (100 * p.done) / p.total : 0}%"></div></div>`)
    .join("");
  const log = $("#job-log");
  log.textContent = s.log.join("\n");
  log.scrollTop = log.scrollHeight;
  $("#btn-scrape").disabled = s.status === "running";
  $("#btn-stop").disabled = s.status !== "running";
  if (s.summary) $("#job-summary").innerHTML = summaryHtml(s.summary);
  if (s.status === "running") pollTimer = setTimeout(pollJob, 2000);
  else loadRuns();
}

function summaryHtml(sum) {
  return `<table><tr><th>المتجر</th><th>أصناف</th><th>مقبول</th><th>التفاصيل</th></tr>${Object.entries(sum)
    .map(([k, v]) => `<tr><td>${esc(actors[k]?.label || k)}</td><td>${v.lines}</td><td><b>${v.accepted}</b></td>
      <td>${Object.entries(v.statuses).map(([s, n]) => `${esc(STATUS_AR[s] || s)}: ${n}`).join(" · ")}</td></tr>`)
    .join("")}</table>`;
}

async function loadRuns() {
  const runs = await api("/api/runs");
  $("#runs").innerHTML = runs.length
    ? `<div class="runs-list">${runs.map((r) => `<button data-run="${esc(r.name)}" ${r.has_results ? "" : "disabled"}>${esc(r.name.replace("_portal", ""))}</button>`).join("")}</div>`
    : `<p class="muted">لا توجد تشغيلات بعد.</p>`;
  $$("#runs button[data-run]").forEach((b) => b.addEventListener("click", () => showRun(b.dataset.run)));
}

async function showRun(name) {
  const rows = await api(`/api/runs/${encodeURIComponent(name)}/results`);
  const filter = `<div class="toolbar"><input id="res-filter" placeholder="فلترة النتائج"><select id="res-status"><option value="">كل الحالات</option><option value="yes">المقبول فقط</option><option value="no">غير المقبول</option></select>
    <a class="btn" href="/api/runs/${encodeURIComponent(name)}/results?download=1">تنزيل CSV</a></div>`;
  $("#run-results").innerHTML = `<h3>${esc(name)}</h3>${filter}<div class="table-wrap"><table><thead><tr><th>المتجر</th><th>الكود</th><th>الصنف</th><th>الكمية</th><th>الحالة</th><th>السعر</th><th>قبل الخصم</th><th>عنوان المنتج</th></tr></thead><tbody></tbody></table></div>`;
  const draw = () => {
    const q = $("#res-filter").value.trim().toLowerCase();
    const st = $("#res-status").value;
    const shown = rows.filter((r) => (!st || r.accepted === st) && (!q || Object.values(r).join(" ").toLowerCase().includes(q)));
    $("#run-results tbody").innerHTML = shown
      .slice(0, 500)
      .map((r) => `<tr><td>${esc(r.retailer)}</td><td class="ltr">${esc(r.item_code)}</td><td>${esc(r.name_ar)} <span class="muted">${esc(r.brand_ar)}</span></td>
        <td>${esc(r.basket_qty)}</td><td><span class="pill ${r.accepted === "yes" ? "ok" : r.status === "not_found" ? "" : "warn"}">${esc(STATUS_AR[r.status] || r.status)}</span></td>
        <td class="ltr">${esc(r.price)}</td><td class="ltr">${esc(r.regular_price)}</td>
        <td>${r.url ? `<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a>` : ""}</td></tr>`)
      .join("");
  };
  $("#res-filter").addEventListener("input", draw);
  $("#res-status").addEventListener("change", draw);
  draw();
}

// ---------------------------------------------------------------- basket tab
let page = 0;
const PER = 50;

function filteredBasket() {
  const q = $("#basket-search").value.trim().toLowerCase();
  const g = $("#basket-group").value;
  return basket
    .map((it, idx) => ({ it, idx }))
    .filter(({ it }) => (!g || it.group_code === g) && (!q || [it.item_code, it.name_ar, it.brand_ar, it.barcode_raw].join(" ").toLowerCase().includes(q)));
}

function renderBasket() {
  const rows = filteredBasket();
  const pages = Math.max(1, Math.ceil(rows.length / PER));
  page = Math.min(page, pages - 1);
  $("#basket-table tbody").innerHTML = rows
    .slice(page * PER, (page + 1) * PER)
    .map(({ it, idx }) => `<tr><td class="ltr">${esc(it.item_code)}</td><td>${esc(it.name_ar)}</td><td>${esc(it.brand_ar)}</td>
      <td class="ltr">${esc(it.barcode_raw)}</td><td>${esc(it.qty_raw)}${it.qty_flag ? ` <span class="pill warn">${esc(it.qty_flag)}</span>` : ""}</td>
      <td>${esc(it.origin_raw)}</td><td>${it.match_mode === "barcode" ? "باركود" : "مواصفات"}</td>
      <td><button data-edit="${idx}">تعديل</button> <button data-del="${idx}" class="danger">حذف</button></td></tr>`)
    .join("");
  $("#pg-info").textContent = `${page + 1} / ${pages}`;
  const nb = basket.filter((i) => i.barcode_kind === "gtin").length;
  $("#basket-info").textContent = `${basket.length} صنف في السلة (${nb} بباركود) · المعروض ${rows.length}` + (basketDirty ? " · ⚠ تعديلات غير محفوظة" : "");
  $$("[data-edit]").forEach((b) => b.addEventListener("click", () => editItem(+b.dataset.edit)));
  $$("[data-del]").forEach((b) =>
    b.addEventListener("click", () => {
      const it = basket[+b.dataset.del];
      if (!confirm(`حذف ${it.item_code} ${it.name_ar}؟`)) return;
      basket.splice(+b.dataset.del, 1);
      basketDirty = true;
      renderBasket();
    })
  );
}

function fillGroupSelect() {
  const cur = $("#basket-group").value;
  $("#basket-group").innerHTML = `<option value="">كل المجموعات</option>` + groupsOf(basket).map(([c, n]) => `<option value="${esc(c)}">${esc(n)}</option>`).join("");
  $("#basket-group").value = cur;
}

$("#basket-search").addEventListener("input", () => { page = 0; renderBasket(); });
$("#basket-group").addEventListener("change", () => { page = 0; renderBasket(); });
$("#pg-prev").addEventListener("click", () => { page = Math.max(0, page - 1); renderBasket(); });
$("#pg-next").addEventListener("click", () => { page++; renderBasket(); });

const dlg = $("#item-dialog");
const form = $("#item-form");
let editing = null;

function editItem(idx) {
  editing = idx;
  const it = idx === null ? {} : basket[idx];
  $("#item-dialog-title").textContent = idx === null ? "صنف جديد" : `تعديل ${it.item_code}`;
  for (const el of form.elements) if (el.name) el.value = it[el.name] ?? "";
  $("#item-preview").textContent = "";
  dlg.showModal();
}
$("#btn-add-item").addEventListener("click", () => editItem(null));

let previewTimer;
form.addEventListener("input", () => {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(async () => {
    try {
      const { item } = await api("/api/basket/preview", { method: "POST", json: formData() });
      $("#item-preview").textContent = `GTIN: ${item.gtin || "—"} (${item.barcode_kind}) · الكمية: ${item.qty_total || "?"} ${item.qty_unit || ""}${item.qty_flag ? " ⚠ " + item.qty_flag : ""} · المنشأ: ${item.origin_iso || "—"} · المطابقة: ${item.match_mode}`;
    } catch (e) {
      $("#item-preview").textContent = "⚠ " + e.message;
    }
  }, 300);
});

function formData() {
  const d = {};
  for (const el of form.elements) if (el.name) d[el.name] = el.value.trim();
  return d;
}

dlg.addEventListener("close", async () => {
  if (dlg.returnValue !== "ok") return;
  try {
    const { item } = await api("/api/basket/preview", { method: "POST", json: formData() });
    const clash = basket.findIndex((x, i) => x.item_code === item.item_code && i !== editing);
    if (clash >= 0) return toast(`الكود ${item.item_code} موجود مسبقاً`, true);
    if (editing === null) basket.push(item);
    else basket[editing] = item;
    basketDirty = true;
    fillGroupSelect();
    renderBasket();
  } catch (e) {
    toast(e.message, true);
  }
});

$("#btn-save-basket").addEventListener("click", async () => {
  try {
    const r = await api("/api/basket", { method: "PUT", json: basket });
    basket = r.items;
    basketDirty = false;
    renderBasket();
    renderScrapePicks();
    toast(`حُفظت السلة (${basket.length} صنف)`);
  } catch (e) {
    toast(e.message, true);
  }
});

$("#basket-file").addEventListener("change", async (ev) => {
  const f = ev.target.files[0];
  if (!f || !confirm(`استبدال السلة كاملة بمحتوى ${f.name}؟`)) return;
  const fd = new FormData();
  fd.append("file", f);
  try {
    const r = await api("/api/basket/upload", { method: "POST", body: fd });
    basket = r.items;
    basketDirty = false;
    fillGroupSelect();
    renderBasket();
    renderScrapePicks();
    toast(`تم تحميل ${basket.length} صنف`);
  } catch (e) {
    toast(e.message, true);
  }
  ev.target.value = "";
});

// ---------------------------------------------------------------- actors tab
function renderActors() {
  $("#actor-list").innerHTML = Object.entries(actors)
    .map(([k, a]) => `<div class="actor" data-key="${esc(k)}">
      <div class="actor-head"><h3>${esc(a.label || k)}</h3><label><input type="checkbox" data-f="enabled" ${a.enabled ? "checked" : ""} style="width:auto"> مفعّل</label>
        <span class="muted" dir="ltr">${esc(k)}</span><button class="danger" data-remove>حذف</button></div>
      <div class="grid4">
        <label>الاسم<input data-f="label" value="${esc(a.label || "")}"></label>
        <label>Actor (username/name)<input data-f="actor" dir="ltr" value="${esc(a.actor)}"></label>
        <label>النمط<select data-f="mode">${modes.map((m) => `<option ${m === a.mode ? "selected" : ""}>${m}</option>`).join("")}</select></label>
        <label>المحلل (parser)<select data-f="parser">${parsers.map((p) => `<option ${p === a.parser ? "selected" : ""}>${p}</option>`).join("")}</select></label>
        <label>باركود لكل تشغيل<input data-f="batch_size" type="number" min="1" value="${a.batch_size}"></label>
        <label>تشغيلات متوازية<input data-f="parallel_runs" type="number" min="1" value="${a.parallel_runs}"></label>
      </div>
      <label>رابط البحث (للنمط search_urls، يحتوي {barcode})<input data-f="url_template" dir="ltr" value="${esc(a.url_template || "")}"></label>
      <label>الإدخال (input JSON)<textarea data-f="input" class="code" rows="9" spellcheck="false">${esc(JSON.stringify(a.input, null, 2))}</textarea></label>
      ${a.parser === "generic" || a.fields ? `<label>أسماء الحقول للمحلل generic (JSON)<textarea data-f="fields" class="code" rows="5" spellcheck="false">${esc(JSON.stringify(a.fields || { searched_barcode: "searchQuery", title: "title", price: "price", regular_price: "regularPrice", in_stock: "inStock", url: "url" }, null, 2))}</textarea></label>` : ""}
      <label>ملاحظات<input data-f="notes" value="${esc(a.notes || "")}"></label>
    </div>`)
    .join("");
  $$("#actor-list [data-remove]").forEach((b) =>
    b.addEventListener("click", () => {
      const k = b.closest(".actor").dataset.key;
      if (!confirm(`حذف ${k}؟ (يُطبّق عند الحفظ)`)) return;
      collectActors();
      delete actors[k];
      renderActors();
    })
  );
  $$('#actor-list [data-f="parser"]').forEach((s) => s.addEventListener("change", () => { collectActors(); renderActors(); }));
}

function collectActors() {
  const out = {};
  for (const box of $$("#actor-list .actor")) {
    const a = { ...actors[box.dataset.key] };
    for (const el of $$("[data-f]", box)) {
      const f = el.dataset.f;
      if (f === "enabled") a.enabled = el.checked;
      else if (f === "input" || f === "fields") {
        try { a[f] = JSON.parse(el.value); } catch (e) { throw new Error(`${box.dataset.key}: ${f} ليس JSON صحيحاً (${e.message})`); }
      } else if (f === "batch_size" || f === "parallel_runs") a[f] = +el.value;
      else a[f] = el.value.trim();
    }
    if (a.parser !== "generic" && !box.querySelector('[data-f="fields"]')) delete a.fields;
    out[box.dataset.key] = a;
  }
  actors = out;
  return out;
}

$("#btn-add-actor").addEventListener("click", () => {
  const k = (prompt("مفتاح المتجر بالإنجليزية (مثل spinneys):") || "").trim().toLowerCase();
  if (!k) return;
  if (!/^[a-z0-9_]{1,40}$/.test(k) || actors[k]) return toast("مفتاح غير صالح أو موجود", true);
  try { collectActors(); } catch (e) { return toast(e.message, true); }
  actors[k] = { label: k, enabled: false, actor: "username/actor-name", mode: "barcodes", batch_size: 10, parallel_runs: 2, input: { query: "{barcodes_json}" }, parser: "generic", fields: { searched_barcode: "searchQuery", title: "title", price: "price", regular_price: "regularPrice", in_stock: "inStock", url: "url" }, notes: "" };
  renderActors();
});

$("#btn-save-actors").addEventListener("click", async () => {
  try {
    const r = await api("/api/actors", { method: "PUT", json: { actors: collectActors(), page_function: $("#page-function").value } });
    actors = r.actors;
    renderActors();
    renderScrapePicks();
    toast("حُفظت إعدادات الـ Actors");
  } catch (e) {
    toast(e.message, true);
  }
});

// ---------------------------------------------------------------- settings tab
async function loadSettings() {
  const s = await api("/api/settings");
  $("#token-state").textContent = s.token_set ? `المفتاح محفوظ (${s.token_hint})` : "لا يوجد مفتاح بعد.";
}
$("#btn-token").addEventListener("click", async () => {
  try {
    await api("/api/settings", { method: "PUT", json: { token: $("#token").value } });
    $("#token").value = "";
    loadSettings();
    toast("حُفظ المفتاح");
  } catch (e) {
    toast(e.message, true);
  }
});
$("#btn-push").addEventListener("click", async () => {
  const out = $("#push-out");
  out.hidden = false;
  out.textContent = "جارٍ الرفع…";
  try {
    const r = await api("/api/git/push", { method: "POST", json: { message: $("#commit-msg").value } });
    out.textContent = `تم الرفع إلى ${r.branch}\n${r.output}`;
  } catch (e) {
    out.textContent = "فشل: " + e.message;
  }
});

window.addEventListener("beforeunload", (e) => { if (basketDirty) e.preventDefault(); });

// ---------------------------------------------------------------- boot
(async function boot() {
  try {
    const [b, a] = await Promise.all([api("/api/basket"), api("/api/actors")]);
    basket = b;
    ({ actors, parsers, modes } = a);
    $("#page-function").value = a.page_function;
    fillGroupSelect();
    renderBasket();
    renderActors();
    renderScrapePicks();
    loadRuns();
    loadSettings();
    pollJob();
  } catch (e) {
    toast("تعذّر تحميل البيانات: " + e.message, true);
  }
})();
