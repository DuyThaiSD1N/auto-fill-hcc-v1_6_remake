// Điền đợt 2 trên form Angular (cổng liên thông): BE soát lại sau lượt điền đầu, engine ghi lại RIÊNG các ô BE sửa —
// không đè ô cán bộ đã sửa tay, giữ viền của lượt điền đầu, và chỉ bản khai năng lực "secondPassAngular" mới chạy.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8").replace(/^\s*\/\/.*$/gm, "");
const angular = read("content/fill-angular.js");
const patch = angular.slice(angular.indexOf("function ngShownArea"), angular.indexOf("function readAngularField"));

test("bộ ghi lại ô Angular chỉ ghi ô còn trống hoặc còn đúng giá trị lượt đầu", () => {
  assert.match(patch, /function ngPatchUntouched\(f\)/);
  assert.match(patch, /return hasFirst && ngSameText\(shown, f\.from\);/);
  assert.match(patch, /result\.skipped\.push\(\{ name: f\.name, reason: untouched === false \? "changed" : "not-found" \}\);/);
});

test("bộ ghi lại ô dùng bộ điền lượt đầu, giữ viền đã tô", () => {
  assert.match(patch, /await fillFormAngular\(todo, \{ keepMarks: true \}\)/);
  assert.match(angular, /async function fillFormAngular\(fields, opts = \{\}\) \{[\s\S]*?if \(!opts\.keepMarks\) clearAutofillMarks\(\);/);
  assert.match(angular, /H\.patchFormAngular = patchFormAngular;/);
});

test("điều phối patchFields chọn bộ ghi Angular, bản khai năng lực secondPassAngular", () => {
  assert.match(read("content/fill-core.js"), /formKind === "angular" \? H\.patchFormAngular : null;/);
  assert.match(read("sidebar.js"), /supportsSecondPassAngular: true,/);
});

test("đọc ô ngày Angular theo ô nhập ngày, không theo chữ ô chọn định dạng", () => {
  const reader = angular.slice(angular.indexOf("function readAngularField"));
  assert.match(reader, /if \(f\.comp === "date" \|\| f\.comp === "ngaysinh"\) \{[\s\S]*?ngVisibleInputs\(el\)[\s\S]*?getAttribute\("maxlength"\) === "10"/);
});
