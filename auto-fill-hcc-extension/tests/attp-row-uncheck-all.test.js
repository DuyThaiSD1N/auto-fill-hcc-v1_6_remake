// Cổng dvc.moc (Bộ Xây dựng) tick sẵn mọi dòng → BE gửi untickUnplannedRows, FE bấm "Chọn/Bỏ chọn tất cả"
// (tối đa 2 lần, tới khi không còn dòng tick) trước khi đính; đã có dòng mang tệp thì không bấm.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const src = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");
const code = src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

function body(name) {
  const start = code.indexOf(`async function ${name}(`);
  assert.ok(start >= 0, `thiếu ${name}`);
  const next = code.indexOf("\n  async function ", start + 10);
  return code.slice(start, next > 0 ? next : undefined);
}

test("uncheckAllAttpRows bấm ô chọn tất cả tối đa 2 lần và bỏ qua khi đã có tệp", () => {
  const fn = body("uncheckAllAttpRows");
  assert.match(fn, /\.check-all-checkbox/);
  assert.match(fn, /i < 2 && anyRowChecked\(\)/);
  assert.match(fn, /attpRowAttachedFingerprints\(row\)\.length\)\) return false/);
});

test("attachFilesByAttpRow chỉ bỏ chọn tất cả khi BE gửi cờ, trước vòng tick dòng", () => {
  const fn = body("attachFilesByAttpRow");
  const gate = fn.indexOf("item.untickUnplannedRows)) await uncheckAllAttpRows()");
  assert.ok(gate > 0);
  assert.ok(gate < fn.indexOf("await tickAttpRowCheckbox(row)"));
});
