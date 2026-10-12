const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const src = fs.readFileSync(path.join(__dirname, "..", "content", "fill-surveyjs.js"), "utf8")
  .replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

test("form mới: bỏ qua tệp đã có trên dòng theo tên hoặc theo nội dung (SHA-256)", () => {
  assert.match(src, /crypto\.subtle\.digest\("SHA-256"/);
  assert.match(src, /sessionStorage\.getItem\(ATTACHED_KEY\)/);
  assert.match(src, /e\.hash === hash && e\.row === rowKey && count\(beforeText, fold\(e\.name\)\) > 0/);
  assert.match(src, /if \(count\(beforeText, wanted\) > 0 \|\| sameContent\) \{\s*skippedNames\.push/);
  assert.match(src, /if \(hash\) rememberAttached\(\{ hash, name: file\.name, row: rowKey \}\)/);
});

test("form mới: trả số tệp bỏ qua để panel/bot báo 'đã có'", () => {
  assert.match(src, /skipped: skippedNames\.length/);
});
