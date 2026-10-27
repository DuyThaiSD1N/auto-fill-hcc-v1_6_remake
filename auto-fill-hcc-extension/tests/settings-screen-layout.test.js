// Màn Cài đặt: chia nhóm theo tần suất dùng tại quầy, nhãn "Tài khoản" cho mục lưu ở BE, báo lưu / lỗi ngay dưới
// dòng vừa bấm (dòng báo cuối trang bị khuất khi màn cuộn), cài đặt tài khoản không tải được thì nói rõ + Thử lại.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const html = fs.readFileSync(path.join(root, "sidebar.html"), "utf8");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const css = fs.readFileSync(path.join(root, "sidebar.css"), "utf8");
const screen = html.slice(html.indexOf('<section class="settings-screen"'), html.indexOf("</section>",
  html.indexOf('<section class="settings-screen"')));

test("4 nhóm theo đúng thứ tự: nhận giấy → đính kèm → điền tờ khai → hiển thị", () => {
  const titles = [...screen.matchAll(/<h2 class="settings-group-title">([^<]+)<\/h2>/g)].map((m) => m[1]);
  assert.deepEqual(titles, ["Nhận giấy tờ", "Đính kèm hồ sơ", "Điền tờ khai", "Hiển thị &amp; giọng đọc"]);
  const order = ["prefer-scan-switch", "attach-split-switch", "rename-files-switch", "attach-mode-group",
    "submitter-declaration-switch", "panel-mode-group", "voice-group"].map((id) => screen.indexOf(`id="${id}"`));
  assert.ok(order.every((pos, i) => pos > 0 && (i === 0 || pos > order[i - 1])));
});

test("chỉ hai mục lưu theo tài khoản mang nhãn Tài khoản", () => {
  const chips = [...screen.matchAll(/class="settings-chip">Tài khoản</g)];
  assert.equal(chips.length, 2);
  assert.match(screen, /id="rename-files-label"[^>]*>[^<]*<\/label><span\s+class="settings-chip">Tài khoản/);
  assert.match(screen, /id="submitter-declaration-label"[^>]*>[^<]*<\/label><span\s+class="settings-chip">Tài khoản/);
});

test("nút chọn không dùng emoji (hiển thị khác nhau giữa các máy quầy)", () => {
  for (const id of ["panel-mode-push", "panel-mode-side", "attach-mode-merge", "attach-mode-split"]) {
    const btn = screen.slice(screen.indexOf(`id="${id}"`), screen.indexOf("</button>", screen.indexOf(`id="${id}"`)));
    assert.match(btn, /<b>[^<]+<\/b><small>[^<]+<\/small>/, id);
    assert.doesNotMatch(btn, /\p{Extended_Pictographic}/u, id);
  }
  assert.doesNotMatch(sidebar, /v\.gender === "nam" \? "👨" : "👩"/);
  assert.match(sidebar, /name\.textContent = v\.label;/);
});

test("mỗi dòng có chỗ báo riêng; bỏ dòng báo chung cuối trang", () => {
  for (const id of ["prefer-scan", "attach-split", "rename-files", "attach-mode", "submitter-declaration",
    "panel-mode", "voice"]) {
    assert.match(screen, new RegExp(`class="settings-row-status" id="${id}-status" role="status"`), id);
  }
  assert.doesNotMatch(html, /id="settings-saved"/);
  assert.doesNotMatch(sidebar, /\$settingsSaved|announceAttachmentSettingsSaved/);
  assert.match(css, /\.settings-row-status:empty \{ display: none; \}/);
  // "✓ Đã lưu" tự tắt; lỗi giữ lại kèm Thử lại.
  assert.match(sidebar, /setSettingStatus\(id, "✓ Đã lưu"\);\s*settingsStatusTimers\.set\(id, setTimeout/);
  assert.match(sidebar, /setSettingStatus\(id, "Chưa lưu được\.", \{ error: true, retry \}\);/);
  assert.match(sidebar, /announceSettingFailed\("prefer-scan-status", \(\) => savePreferScan\(value\)\);/);
  assert.match(sidebar, /announceSettingFailed\(statusId, \(\) => saveAccountSetting\(changes, statusId\)\);/);
});

test("cài đặt tài khoản: đang tải / không tải được thì nói rõ, kèm Thử lại", () => {
  const block = sidebar.slice(sidebar.indexOf("async function refreshAccountSettings()"),
    sidebar.indexOf("function forgetAccountSettings()"));
  assert.match(block, /if \(!accountSettingsLoaded\) \{\s*for \(const id of ACCOUNT_STATUS_IDS\) setSettingStatus\(id, "Đang tải cài đặt tài khoản…", \{ pending: true \}\);/);
  assert.match(block, /"Chưa tải được cài đặt tài khoản\.", \{ error: true, retry: refreshAccountSettings \}/);
});
