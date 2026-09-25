// Tính năng "dùng lại hồ sơ trước" đã GỠ (chốt nghiệp vụ 23/09/2026).
//
// Nó chép NGUYÊN ẢNH giấy tờ công dân vào chrome.storage.local để mời dùng lại ở hồ sơ kế tiếp.
// Test chốt hai thứ: code không quay lại (qua merge/ghi đè từ một bản cũ — popup.js đã từng mất
// code theo đúng đường đó), và dữ liệu cũ còn trên máy quầy được dọn.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");
const html = fs.readFileSync(path.join(root, "popup.html"), "utf8");
const css = fs.readFileSync(path.join(root, "popup.css"), "utf8");

for (const dau of ["renderPrevSessionOffer", "reusePrevSession", "archiveCurrentSessionAsPrev",
  "readPrevSession", "PREV_SESSION_KEY"]) {
  assert.ok(!popup.includes(dau), `popup.js còn "${dau}" — tính năng dùng lại hồ sơ trước đã gỡ`);
}
assert.ok(!/prevSessionOffer|prev-session-offer/.test(html), "popup.html còn khối lời mời");
assert.ok(!/prev-session-offer|prev-offer/.test(css), "popup.css còn style lời mời");

// Dữ liệu cũ (ảnh giấy tờ công dân) phải được dọn, không để nằm lại trên máy quầy.
assert.match(popup, /k\.startsWith\("autofill_prev_session_"\)/);
assert.match(popup, /void purgeLegacyPrevSessions\(\);/);

// Hàm ánh xạ snapshot vẫn DÙNG CHUNG cho saveSession/restoreSession — không được gỡ theo.
assert.match(popup, /function fileItemToSnapshot\(/);
assert.match(popup, /function fileItemFromSnapshot\(/);

console.log("không còn tính năng dùng lại hồ sơ trước, dữ liệu cũ được dọn passed");
