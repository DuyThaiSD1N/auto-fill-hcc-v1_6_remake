// Đoạn mở đầu "⛔" (BE đặt cho cảnh báo cần xem lại trước khi nộp, vd trùng tên hộ kinh doanh) hiện đỏ đậm.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const read = (name) => fs.readFileSync(path.join(__dirname, "..", name), "utf8");

test("renderMarkdown gắn md-danger cho đoạn mở đầu ⛔, đoạn khác giữ nguyên", () => {
  const ctx = { window: {} };
  vm.runInNewContext(read("services/render.js"), ctx);
  const html = ctx.window.renderMarkdown("⛔ Cổng có **2 hộ kinh doanh** trùng\n\n✓ Đã điền xong\n- ⛔ dòng danh sách");
  assert.match(html, /<p class="md-danger">⛔ Cổng có <strong>2 hộ kinh doanh<\/strong> trùng<\/p>/);
  assert.match(html, /<p>✓ Đã điền xong<\/p>/);
  assert.match(html, /<li>⛔ dòng danh sách<\/li>/);
});

test("đỏ đậm thắng màu chữ đậm của bubble cảnh báo; bubble mở đầu ⛔ là tông cảnh báo", () => {
  assert.match(read("sidebar.css"),
    /\.msg\.bot \.md-danger, \.msg\.bot \.md-danger strong, \.msg\.bot\.warn \.md-danger strong \{ color: #b71c1c; font-weight: 700; \}/);
  assert.match(read("sidebar.js"), /if \(\/\^\(⚠️\|⚠\|❗\|🚫\|⛔\)\/\.test\(s\)\) return " warn";/);
});
