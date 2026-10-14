// Tính năng "dùng lại hồ sơ trước" đã GỠ (chốt nghiệp vụ 23/09/2026), cả hai bản extension.
// Bản này cất THAM CHIẾU giấy tờ (tlnd_ho_so_truoc_<tab>); chốt code không quay lại và khoá cũ
// trên máy quầy được dọn.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const html = fs.readFileSync(path.join(root, "sidebar.html"), "utf8");
const css = fs.readFileSync(path.join(root, "sidebar.css"), "utf8");

for (const dau of ["catHoSoTruoc", "docHoSoTruoc", "hienLoiMoiHoSoTruoc", "dungLaiHoSoTruoc",
  "KHOA_HO_SO_TRUOC", "$hoSoTruoc"]) {
  assert.ok(!sidebar.includes(dau), `sidebar.js còn "${dau}" — tính năng dùng lại hồ sơ trước đã gỡ`);
}
assert.ok(!/prev-session-offer/.test(html), "sidebar.html còn khối lời mời");
assert.ok(!/prev-session-offer|prev-offer/.test(css), "sidebar.css còn style lời mời");
assert.ok(!/source: "reuse"/.test(sidebar), "còn đường tải lại giấy tờ từ phiên cũ");

assert.match(sidebar, /k\.startsWith\("tlnd_ho_so_truoc_"\)/, "phải dọn khoá cũ còn trên máy quầy");

console.log("không còn tính năng dùng lại hồ sơ trước, khoá cũ được dọn passed");
