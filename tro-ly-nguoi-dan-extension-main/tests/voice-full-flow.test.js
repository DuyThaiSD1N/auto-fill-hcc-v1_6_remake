// Giọng nói toàn trình: nút nào đang hiện thì nói được nút đó. BE chọn nút theo lời nói; nút cần
// extension gom dữ liệu trên trang thì BE nhờ "bấm hộ" (press_chip), nhóm nút đã dùng thì khoá lại
// (chip_used), thẻ xin phép trả lời bằng lời thì tự tích + khoá (consent_verbal).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = (f) => fs.readFileSync(path.join(root, f), "utf8");
const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const js = strip(read("sidebar.js"));

test("khai capability supportsVoiceChips", () => {
  assert.match(js, /supportsVoiceChips: true,/);
});

test("press_chip: bấm đúng nút còn sống, ngoài runActions, không thêm bong bóng nhãn nút", () => {
  const i = js.indexOf('a.type === "press_chip"');
  assert.ok(i > 0);
  const block = js.slice(i, js.indexOf('a.type === "chip_used"', i));
  assert.match(block, /setTimeout\(\(\) => \{/);
  assert.match(block, /b\.dataset\.send === a\.send && !b\.disabled/);
  assert.match(block, /chipPressByVoice = true;\s*btn\.click\(\);/);
  assert.match(js, /const byVoice = chipPressByVoice;\s*chipPressByVoice = false;/);
  assert.match(js, /if \(!byVoice\) addUserText\(c\.label, c\.labelHmong\);/);
});

test("chip_used khoá cả nhóm nút; consent_verbal tích đủ ô và khoá thẻ", () => {
  assert.match(js, /a\.type === "chip_used" && a\.send[\s\S]{0,300}x\.disabled = true;/);
  assert.match(js, /a\.type === "consent_verbal"\) \{\s*markConsentVerbal\(!!a\.accepted\);/);
  const fn = js.slice(js.indexOf("function markConsentVerbal("), js.indexOf("function foldVi("));
  assert.match(fn, /if \(accepted\) el\.querySelectorAll\('input\[type="checkbox"\]'\)\.forEach\(\(b\) => \{ b\.checked = true; \}\);/);
  assert.match(fn, /el\.querySelectorAll\("button, input"\)\.forEach\(\(x\) => \{ x\.disabled = true; \}\);/);
});

test("câu nhận từ giọng nói hiện 🎙 + nghiêng", () => {
  assert.match(js, /if \(voice\) el\.classList\.add\("voice"\);/);
  assert.match(js, /addUserText\(text, "", true\);\s*ask\(text, "voice"\);/);
  assert.match(read("sidebar.css"), /\.msg\.user\.voice::before \{ content: "🎙 "/);
});
