// Ô lồng trong khối x-select-area không có thẻ x-* riêng (khối mẹ / cha nuôi của tờ khai nuôi con nuôi): engine điền tìm
// ô ngày theo ô con `<tên>-day`, ô tích theo checkbox cùng name, dropdown không tên theo khối + nhãn BE gửi kèm.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const legacy = strip(fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8"));

test("không thấy ô theo tên thì tìm ô lồng trước khi báo không tìm thấy", () => {
  assert.match(legacy, /if \(!found\.el\) \{\s*const nested = findNestedLegacyControl\(f\);\s*if \(nested\) found = \{ el: nested, usedName: f\.name \};\s*\}\s*const container = found\.el;/);
});

test("ô ngày / ô tích / dropdown không tên trong khối lồng", () => {
  assert.match(legacy, /input\[name="\$\{CSS\.escape\(n\)\}-day"\]/);
  assert.match(legacy, /input\[type="checkbox"\]\[name="\$\{CSS\.escape\(n\)\}"\]/);
  assert.match(legacy, /!f\.label \|\| !Array\.isArray\(f\.containers\)/);
  assert.match(legacy, /foldLegacyChoice\(nestedControlLabel\(widget\)\)\.includes\(wanted\)/);
});
