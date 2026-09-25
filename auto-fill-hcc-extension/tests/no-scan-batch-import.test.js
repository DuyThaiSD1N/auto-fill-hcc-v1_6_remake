// Tính năng "gom lô tệp quét có sẵn trong thư mục" đã GỠ, giống bản handfree. Nó đọc /v1/files rồi
// ĐOÁN tệp nào thuộc công dân đang ngồi đây theo khoảng cách thời gian: đoán chắc thì tự thêm cả
// lô vào hồ sơ, không chắc thì hiện hộp "Máy quét có nhiều file gần đây, chưa chắc cùng một người"
// cho cán bộ chọn tay. Nay chỉ nhận tệp máy quét bắn ra TRONG LÚC phiên đang mở.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");
const html = fs.readFileSync(path.join(root, "popup.html"), "utf8");
const css = fs.readFileSync(path.join(root, "popup.css"), "utf8");

test("không còn gom lô tệp quét có sẵn trên đĩa", () => {
  for (const dau of ["attemptBatchImport", "phanTichBatchGanNhat", "batchImportAttempted",
    "scanRecentPending", "renderScanRecentList", "addScanRecentItems",
    // Watermark chỉ phục vụ gom lô (chặn lô của công dân trước); gom lô gỡ rồi thì nó là code chết.
    "scanWatermarkMs", "restoreScanWatermark", "resetScanBatchImportState"]) {
    assert.ok(!popup.includes(dau), `popup.js còn "${dau}" — tính năng gom lô đã gỡ`);
  }
  assert.ok(!/scanRecentList|scan-recent/.test(html), "popup.html còn hộp danh sách tệp gần đây");
  assert.ok(!/scan-recent/.test(css), "popup.css còn style danh sách tệp gần đây");
});

test("những thứ PHẢI còn — không gỡ lố", () => {
  // 1. Luồng sống: file máy quét bắn ra lúc phiên đang mở vẫn tự vào hồ sơ.
  assert.match(popup, /onFile: handleScanAgentFile,/, "mất luồng nhận file quét lúc phiên đang mở");
  assert.match(popup, /async function importOneScanFile\(/);
  // 2. Đối soát: chỉ soi tệp ĐÃ nằm trong phiên (bị xoá/ghi đè lúc popup đóng), không tự thêm tệp lạ.
  assert.match(popup, /async function reconcileScanAgentFiles\(/);
  assert.match(popup, /void reconcileScanAgentFiles\(helpers\);/, "onConnected phải còn gọi đối soát");
  // 3. Nhớ tệp cán bộ đã gỡ tay: agent bắn lại file.added khi quét đè cùng nội dung.
  assert.match(popup, /function ghiNhanDaGo\(/);
  assert.match(popup, /if \(scanDaGo\.has\(hash\)\) return false;/);
});
