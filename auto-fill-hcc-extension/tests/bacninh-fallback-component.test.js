// Bắc Ninh mở eform cũ (link mã cũ) thì thành phần hồ sơ mang mã cũ: BE gửi kèm fallbackComponentName, engine đính
// thử mã này khi mã chính không có trên trang (cùng logic với tro-ly-nguoi-dan-extension/content/fill-bacninh.js).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const src = fs.readFileSync(path.join(__dirname, "..", "content", "fill-bacninh.js"), "utf8");

test("đính kèm Bắc Ninh thử mã thành phần dự phòng khi mã chính không có trên trang", () => {
  assert.match(src, /fallbackComponentName: item\.fallbackComponentName \|\| ""/);
  assert.match(src, /findComponentId\(index, g\.componentName\)\s*\|\| \(g\.fallbackComponentName \? findComponentId\(index, g\.fallbackComponentName\) : null\)/);
});
