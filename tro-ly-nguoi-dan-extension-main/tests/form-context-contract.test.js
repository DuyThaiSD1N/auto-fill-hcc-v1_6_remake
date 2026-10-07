const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const fillCore = fs.readFileSync(path.join(root, "content/fill-core.js"), "utf8");

test("trợ lý gửi formContext vào chat giống auto-fill", () => {
  assert.match(fillCore, /msg\.action === "collectFormContext"/);
  assert.match(fillCore, /const formContext = collectFormContext\(\);/);
  // eForm Bộ Tư pháp: gộp dữ liệu VNeID của tài khoản (getDataEform) như auto-fill.
  assert.match(fillCore, /collectMojAccountContext\(\)\s*\.then\(\(account\) => sendResponse\(\{ ok: true, formContext: \{ \.\.\.formContext, \.\.\.account \} \}\)\)/);
  assert.match(fillCore, /api\/eform-service\/eform\/getDataEform/);
  assert.match(sidebar, /sendToContent\(\{ action: "collectFormContext" \}\)/);
  assert.match(sidebar, /form_context: formResult\?\.formContext \|\| \{\}/);
  assert.match(sidebar, /attachment_context: attachmentResult\?\.attachmentContext \|\| \{\}/);
  // preferredLang: ngôn ngữ máy quầy (tiếng Mông) để phiên MỚI chào đúng tiếng ngay lượt đầu.
  assert.match(sidebar, /api\.ask\(message, \{ source, displayText, clientContext, preferredLang \}\)/);
});
