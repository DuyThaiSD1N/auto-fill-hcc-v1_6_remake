// Quay lại bước trước trên wizard tư pháp: trợ lý bấm nút "Quay lại" của cổng và đếm lại ô tờ khai khi lùi về Kê khai.
// BE (chat/step_back.py) chỉ bật khi thấy capability supportsStepBack.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = (...p) => fs.readFileSync(path.join(root, ...p), "utf8");
const strip = (code) => code.replace(/\/\/.*/g, "");
const sidebar = read("sidebar.js");
const guided = read("content", "guided-steps.js");

test("khai capability supportsStepBack", () => {
  const block = sidebar.match(/const CLIENT_CAPABILITIES = Object\.freeze\(\{([\s\S]*?)\}\);/);
  assert.ok(block, "không tìm thấy CLIENT_CAPABILITIES");
  assert.match(strip(block[1]), /supportsStepBack:\s*true/);
});

test("hai lệnh chạy ngoài runActions (không ask() lồng trong ask())", () => {
  const code = strip(sidebar);
  assert.match(code, /a\.type === "guided_click_back"\) \{\s*setTimeout\(\(\) => \{ void runGuidedBack\(\); \}, 0\);/);
  assert.match(code, /a\.type === "step_back_scan"\) \{\s*setTimeout\(\(\) => \{ void runStepBackScan\(a\); \}, 0\);/);
});

test("báo BE kết quả: không thấy nút / số ô tờ khai sau khi lùi", () => {
  const code = strip(sidebar);
  assert.match(code, /async function runGuidedBack\(\)[\s\S]*?action: "guidedClickBack"[\s\S]*?__event:step_back_failed/);
  assert.match(code, /async function runStepBackScan\(a\)[\s\S]*?action: "fieldReviewMark"[\s\S]*?__event:step_back_form:/);
});

test("engine bấm đúng nút Quay lại của cổng tư pháp", () => {
  const code = strip(guided);
  assert.match(code, /button\[data-e2e="btn-back"\]/);
  assert.match(code, /fold\(el\.textContent\) === "quay lai"/); // bước 3: nút trơn, khớp nguyên chữ
  assert.match(code, /msg\?\.action !== "guidedClickBack"/);
});

test("bấm nút Quay lại nằm cạnh nút đi tiếp của bước đang mở, ưu tiên trước mọi nút quay lại khác", () => {
  const code = strip(guided);
  assert.match(code, /STEP_ACTION_SELECTORS = \["#nop-thu-tuc-b-3"/);
  assert.match(code, /function findBackButton\(\) \{\s*const beside = stepBackButton\(\);\s*if \(beside\) return beside;/);
});

test("không bấm Quay lại hai lần liền (lùi 2 bước)", () => {
  const code = strip(guided);
  assert.match(code, /Date\.now\(\) - lastBackAt < BACK_COOLDOWN_MS[\s\S]*?lastBackAt = Date\.now\(\);\s*clickLikeUser\(button\);/);
});
