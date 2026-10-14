// Tính năng "gom lô tệp quét có sẵn trong thư mục" đã GỠ (chốt nghiệp vụ 23/09/2026).
// Nó đọc /v1/files rồi ĐOÁN tệp nào thuộc công dân đang ngồi đây theo khoảng cách thời gian; đoán
// không chắc hoặc lô quá cũ thì hiện hộp "Máy quét có tệp gần đây, chưa chắc của công dân này" cho
// cán bộ chọn tay. Nay chỉ nhận tệp máy quét bắn ra trong lúc phiên đang mở.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const html = fs.readFileSync(path.join(root, "sidebar.html"), "utf8");
const css = fs.readFileSync(path.join(root, "sidebar.css"), "utf8");

for (const dau of ["thuGomLoQuet", "hienDanhSachGanDay", "themTuDanhSachGanDay",
  "scanRecentPending", "scanLoDaThuSid", "TLNDScanLo"]) {
  assert.ok(!sidebar.includes(dau), `sidebar.js còn "${dau}" — tính năng gom lô đã gỡ`);
}
assert.ok(!/scan-recent/.test(html), "sidebar.html còn khối danh sách tệp gần đây");
assert.ok(!/scan-recent/.test(css), "sidebar.css còn style danh sách tệp gần đây");
assert.ok(!/scanLo\.js/.test(html), "sidebar.html còn nạp lib/scanLo.js");
assert.ok(!fs.existsSync(path.join(root, "lib/scanLo.js")), "lib/scanLo.js chưa xoá");

// Hai thứ PHẢI còn lại, nếu không là gỡ lố:
// 1. Watermark — chốt chặn duy nhất còn lại giữa giấy của hai công dân liên tiếp.
assert.match(sidebar, /if \(scanWatermarkMs && mtime && mtime <= scanWatermarkMs\) return false;/,
  "mất watermark là kéo giấy công dân trước sang hồ sơ công dân sau");
// 2. Đối soát — nó chỉ soi những tệp ĐÃ nằm trên phiên này (bắt ca bị xoá/ghi đè lúc Trợ lý đóng),
//    không bao giờ tự thêm tệp lạ, nên không thuộc diện gỡ.
assert.match(sidebar, /async function doiSoatTepQuet\(\)/, "lượt đối soát không nằm trong diện gỡ");

console.log("không còn gom lô tệp quét, chỉ nhận tệp quét lúc phiên đang mở passed");
