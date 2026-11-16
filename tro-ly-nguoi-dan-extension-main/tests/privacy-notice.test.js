// Thông báo bảo vệ dữ liệu cá nhân: hiện trước khi mở phiên từ màn bắt đầu, một nút xác nhận, chữ lấy từ BE.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const sidebar = strip(fs.readFileSync(path.join(root, "sidebar.js"), "utf8"));
const html = fs.readFileSync(path.join(root, "sidebar.html"), "utf8");

test("mở phiên từ màn bắt đầu: chờ xác nhận thông báo rồi mới tạo conversation", () => {
  assert.match(sidebar, /async function beginConversation\(spoken = ""\) \{[\s\S]*?await showPrivacyNotice\(\);\s*showChatScreen\(Date\.now\(\)\);[\s\S]*?await ask\("", "system"\);/);
  assert.match(sidebar, /if \(busy \|\| endingSession \|\| beginningConversation\) return;/);
});

test("đổi / làm thủ tục khác cùng công dân không đi qua beginConversation nên không hiện lại", () => {
  const body = sidebar.match(/async function returnToStart[\s\S]*?\n  \}\n/)[0];
  assert.doesNotMatch(body, /beginConversation|showPrivacyNotice/);
  assert.match(body, /if \(shouldOpenProcedurePicker\) \{[\s\S]*?showProcedurePicker\(\);\s*\}\s*else \{\s*showStartScreen\(\);/);
});

test("chữ thông báo lấy từ voice/config, BE cũ không gửi thì bỏ qua; chỉ có một nút", () => {
  assert.match(sidebar, /const n = voiceCfg\?\.privacyNotice;\s*if \(!Array\.isArray\(n\?\.summary\) \|\| !n\.summary\.length\) return;/);
  assert.match(sidebar, /\$ok\.addEventListener\("click", resolve, \{ once: true \}\)/);
  const dialog = html.match(/<div class="pdp" id="pdp"[\s\S]*?<\/div>\s*<\/div>\s*<\/div>/)[0];
  assert.equal((dialog.match(/<button/g) || []).length, 2, "chỉ nút xem đầy đủ + nút xác nhận");
  assert.doesNotMatch(html, /Đồng ý và dùng|Không dùng/);
});
