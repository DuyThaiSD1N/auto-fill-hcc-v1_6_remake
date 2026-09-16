const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "sidebar.html"), "utf8");
const css = fs.readFileSync(path.join(root, "sidebar.css"), "utf8");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));

test("version trên header đọc từ manifest, ngày phát hành ghi tay đúng dạng và vào aria-label", () => {
  // Cán bộ đọc số ở header để báo lỗi, lệch với bản đang chạy là báo nhầm phiên bản. Số KHÔNG ghi
  // trong html nữa: sidebar.js đọc chrome.runtime.getManifest() lúc chạy — ghi tay từng trôi thật
  // (header "v1.2" trong khi extension đã lên 1.8). Chỉ ngày phát hành còn ghi tay ở data-ngay.
  const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
  assert.ok(manifest.version, "manifest phải có version");
  assert.match(html, /id="release-meta"[^>]*data-ngay="\d{2}\/\d{2}\/\d{4}"/, "header phải có data-ngay dạng dd/mm/yyyy");
  const khoi = sidebar.slice(sidebar.indexOf("getManifest().version"), sidebar.indexOf('getElementById("status")'));
  assert.match(khoi, /getElementById\("release-meta"\)/, "số trên header phải lấy từ manifest");
  assert.match(khoi, /phát hành ngày \$\{Number\(d\)\} tháng \$\{Number\(m\)\} năm \$\{y\}/, "aria-label phải đọc cả ngày phát hành");
});

test("panel hẹp xếp version xuống hàng riêng và giữ cụm nút cố định", () => {
  assert.match(css, /\.bot-h \.sp\s*\{[^}]*flex-shrink:\s*0/s);
  assert.match(css, /\.bot-h \.ib\s*\{[^}]*flex-shrink:\s*0/s);
  assert.match(
    css,
    /@media\s*\(max-width:\s*460px\)\s*\{[\s\S]*?\.bot-h \.title-line\s*\{[^}]*display:\s*grid[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)/
  );
});
