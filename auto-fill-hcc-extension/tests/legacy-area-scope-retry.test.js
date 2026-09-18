// Cổng dichvucong dựng hỏng khối địa chỉ (dropdown Tỉnh/Xã không chọn được). Pass sửa lỗi cũ KHÔNG
// chữa được vì nó chỉ retry field ĐÃ từng điền thành công (eligibleNames = filledNames). Cách chữa:
// tick sang option khác của ô "Trong nước/Nước ngoài/Khác" rồi tick lại option cũ để cổng dựng lại
// khối, sau đó điền lần 2.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8");

assert.match(source, /function legacyAreaScopeGroup\(container\)/, "Phải tìm được ô tích phạm vi địa chỉ");
assert.match(source, /async function resetLegacyAreaScope\(container\)/, "Phải có bước tick lại ô phạm vi");
assert.match(source, /async function fillAreaWidgets\(container, data\)/, "Tách phần điền để gọi lại lần 2");

const start = source.indexOf("async function fillSelectArea(container, f)");
const end = source.indexOf("async function fillAreaWidgets(container, data)", start);
assert.ok(start >= 0 && end > start, "Không tách được fillSelectArea");
const wrapper = source.slice(start, end);

// Chỉ tick lại khi địa chỉ THẬT SỰ chưa vào (tránh phá khối đang đúng), và điền lại sau khi tick.
assert.match(wrapper, /if \(legacyAreaRolesFilled\(container, data\)\) return any;/);
assert.match(wrapper, /await resetLegacyAreaScope\(container\)/);
assert.match(wrapper, /const retried = await fillAreaWidgets\(fresh, data\);/);
// Không có Tỉnh/Xã để đối chiếu thì không tick lại.
assert.match(wrapper, /if \(!data\.tinh && !data\.xa\) return any;/);
// Tick lại có thể thay phần tử → phải lấy lại khối theo name trước khi điền lần 2.
assert.match(wrapper, /if \(!container\.isConnected\)[\s\S]*findNamedElement\("x-select-area", fieldCandidates\(f\)\)/);
// Mỗi lượt điền chỉ tick lại MỘT lần cho mỗi khối: tick vòng vòng làm mất dữ liệu ô khác trong khối.
assert.match(wrapper, /legacyAreaScopeResetRun\.get\(container\) === legacyFillRun/);
assert.match(source, /legacyFillRun\+\+;/, "Mỗi lượt fillForm phải mở lại quyền tick một lần");

const scopeStart = source.indexOf("function legacyAreaScopeGroup(container)");
const scopeEnd = source.indexOf("async function clickLegacyRadioOption", scopeStart);
const scope = source.slice(scopeStart, scopeEnd);
// Ô tích phải thuộc khối ngoài (không phải ô tích bên trong chính khối địa chỉ) và có option "Trong nước".
assert.match(scope, /group\.contains\(container\) \|\| container\.contains\(group\)/);
assert.match(scope, /labelOf\(box\)\.includes\("trong nuoc"\)/);
assert.match(scope, /\/khac\|nuoc ngoai\//, "Ưu tiên nhảy sang Khác/Nước ngoài rồi mới quay lại");

console.log("legacy area scope retry passed");
