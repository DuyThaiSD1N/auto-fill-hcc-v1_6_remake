// Đăng nhập VNeID xong, cổng liên thông đưa về TRANG CHỦ (#/) chứ không quay lại link kê khai đang mở dở. Trang chủ
// không có tín hiệu nào watcher nhận ra → bot đứng chờ "đăng nhập VNeID". Extension phải nhận ra trang chủ (thẻ thủ tục
// có id mã TTHC) và báo cờ lienThongHome để BE mở lại link kê khai.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const strip = (s) => s.replace(/^\s*\/\/.*$/gm, "");
const content = strip(fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8"));
const sidebar = strip(fs.readFileSync(path.join(__dirname, "..", "sidebar.js"), "utf8"));

test("content nhận ra trang chủ liên thông theo thẻ thủ tục, trừ trang kê khai", () => {
  assert.match(content, /const lienThongHome = location\.hostname === "lienthong\.dichvucong\.gov\.vn" && !keKhaiForm/);
  assert.match(content, /\.teca-card-container-new\[id\]/);
  assert.match(content, /\n\s*lienThongHome,\n/);
});

test("sidebar coi lienThongHome là tín hiệu trang, đưa vào chữ ký watcher và gửi BE", () => {
  assert.match(sidebar, /\|\| c\.maeAgencyBlock \|\| c\.lienThongHome/);
  assert.match(sidebar, /const sig = `[^`]*\$\{ctx\.lienThongHome \? 1 : 0\}`;/);
  assert.match(sidebar, /lienThongHome: !!c\.lienThongHome,/);
});
