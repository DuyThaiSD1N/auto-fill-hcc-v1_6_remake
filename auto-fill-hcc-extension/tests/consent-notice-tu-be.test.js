// Thẻ xác nhận xử lý dữ liệu: chữ do BE cấp (GET /api/v1/consent/notice); tải lỗi mới dùng chữ viết sẵn.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const read = (f) => strip(fs.readFileSync(path.join(__dirname, "..", f), "utf8"));
const popup = read("popup.js");
const endpoints = read("api/endpoints.js");

test("API lấy nội dung thẻ từ BE", () => {
  assert.match(endpoints, /consentNotice\(\)\s*\{\s*return apiJson\("\/api\/v1\/consent\/notice"\);/);
});

test("mở thẻ: tải nội dung BE rồi mới hiện, tải lỗi giữ bản viết sẵn", () => {
  assert.match(popup, /async function openConsent\(\)[\s\S]*?const data = await loadConsentNotice\(\);\s*if \(data\) renderConsentNotice\(data\.notice, label\);[\s\S]*?showView\("consent"\);/);
  assert.match(popup, /await openConsent\(\);\s*return false;/);
  assert.match(popup, /async function loadConsentNotice\(\)[\s\S]*?catch \(e\)/);
});

test("đồng ý: gửi đúng version + chữ cam kết của bản đang hiện", () => {
  assert.match(popup, /const required = notice \? notice\.statements : CONSENT_STATEMENTS;/);
  assert.match(popup, /version: consentNotice\?\.version \|\| CONSENT_VERSION,/);
});

test("chữ từ BE luôn được thoát HTML trước khi nhấn đậm", () => {
  assert.match(popup, /function consentRich\(s\) \{ return escapeConsent\(s\)\.replace\(/);
  const render = popup.match(/function renderConsentNotice[\s\S]*?\n\}/)[0];
  const lines = render.split("\n").filter((l) => l.includes("innerHTML ="));
  assert.ok(lines.length >= 4);
  for (const l of lines) assert.match(l, /consentRich\(/, l.trim());
});
