// Màn bắt đầu nói được ("bắt đầu" / tên thủ tục); VNeID không hiện mã QR → nút tải lại trang.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const sidebar = strip(fs.readFileSync(path.join(root, "sidebar.js"), "utf8"));
const html = fs.readFileSync(path.join(root, "sidebar.html"), "utf8");
const content = strip(fs.readFileSync(path.join(root, "content.js"), "utf8"));

test("màn bắt đầu có nút mic; câu nói đầu tiên mở phiên và gửi luôn làm câu đầu", () => {
  assert.match(html, /id="start-mic-btn" class="start-mic"/);
  assert.match(sidebar, /\$startMic\?\.addEventListener\("click", \(\) => \{[\s\S]*?startByVoice = true;\s*void startVoice\(\);/);
  assert.match(sidebar, /if \(startByVoice\) \{\s*startByVoice = false;\s*setMicUI\(false\);\s*if \(text\) void beginConversation\(text\);/);
  assert.match(sidebar, /if \(spoken\) \{\s*addUserText\(spoken, "", true\);\s*await ask\(spoken, "voice"\);/);
});

test("VNeID không có ảnh mã QR sau ~6s → loginQrMissing, sidebar mở panel và gửi trạng thái", () => {
  assert.match(content, /document\.querySelector\('img\[alt="qr_images"\]'\)/);
  assert.match(content, /performance\.now\(\) > 6000/);
  assert.match(sidebar, /\|\| ctx\.loginQrMissing\s*\)\) restorePanel\(\);/);
  assert.match(sidebar, /\|\$\{ctx\.loginQrMissing \? 1 : 0\}`;/);
  assert.match(sidebar, /loginQrMissing: !!c\.loginQrMissing,/);
});

test("nút Tải lại trang: khai cờ, lệnh reload_page → content tải lại trang", () => {
  assert.match(sidebar, /supportsPageReload: true,/);
  assert.match(sidebar, /a\.type === "reload_page"\) \{\s*window\.parent\.postMessage\(\{ __tlnd: "reloadPage" \}, "\*"\);/);
  assert.match(content, /else if \(t === "reloadPage"\) location\.reload\(\);/);
});
