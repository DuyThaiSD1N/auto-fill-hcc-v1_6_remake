const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const html = fs.readFileSync(path.join(__dirname, "..", "popup.html"), "utf8");
const css = fs.readFileSync(path.join(__dirname, "..", "popup.css"), "utf8");
const js = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");

assert.match(html, /id="status"[^>]*role="status"[^>]*aria-live="polite"[^>]*aria-atomic="true"/);
assert.match(
  html,
  /id="statusDetailsToggle"[^>]*aria-expanded="false"[^>]*aria-controls="statusDetails"[^>]*hidden>Xem chi tiết/,
);
assert.match(html, /id="statusDetails"[^>]*role="region"[^>]*hidden/);

assert.match(js, /safeDetails\.length === 0/);
assert.match(js, /statusDetailsToggle\.textContent = expanded \? "Xem chi tiết" : "Ẩn chi tiết"/);
assert.match(js, /statusEl\.setAttribute\("role", type === "err" \? "alert" : "status"\)/);
assert.match(js, /console\.warn\("\[AutoFill\] Cảnh báo trích xuất:", errors\)/);
assert.doesNotMatch(js, /Không khớp:\s*\$\{fillRes\.notFound/);

assert.match(css, /\.status-details-toggle:hover\s*\{[\s\S]*?background:\s*#e8f2fd;[\s\S]*?color:\s*#0b467f;/);
assert.match(css, /\.status-details-toggle:focus-visible\s*\{[\s\S]*?outline:\s*3px solid rgba\(21, 101, 192, 0\.24\);/);
assert.match(css, /\.status-details\[hidden\],[\s\S]*?\.status-details-toggle\[hidden\]\s*\{\s*display:\s*none;/);

console.log("status details UI: concise, conditional and accessible disclosure passed");
