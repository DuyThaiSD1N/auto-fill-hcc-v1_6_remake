const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "sidebar.html"), "utf8");
const css = fs.readFileSync(path.join(root, "sidebar.css"), "utf8");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");

test("cài đặt mở trong panel và bánh răng đứng cạnh tài khoản", () => {
  const settingsButton = html.indexOf('id="settings-btn"');
  const accountButton = html.indexOf('id="acc-btn"');

  assert.ok(settingsButton > 0);
  assert.ok(accountButton > settingsButton);
  assert.match(html, /id="settings-screen"/);
  assert.match(html, /Tách giấy tờ trong file/);
  assert.match(html, /Tự tách file có nhiều giấy tờ; hai mặt CCCD cùng người vẫn gộp chung\./);
  assert.match(css, /body\.settings-mode[\s\S]*\.bot-b[\s\S]*display: none/);
  assert.match(sidebar, /function openSettingsScreen\(\)/);
  assert.match(sidebar, /function closeSettingsScreen\(/);
  assert.doesNotMatch(sidebar, /settings[^\n]{0,80}(window\.open|chrome\.tabs\.create)/i);
});

test("tùy chọn lưu theo máy và đi xuyên client context dưới dạng boolean riêng", () => {
  assert.match(sidebar, /ATTACH_SPLIT_DOCUMENTS_KEY = "tlnd_attach_split_documents"/);
  assert.match(sidebar, /let attachSplitDocuments = false/);
  assert.match(sidebar, /attachment_preferences:\s*\{ splitDocuments: attachSplitDocuments \}/);
  assert.match(sidebar, /chrome\.storage\.local\.set\([\s\S]*ATTACH_SPLIT_DOCUMENTS_KEY/);
  assert.match(sidebar, /chrome\.storage\?\.onChanged\?\.addListener/);
  assert.match(sidebar, /await restoreAttachmentSettings\(\)/);
  assert.doesNotMatch(sidebar, /attachment_preferences:\s*\{\s*splitMode:/);
});

test("mở cài đặt tạm dừng giọng nói nhưng không tắt chế độ rảnh tay", () => {
  const start = sidebar.indexOf("function openSettingsScreen");
  const end = sidebar.indexOf("function closeSettingsScreen", start);
  const openBlock = sidebar.slice(start, end);

  assert.match(openBlock, /settingsResumeHandsfree = handsfree/);
  assert.match(openBlock, /stopVoice\(\)/);
  assert.match(openBlock, /stopReplyTts\(\)/);
  assert.doesNotMatch(openBlock, /setHandsfree\(false\)/);
  assert.match(sidebar, /function startVoice\(\)[\s\S]*settings-mode/);
  assert.match(sidebar, /settingsResumeHandsfree && handsfree && voiceCfg\.asr[\s\S]*startVoice\(\)/);
});
