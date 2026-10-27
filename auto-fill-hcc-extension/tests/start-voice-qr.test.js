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
  assert.match(sidebar, /\$startMic\?\.addEventListener\("click", \(\) => \{[\s\S]*?startByVoice = true;\s*if \(voiceListening\) setMicUI\(true, [^)]*\);\s*else void startVoice\(\);/);
  assert.match(sidebar, /if \(startByVoice\) \{\s*startByVoice = false;\s*setMicUI\(false\);\s*showStartHeard\([^;]*\);\s*if \(text\) \{[\s\S]*?void beginConversation\(text\);/);
  assert.match(sidebar, /if \(spoken\) \{\s*addUserText\(spoken, "", true\);\s*await ask\(spoken, "voice"\);/);
});

test("VNeID không có ảnh mã QR sau ~6s → loginQrMissing, sidebar mở panel và gửi trạng thái", () => {
  assert.match(content, /document\.querySelector\('img\[alt="qr_images"\]'\)/);
  assert.match(content, /performance\.now\(\) > 6000/);
  assert.match(sidebar, /\|\| ctx\.loginQrMissing\s*\)\) restorePanel\(\);/);
  assert.match(sidebar, /\|\$\{ctx\.loginQrMissing \? 1 : 0\}[^`]*`;/);
  assert.match(sidebar, /loginQrMissing: !!c\.loginQrMissing,/);
});

test("nút Tải lại trang: khai cờ, lệnh reload_page → content tải lại trang", () => {
  assert.match(sidebar, /supportsPageReload: true,/);
  assert.match(sidebar, /a\.type === "reload_page"\) \{\s*window\.parent\.postMessage\(\{ __tlnd: "reloadPage" \}, "\*"\);/);
  assert.match(content, /else if \(t === "reloadPage"\) location\.reload\(\);/);
});

test("nói ở màn bắt đầu = bật sẵn Rảnh tay, chưa mở mic tới khi trợ lý đọc xong câu đầu", () => {
  assert.match(sidebar, /if \(startByVoice\) \{[\s\S]{0,260}if \(text\) \{[\s\S]*?setHandsfree\(true, \{ listen: false \}\);\s*void beginConversation\(text\);/);
  assert.match(sidebar, /function setHandsfree\(on, \{ listen = true \} = \{\}\) \{[\s\S]*?\$hfBtn\?\.classList\.toggle\("active", on\);\s*if \(on && !listen\) return;/);
});

test("màn bắt đầu hiện lời công dân đang nói: partial nhạt, final đậm, không nghe được thì nhắc nói lại", () => {
  const html = fs.readFileSync(path.join(root, "sidebar.html"), "utf8");
  assert.match(html, /<p id="start-heard" class="start-heard" aria-live="polite" hidden><\/p>/);
  assert.match(sidebar, /if \(startByVoice\) showStartHeard\(msg\.text \|\| "", "partial"\);/);
  assert.match(sidebar, /showStartHeard\(text \|\| "Em chưa nghe rõ[^"]*", text \? "final" : "miss"\);/);
});

test("màn bắt đầu: không tự mở mic ngầm; nút mic chỉ tắt khi chính nó đang nghe; về màn bắt đầu thì tắt Rảnh tay", () => {
  assert.match(sidebar, /&& !document\.body\.classList\.contains\("start-mode"\)\s*&& !window\.__hccTTS\?\.isSpeaking/);
  assert.match(sidebar, /if \(voiceListening && !startByVoice && document\.body\.classList\.contains\("start-mode"\)\) \{\s*pauseMic\(\);/);
  assert.match(sidebar, /if \(voiceListening && startByVoice\) \{ startByVoice = false; showStartHeard\(""\); stopVoice\(\); return; \}/);
  assert.match(sidebar, /function showStartScreen\(\) \{[\s\S]{0,200}if \(handsfree\) setHandsfree\(false\);/);
  assert.match(sidebar, /if \(chatBootFinished && document\.body\.classList\.contains\("start-mode"\)\) \{ rememberHandsfree\(false\); return; \}/);
});
