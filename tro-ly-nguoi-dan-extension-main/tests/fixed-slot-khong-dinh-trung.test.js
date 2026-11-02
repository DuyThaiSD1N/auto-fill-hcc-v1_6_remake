// Đính kèm lại ô cố định (vd mai táng BYT): tệp cùng tên đã có trên dòng thì không gắn thêm bản trùng.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const src = fs.readFileSync(path.join(__dirname, "..", "content", "attach-core.js"), "utf8");
const code = src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

function fnBody(signature) {
  const start = code.indexOf(signature);
  assert.ok(start >= 0, `thiếu ${signature}`);
  const next = code.slice(start + 10).search(/\n(async )?function /);
  return code.slice(start, next > 0 ? start + 10 + next : undefined);
}

test("filesNotOnRow lần theo tệp nguồn (hành vi chi tiết: attach-dedupe-source-memory.test.js ở handfree)", () => {
  const fn = fnBody("function filesNotOnRow(");
  assert.match(fn, /const shown = attpRowAttachedFingerprints\(row\);/);
  assert.match(fn, /shownIndexForFile\(shown, file, memory\)/);
  assert.match(fn, /shown\.splice\(at, 1\)/);
});

test("fixed-slot dạng input chỉ gắn tệp chưa có trên dòng và báo số tệp bỏ qua", () => {
  const fn = fnBody("async function attachFilesByFixedSlot(");
  const filter = fn.indexOf("const pending = filesNotOnRow(markTarget, files)");
  assert.ok(filter > 0);
  assert.ok(filter < fn.indexOf("setFilesOnInput(input, pending"));
  assert.match(fn, /skipped: skippedNames\.length,\s*fileNames: attachedNames,\s*skippedNames,/);
});

test("luồng chính cộng tệp bỏ qua của fixed-slot vào báo cáo", () => {
  assert.match(code, /attachedNames\.push\(\.\.\.\(fixedResult\.fileNames \|\| \[\]\)\);\s*skippedNames\.push\(\.\.\.\(fixedResult\.skippedNames \|\| \[\]\)\);/);
});

test("fixed-slot dạng menu (liên thông) chỉ gắn tệp chưa có trên dòng, cả ô chính lẫn ô dự phòng", () => {
  const fn = fnBody("async function attachFilesByFixedSlot(");
  const menu = fn.slice(fn.indexOf("const tryMenuSlot"));
  const filter = menu.indexOf("const pending = filesNotOnRow(markTarget, files)");
  assert.ok(filter > 0 && filter < menu.indexOf("await openMenuGetFileInput(trigger)"));
  assert.match(menu, /setFilesOnInput\(menuInput, pending,/);
  assert.match(menu, /pendingNames\.every\(/);
  assert.match(menu, /attachedNames\.push\(\.\.\.first\.attached\);\s*skippedNames\.push\(\.\.\.first\.skipped\);/);
  assert.match(menu, /attachedNames\.push\(\.\.\.second\.attached\);\s*skippedNames\.push\(\.\.\.second\.skipped\);/);
});

test("Giấy tờ khác iGate: dòng cùng tên đã mang đúng tệp thì không thêm dòng mới", () => {
  const fn = fnBody("async function attachOneFileToOtherListFile(");
  const check = fn.indexOf("otherListFileRows().find(");
  assert.ok(check > 0 && check < fn.indexOf("await ensureOtherListFileRow(componentName)"));
  assert.match(fn, /attachmentKeyEquals\(otherListFileNameInput\(candidate\)\?\.value, componentName\)/);
  assert.match(fn, /skippedNames: \[file\.name\]/);
  assert.match(code, /attachedNames\.push\(\.\.\.\(result\.fileNames \|\| \[\]\)\);\s*skippedNames\.push\(\.\.\.\(result\.skippedNames \|\| \[\]\)\);/);
});

test("Bộ Công an: dùng lại dòng tự thêm lượt trước, chỉ gắn tệp chưa có, toàn bộ đã có thì không báo lỗi", () => {
  const fn = fnBody("async function attachFilesByBcaPlan(");
  assert.match(fn, /const reusable = item\.newRow && files\.length && bcaGroupRows\(container\)\.find/);
  assert.ok(fn.indexOf("const reusable") < fn.indexOf("await bcaAddRow("));
  assert.match(fn, /const pending = filesNotOnRow\(row, files\);/);
  assert.match(fn, /if \(!attachedNames\.length && !skippedNames\.length\) return \{ error/);
  assert.match(fn, /skipped: skippedNames\.length, skippedNames,/);
});
