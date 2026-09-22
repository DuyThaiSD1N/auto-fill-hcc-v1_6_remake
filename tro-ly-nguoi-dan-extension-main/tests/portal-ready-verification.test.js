const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");

test("nút phao 'Kiểm tra lại trang hiện tại' đã bỏ khỏi UI", () => {
  // Yêu cầu 22/09/2026. Lọc ở FE chứ KHÔNG gỡ chip ở backend: backend còn phục vụ bản
  // extension cũ trên chợ vốn dựa vào nút này để công dân tự yêu cầu đọc lại trang.
  assert.doesNotMatch(sidebar, /renderChips\(\[\{ label: "Kiểm tra lại trang hiện tại"/);
  assert.match(sidebar, /chips\.filter\(\(c\) => c\.send !== "__event:sso_success"\)/);
  // Không được thay bằng lời xác nhận suông "đã vào trang" — phải đọc DOM thật.
  assert.doesNotMatch(sidebar, /label: "Tôi đã vào trang làm hồ sơ"/);
});

test("hết ~60s chưa nhận ra trang thì tự đọc lại DOM, không đứng im", () => {
  const block = sidebar.match(/watcherTicks >= 17 && !fallbackChipShown\) \{([\s\S]*?)\} else if/);
  assert.ok(block, "thiếu nhánh phao sau ~60 giây");
  assert.match(block[1], /void verifyPortalState\(\)/);
});

test("action xác minh đọc lại DOM rồi gửi page_status có cờ manualCheck", () => {
  assert.match(sidebar, /a\.type === "verify_portal_state"/);
  assert.match(sidebar, /async function verifyPortalState\(\)[\s\S]*readPageContext\(\)[\s\S]*sendPageStatus\(\{ \.\.\.\(ctx\?\.ok \? ctx : \{ ok: true \}\), manualCheck: true \}\)/);
  assert.match(sidebar, /setTimeout\(\(\) => \{ void verifyPortalState\(\); \}, 0\)/);
  assert.match(sidebar, /manualCheck: !!c\.manualCheck/);
});

test("xác minh được hoãn khỏi request hiện tại để không kẹt hàng đợi ask", () => {
  const actionStart = sidebar.indexOf('a.type === "verify_portal_state"');
  const nextAction = sidebar.indexOf('a.type === "prepare_business_registration"', actionStart);
  const block = sidebar.slice(actionStart, nextAction);
  assert.match(block, /setTimeout\(\(\) => \{ void verifyPortalState\(\); \}, 0\)/);
});
