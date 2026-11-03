// Đính kèm lại ô cố định / Giấy tờ khác iGate: tệp cùng tên đã có trên dòng thì không gắn thêm bản trùng.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const src = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");
const code = src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

function fnBody(signature) {
  const start = code.indexOf(signature);
  assert.ok(start >= 0, `thiếu ${signature}`);
  const next = code.slice(start + 10).search(/\n  (async )?function /);
  return code.slice(start, next > 0 ? start + 10 + next : undefined);
}

test("filesNotOnRow lần theo tệp nguồn (hành vi chi tiết: attach-dedupe-source-memory.test.js ở handfree)", () => {
  const fn = fnBody("function filesNotOnRow(");
  assert.match(fn, /const shown = attpRowAttachedFingerprints\(row\);/);
  assert.match(fn, /shownIndexForFile\(shown, file, memory\)/);
  assert.match(fn, /shown\.splice\(at, 1\)/);
});

test("fixed-slot dạng input và menu chỉ gắn tệp chưa có trên dòng, báo số tệp bỏ qua", () => {
  const fn = fnBody("async function attachFilesByFixedSlot(");
  assert.equal((fn.match(/const pending = filesNotOnRow\(markTarget, files\)/g) || []).length, 2);
  assert.ok(fn.indexOf("filesNotOnRow(markTarget, files)") < fn.indexOf("setFilesOnInput(input, pending"));
  assert.match(fn, /setFilesOnInput\(menuInput, pending,/);
  assert.doesNotMatch(fn, /skipped: 0,/);
  assert.doesNotMatch(fn, /skippedNames: \[\],/);
});

test("Giấy tờ khác iGate: dòng cùng tên đã mang đúng tệp thì không thêm dòng mới", () => {
  const fn = fnBody("async function attachOneFileToOtherListFile(");
  const check = fn.indexOf("otherListFileRows().find(");
  assert.ok(check > 0 && check < fn.indexOf("await ensureOtherListFileRow(componentName)"));
  assert.match(fn, /skippedNames: \[file\.name\]/);
  assert.match(code, /attachedNames\.push\(\.\.\.\(result\.fileNames \|\| \[\]\)\);\s*skippedNames\.push\(\.\.\.\(result\.skippedNames \|\| \[\]\)\);/);
});
