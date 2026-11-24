// Form cũ (eForm x-*): field mang cờ "clear" là ô cổng đổ sẵn từ tài khoản đăng nhập nhưng thuộc người khác — engine
// phải XOÁ ô (kể cả ô ngày), và coi ô đã trống là đạt; bản điền thường bỏ qua giá trị rỗng nên ô cũ còn nguyên.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const legacy = fs.readFileSync(path.join(root, "content/fill-legacy.js"), "utf8").replace(/^\s*\/\/.*$/gm, "");

test("fillLegacyComponent chuyển field clear sang nhánh xoá", () => {
  assert.match(legacy, /async function fillLegacyComponent\([^)]*\)[^{]*\{\s*if \(field\.clear\) return clearLegacyComponent\(container, field\);/);
  assert.match(legacy, /case "x-date":\s*case "x-date-text": return clearLegacyDate\(container, field\);/);
});

test("ô ngày clear đạt khi cả ngày / tháng / năm đã trống", () => {
  assert.match(legacy, /if \(field\.clear\) \{\s*const empty = \[day, month, year\]\.every/);
});
