// node build.js : concatenates src/ into scraping-panel.html
const fs = require("fs"), path = require("path");
const dir = path.join(__dirname, "src");
const files = fs.readdirSync(dir).sort();
const html = files.filter((f) => f.endsWith(".html")).map((f) => fs.readFileSync(path.join(dir, f), "utf8")).join("\n");
const js = files.filter((f) => f.endsWith(".js")).map((f) => `// ---- ${f}\n` + fs.readFileSync(path.join(dir, f), "utf8")).join("\n");
const out = html + "\n<script>\n\"use strict\";\n" + js.replace(/^"use strict";\n/m, "") + "\n</script>\n";
fs.writeFileSync(path.join(__dirname, "scraping-panel.html"), out);
console.log("built", out.split("\n").length, "lines", Buffer.byteLength(out), "bytes");
