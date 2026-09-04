const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const content = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");
const popup = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");

assert.match(content, /const PAGE_TOAST_ID = "autofill-hcc-page-toast"/);
assert.match(content, /host\.attachShadow\(\{ mode: "open" \}\)/, "Toast phải cách ly khỏi CSS của cổng");
assert.match(content, /toast\.setAttribute\("role", "status"\)/);
assert.match(content, /toast\.setAttribute\("aria-live", "polite"\)/);
assert.match(content, /@media \(prefers-reduced-motion: reduce\)/);
assert.match(content, /}, 5000\);/, "Toast phải tự ẩn sau khoảng 5 giây");
assert.match(content, /msg\?\.action === "showPageToast"/);
assert.match(content, /if \(ok\) showPageToast\("Đã đính kèm xong hồ sơ\.", "success"\)/);

assert.match(popup, /async function showPageToast\(message, kind = "success"\)/);
assert.match(popup, /Đã điền xong \$\{filled\} thông tin\./);
assert.match(popup, /Đã đính kèm xong hồ sơ\./);
assert.match(popup, /Đã xử lý xong bước đính kèm\. Vui lòng rà soát hồ sơ\./);

console.log("page toast: fill/attach success, accessibility and reduced motion passed");
