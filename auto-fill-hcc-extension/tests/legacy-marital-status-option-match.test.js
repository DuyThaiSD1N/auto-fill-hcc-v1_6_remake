const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8");

const start = source.indexOf("function foldLegacyChoice");
const end = source.indexOf("\nfunction legacyChoiceHasWord", start);
assert.ok(start >= 0 && end > start, "Không tách được foldLegacyChoice");

const sandbox = {};
vm.runInNewContext(
  `${source.slice(start, end)}\nglobalThis.fold = foldLegacyChoice;`,
  sandbox
);
const fold = sandbox.fold;

// Option "=5" của mục (14) Tình trạng hôn nhân. Backend gửi nhãn có ký tự "…", cổng render
// bằng ba dấu chấm và khoảng trắng không đều -> phải fold về cùng một chuỗi, nếu không dropdown
// bị bỏ trống và người dân bị điền nhầm sang option "đã ly hôn".
const fromBackend =
  "Từ ngày… tháng… năm… đến ngày… tháng… năm … chưa đăng ký kết hôn với ai; hiện tại đang có vợ/chồng";
const onPortal =
  "Từ ngày... tháng... năm... đến ngày... tháng... năm... chưa đăng ký kết hôn với ai; hiện tại đang có vợ/chồng";
assert.equal(fold(fromBackend), fold(onPortal));

// Các option còn lại không được gộp nhầm vào nhau.
const divorced =
  "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng đã ly hôn; hiện tại chưa đăng ký kết hôn với ai";
const widowed =
  "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng vợ/chồng đã chết; hiện tại chưa đăng ký kết hôn với ai";
assert.notEqual(fold(divorced), fold(widowed));
assert.notEqual(fold(fromBackend), fold(divorced));

// Dấu chấm đơn (viết tắt địa danh) vẫn giữ nguyên để không phá khớp tên phường/xã.
assert.equal(fold("P.10"), "p.10");
assert.equal(fold("Phường Xuân Hương - Đà Lạt"), "phuong xuan huong da lat");

console.log("legacy marital status option match passed");
