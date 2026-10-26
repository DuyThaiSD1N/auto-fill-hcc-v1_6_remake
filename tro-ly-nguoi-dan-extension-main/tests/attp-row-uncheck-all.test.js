// Cổng dvc.moc (Bộ Xây dựng) tick sẵn mọi dòng → BE gửi untickUnplannedRows, FE bấm "Chọn/Bỏ chọn tất cả"
// (tối đa 2 lần, tới khi không còn dòng tick) trước khi đính; đã có dòng mang tệp thì không bấm.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const src = fs.readFileSync(path.join(__dirname, "..", "content", "attach-core.js"), "utf8");
const code = src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

function body(name) {
  const start = code.indexOf(`async function ${name}(`);
  assert.ok(start >= 0, `thiếu ${name}`);
  const next = code.indexOf("\nasync function ", start + 10);
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

test("attachFilesByAttpRow bỏ tick các dòng untickRows không nằm trong kế hoạch, trước vòng tick dòng", () => {
  const fn = body("attachFilesByAttpRow");
  const gate = fn.indexOf("item.untickRows || []");
  assert.ok(gate > 0);
  assert.match(fn, /if \(row && !planned\) await untickAttpRowCheckbox\(row\);/);
  assert.ok(gate < fn.indexOf("await tickAttpRowCheckbox(row)"));
  assert.match(body("untickAttpRowCheckbox"), /!cb\.checked \|\| attpRowAttachedFingerprints\(row\)\.length\) return false/);
});

test("target add-document-dialog đi engine modal Thêm giấy tờ, có dòng dự phòng fallbackComponentName", () => {
  const dispatch = body("attachFilesByPlan");
  assert.match(dispatch, /item\.target === "add-document-dialog"\)\) \{/);
  assert.match(dispatch, /return await attachFilesWithAddDocumentDialog\(payloadFiles, allAttachments\);/);
  const mixed = body("attachFilesWithAddDocumentDialog");
  assert.ok(mixed.indexOf("attachFilesByFixedSlot") < mixed.indexOf("ensureAddDocumentRows(addDocumentItems)"));
  assert.ok(mixed.indexOf("attachFilesByAttpRow(payloadFiles, attpItems)") < mixed.indexOf("ensureAddDocumentRows("));
  assert.match(mixed, /componentName: item\.fallbackComponentName/);
  assert.match(code, /const ensureAddDocumentRows = \(\(\) => \{/);
  assert.match(code, /fold\(textOf\(node\)\)\.endsWith\("them giay to"\)/);
});
