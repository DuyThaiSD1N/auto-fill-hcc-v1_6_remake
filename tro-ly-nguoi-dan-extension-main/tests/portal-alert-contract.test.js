// Lời cổng nháy ở toast: khung Trợ lý không che toast (dời sang trái) và trợ lý nói lại lời cổng (BE: chat/portal_alert.py).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = (...p) => fs.readFileSync(path.join(root, ...p), "utf8");
const strip = (code) => code.replace(/\/\/.*/g, "");
const sidebar = strip(read("sidebar.js"));
const guided = strip(read("content", "guided-steps.js"));
const content = strip(read("content.js"));

test("khai capability supportsPortalAlert", () => {
  const block = sidebar.match(/const CLIENT_CAPABILITIES = Object\.freeze\(\{([\s\S]*?)\}\);/);
  assert.ok(block);
  assert.match(block[1], /supportsPortalAlert:\s*true/);
});

test("mở Trợ lý thì dời khung toast góc phải sang trái, thu Trợ lý thì trả lại", () => {
  assert.match(content, /function applySidebarPushLayout\(\) \{[\s\S]*?ensureToastShiftStyle\(\);\s*\}/);
  assert.match(content, /function restoreSidebarPushLayout\(\) \{[\s\S]*?getElementById\(TOAST_SHIFT_ID\)\?\.remove\(\);\s*\}/);
  assert.match(content, /#toast-container\.toast-top-right[^{]*\{right:\$\{w \+ 12\}px!important;\}/);
});

test("bắt toast trong lớp fixed, bỏ toast thành công, bỏ toast từ cú bấm của trợ lý", () => {
  const scan = guided.match(/function scanToasts\(\) \{[\s\S]*?\n  \}/);
  assert.ok(scan, "không tìm thấy scanToasts");
  assert.match(scan[0], /Date\.now\(\) < ownClickUntil\) return/);
  assert.match(scan[0], /inFixedLayer\(el\)/);
  assert.match(scan[0], /includes\("success"\)/);
  assert.match(scan[0], /__tlnd: "portalAlert", text/);
  assert.match(guided, /async function pressAndWatch\(button\) \{[\s\S]*?ownClickUntil = Date\.now\(\) \+ OWN_CLICK_MS;/);
});

test("sidebar chỉ nhận toast của đúng tab rồi gửi portal_alert", () => {
  assert.match(sidebar, /__tlnd !== "portalAlert" \|\| String\(sender\?\.tab\?\.id \|\| ""\) !== String\(TAB_ID\)/);
  assert.match(sidebar, /ask\(`__event:portal_alert:\$\{JSON\.stringify\(\{ text \}\)\}`, "system"\)/);
});
