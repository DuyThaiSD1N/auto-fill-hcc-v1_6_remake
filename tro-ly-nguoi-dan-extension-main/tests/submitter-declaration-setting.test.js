// Cài đặt theo tài khoản "Lấy người nộp theo tờ khai" (BE /api/v1/account/settings, khoá submitterFromDeclaration).
// Extension chỉ bật/tắt; BE đọc từ tài khoản khi chạy pipeline. Khoá: mặc định tắt (hành vi cũ), công tắc khoá tới
// khi đọc được giá trị từ BE, đăng xuất phải trả về tắt, lưu gửi đúng khoá.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const stripComments = (src) => src.replace(/\/\/[^\n]*/g, "");
const sidebar = stripComments(fs.readFileSync(path.join(root, "sidebar.js"), "utf8"));
const html = fs.readFileSync(path.join(root, "sidebar.html"), "utf8");

function slice(src, startMarker, endMarker) {
  const start = src.indexOf(startMarker);
  const end = src.indexOf(endMarker, start + startMarker.length);
  assert.ok(start >= 0 && end > start, `Không tìm thấy khối ${startMarker}`);
  return src.slice(start, end);
}

assert.match(html, /id="submitter-declaration-switch"[^>]*aria-checked="false"[^>]*disabled/,
  "công tắc mặc định tắt và khoá tới khi đọc được giá trị từ BE");
assert.match(html, /Lấy người nộp theo tờ khai/);

assert.match(sidebar, /let submitterFromDeclaration = false;/, "mặc định tắt");
assert.match(slice(sidebar, "function storeAccountSettings", "\n  }\n"),
  /submitterFromDeclaration = settings\?\.submitterFromDeclaration === true;/,
  "BE cũ thiếu khoá → coi như tắt");
assert.match(slice(sidebar, "function forgetAccountSettings", "\n  }\n"), /submitterFromDeclaration = false;/,
  "đăng xuất không được để cài đặt của cán bộ trước áp sang người sau");
assert.match(slice(sidebar, "function renderSubmitterDeclarationSetting", "\n  }\n"),
  /\.disabled = !accountSettingsLoaded/, "khoá khi chưa đọc được / đang lưu");
assert.match(sidebar, /saveAccountSetting\(\{ submitterFromDeclaration: !submitterFromDeclaration \}\)/,
  "bấm công tắc gửi đúng khoá lên BE");

// Chế độ tờ khai: BE gắn enableInput cho họ tên + CCCD Phần I → engine điền phải bỏ disabled trước khi ghi.
const fillCore = stripComments(fs.readFileSync(path.join(root, "content/fill-core.js"), "utf8"));
const enableFn = slice(fillCore, "function enableStandardFieldInputs", "\n}\n");
assert.match(enableFn, /node\.removeAttribute\("disabled"\)/);
assert.match(slice(fillCore, "async function fillFormStandard", "try {"),
  /if \(f\.enableInput\) enableStandardFieldInputs\(f, candidates, occurrence\);/,
  "phải bỏ khoá TRƯỚC khi điền ô");

// Field `clear` (vd ngày sinh tài khoản VNeID khi tờ khai không có ngày sinh đầy đủ): xoá trắng + tô đỏ, và bước
// điền lại ô trống không được ghi đè lại.
const loop = slice(fillCore, "async function fillFormStandard", "async function reapplyEmptyStandardTextFields");
assert.match(loop, /f\.clear \? clearStandardDate\(el\)/);
assert.match(loop, /if \(f\.clear\) ok = clearStandardInput\(el\);/);
assert.match(loop, /if \(ok && f\.clear\) markStandardCleared\(f, candidates, occurrence\);/);
assert.match(slice(fillCore, "async function reapplyEmptyStandardTextFields", "\n}\n"), /!f\.clear/);

console.log("submitter declaration setting (handfree) passed");
