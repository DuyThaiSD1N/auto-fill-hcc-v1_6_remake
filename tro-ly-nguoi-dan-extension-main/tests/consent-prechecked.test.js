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

test("phạm vi + mục đích xử lý dữ liệu nằm trong khối thu gọn như khối Điều 4, chữ giữ nguyên", () => {
  const src = require("node:fs").readFileSync(require("node:path").join(__dirname, "..", "sidebar.js"), "utf8");
  assert.match(src, /<details class="clegal cinfo"><summary>Phạm vi, mục đích xử lý dữ liệu<\/summary>[\s\S]*?card\.scope_md[\s\S]*?card\.purpose_md[\s\S]*?<\/details>/);
});
