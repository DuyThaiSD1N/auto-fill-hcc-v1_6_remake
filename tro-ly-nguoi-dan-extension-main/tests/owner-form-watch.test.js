// Bước "Thông tin chủ hồ sơ": sau khi trợ lý điền, công dân có thể tự gõ nốt ô còn trống trên trang thay vì trả lời
// câu hỏi. Watcher phải báo lại BE khi số ô còn trống đổi (chỉ ở owner_waiting_next) để BE tự thấy đủ và đưa nút sang
// bước đính kèm — chữ ký trang cũ không có trạng thái ô nên gõ đủ rồi bot vẫn đứng hỏi.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const sidebar = fs.readFileSync(path.join(__dirname, "..", "sidebar.js"), "utf8")
  .replace(/^\s*\/\/.*$/gm, "");

test("chữ ký watcher có trạng thái ô chủ hồ sơ", () => {
  assert.match(sidebar, /const sig = `[^`]*\|\$\{ownerFormSig\(ctx\)\}[^`]*`;/);
});

test("chỉ tính ô chủ hồ sơ ở owner_waiting_next, bước 1", () => {
  const fn = sidebar.match(/const ownerFormSig = \(ctx\) => \([\s\S]*?\);/);
  assert.ok(fn, "thiếu ownerFormSig");
  assert.match(fn[0], /lastState === "owner_waiting_next"/);
  assert.match(fn[0], /ctx\.wizardStep === 1/);
  assert.match(fn[0], /ctx\.ownerForm\.missing/);
});

const portalDvc = fs.readFileSync(path.join(__dirname, "..", "content", "portal-dvc.js"), "utf8");

test("nút lưu Thông tin định danh: khai cờ, chạy ngoài runActions, báo lại BE", () => {
  assert.match(sidebar, /supportsSaveOwnerProfile: true,/);
  assert.match(sidebar, /a\.type === "save_owner_profile"\) \{\s*setTimeout\(\(\) => \{ void runSaveOwnerProfile\(\); \}, 0\);/);
  assert.match(sidebar, /__action:save_owner_profile_report:/);
});

test("engine lưu: tick checkbox Radix rồi bấm Xác nhận hộp thoại ghi đè", () => {
  const fn = portalDvc.match(/async function saveOwnerProfile\(\) \{[\s\S]*?\n  \}/);
  assert.ok(fn, "thiếu saveOwnerProfile");
  assert.match(fn[0], /aria-checked/);
  assert.match(fn[0], /role="alertdialog"/);
  assert.match(fn[0], /"xac nhan"/);
  // Cổng lưu ngay khi Xác nhận và có thể bỏ dấu tick → toast thành công là tín hiệu chính.
  assert.match(fn[0], /cap nhat thong tin nguoi dung thanh cong/);
  assert.match(portalDvc, /msg\?\.action !== "saveOwnerProfile"/);
});
