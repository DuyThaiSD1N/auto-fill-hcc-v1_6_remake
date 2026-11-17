const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const read = (file) => fs.readFileSync(path.join(__dirname, "..", file), "utf8");
const content = read("content.js");
const patch = content.slice(content.indexOf("function standardPatchSame("), content.indexOf("async function patchFormStandard(") + 900);

test("form Form.io: bộ ghi lại ô đợt 2 chỉ ghi ô còn như lượt đầu hoặc đang trống", () => {
  assert.match(patch, /H\.formSnapshot\?\.readFields\?\.\(\[f\], "standard"\)/);
  assert.match(patch, /return hasFirst && standardPatchSame\(/);
  assert.match(patch, /if \(untouched === false \|\| \(untouched === null && !isNew\)\) \{[\s\S]{0,200}reason: untouched === false \? "changed" : "not-found"/);
  assert.match(patch, /await fillFormStandard\(todo, \{ keepMarks: true \}\)/);
});

test("lượt ghi đợt 2 giữ màu các ô lượt đầu", () => {
  assert.match(content, /async function fillFormStandard\(fields, \{ keepMarks = false \} = \{\}\) \{\s*injectAutofillStyles\(\);\s*if \(!keepMarks\) clearAutofillMarks\(\);/);
});

test("handler patchFields gọi bộ ghi Form.io; popup khai năng lực secondPassFormio", () => {
  // Cổng Form.io bọc khung Angular (Bộ Y tế) bị nhận "angular": ô data[...] / dom-* vẫn đi bộ ghi Form.io.
  assert.match(content, /const standardPatch = patch\.some\(\(f\) =>\s*String\(f\?\.comp \|\| ""\)\.startsWith\("dom-"\) \|\| String\(f\?\.name \|\| ""\)\.startsWith\("data\["\)\);/);
  assert.match(content, /formKind === "standard" \|\| \(formKind === "angular" && standardPatch\) \? H\.patchFormStandard/);
  assert.match(content, /fillFormStandard, patchFormStandard,/);
  assert.match(read("popup.js"), /"secondPassFormio"\]/);
});
