// Thẻ xin phép xử lý dữ liệu: 2 ô cam kết tích sẵn, công dân chỉ bấm "Đồng ý"; biên bản ghi prechecked.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const sidebar = strip(fs.readFileSync(path.join(__dirname, "..", "sidebar.js"), "utf8"));

test("thẻ xin phép: 2 ô cam kết tích sẵn, nút Đồng ý bấm được ngay, báo prechecked cho biên bản", () => {
  assert.match(sidebar, /<label class="ccheck"><input type="checkbox" data-i="\$\{i\}" checked>/);
  assert.match(sidebar, /boxes\.forEach\(\(b\) => b\.addEventListener\("change", sync\)\);[\s\S]{0,300}?sync\(\);/);
  assert.match(sidebar, /accepted, checks: boxes\.map\(\(b\) => b\.checked\), prechecked: true,/);
});
