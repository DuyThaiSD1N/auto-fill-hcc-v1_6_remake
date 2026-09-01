const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");

test("nút phao yêu cầu kiểm tra trang thay vì xác nhận đã vào hồ sơ", () => {
  assert.match(sidebar, /label: "Kiểm tra lại trang hiện tại", send: "__event:sso_success"/);
  assert.doesNotMatch(sidebar, /label: "Tôi đã vào trang làm hồ sơ"/);
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
