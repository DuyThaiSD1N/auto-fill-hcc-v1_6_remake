// Field mang cờ "clear": backend biết ô này đang giữ dữ liệu VNeID của NGƯỜI KHÁC (người nộp hộ)
// nên yêu cầu xóa trắng thay vì điền. Giữ lại sẽ thành họ tên người này + giấy tờ người kia.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8");

assert.match(
  source,
  /if \(field\.clear\) return clearLegacyComponent\(container, field\);/,
  "fillLegacyComponent phải rẽ nhánh xóa trước khi điền"
);
assert.match(source, /function clearLegacyInput\(container, f\)/);
assert.match(source, /function clearLegacyDate\(container, f\)/);
assert.match(source, /async function clearLegacySelect\(container\)/);
assert.match(
  source,
  /const placeholder = options\(\)\.find\(\(o\) => isPlaceholderOpt\(norm\(o\.textContent\)\)\);/,
  "Dropdown chỉ về trống được bằng option giữ chỗ"
);

// legacyFieldState: field clear coi là XONG khi ô đã trống, nếu không guard sẽ retry mãi và
// báo "Không khớp" giả.
assert.match(
  source,
  /filled: !!input && \(field\.clear \? empty : legacyScalarMatches\(input\.value, field\.value\)\)/
);
assert.match(source, /if \(field\.clear\) \{\s*\n\s*const empty = \[day, month, year\]/);

// Ô đã xóa vẫn là ô người dùng phải tự nhập → luôn đỏ.
assert.match(source, /if \(state\.filled && !field\.clear\)/);

console.log("legacy clear prefilled field: clear branch, empty-state and red mark passed");
