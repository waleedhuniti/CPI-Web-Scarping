// daily price of every scraped product (catalogue history change log -> one row per product per day listed), with its COICOP 2018 codes
const fs = require("fs");
const { coicopOf, CNODE } = require("./coicop_tree.js");
const [hp, out] = process.argv.slice(2);
const h = JSON.parse(fs.readFileSync(hp, "utf8"));
const q = (v) => { const s = v == null ? "" : String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
const cols = ["date", "outlet", "product_id", "title", "price", "regular_price", "catalogue_section", "shop_category", "coicop_item_type", "item_type_ar", "item_type_en", "coicop_subclass", "coicop_class", "class_ar", "coicop_division", "division_ar", "url"];
const lines = [cols.join(",")]; let n = 0, un = 0;
for (const [k, p] of Object.entries(h.p)) {
  const t = coicopOf(p.c, p.t);
  if (!t) un++;
  const sub = t ? t.split("-")[0] : "", cls = sub.split(".").slice(0, 3).join("."), div = sub.slice(0, 2);
  let cur = null, reg = null, e = 0;
  for (let d = 0; d < h.days.length; d++) {
    while (e < p.h.length && p.h[e][0] <= d) { cur = p.h[e][1]; reg = p.h[e][2]; e++; }
    if (!(cur > 0)) continue;
    lines.push([h.days[d], p.o, k.slice(k.indexOf("|") + 1), p.t, cur, reg ?? "", p.g, p.c, t || "", t ? CNODE[t].ar : "", t ? CNODE[t].en : "", sub, cls, cls ? (CNODE[cls] || {}).ar || "" : "", div, div ? (CNODE[div] || {}).ar || "" : "", p.u].map(q).join(","));
    n++;
  }
}
fs.writeFileSync(out, lines.join("\n") + "\n");
console.log(out, n, "rows,", Object.keys(h.p).length, "products,", un, "outside COICOP,", h.days.join(" "));
