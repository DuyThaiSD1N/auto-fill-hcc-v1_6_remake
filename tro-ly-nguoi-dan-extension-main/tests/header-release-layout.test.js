const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "sidebar.html"), "utf8");
const css = fs.readFileSync(path.join(root, "sidebar.css"), "utf8");

test("version và ngày phát hành thống nhất trên header", () => {
  assert.match(html, /v1\.2 · 01\/09\/2026/);
  assert.match(html, /phát hành ngày 1 tháng 9 năm 2026/);
});

test("panel hẹp xếp version xuống hàng riêng và giữ cụm nút cố định", () => {
  assert.match(css, /\.bot-h \.sp\s*\{[^}]*flex-shrink:\s*0/s);
  assert.match(css, /\.bot-h \.ib\s*\{[^}]*flex-shrink:\s*0/s);
  assert.match(
    css,
    /@media\s*\(max-width:\s*460px\)\s*\{[\s\S]*?\.bot-h \.title-line\s*\{[^}]*display:\s*grid[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)/
  );
});
