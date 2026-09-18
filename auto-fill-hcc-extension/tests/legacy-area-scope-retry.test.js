// Cổng dichvucong dựng hỏng khối địa chỉ (dropdown Tỉnh/Xã không chọn được). Pass sửa lỗi cũ KHÔNG
// chữa được vì nó chỉ retry field ĐÃ từng điền thành công (eligibleNames = filledNames). Cách chữa:
// tick sang option khác của ô "Trong nước/Nước ngoài/Khác" rồi tick lại option cũ để cổng dựng lại
// khối, sau đó điền lần 2 — và CHỈ hai lượt đó, không retry thêm.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8");

assert.match(source, /function legacyAreaScopeGroup\(container\)/, "Phải tìm được ô tích phạm vi địa chỉ");
assert.match(source, /async function resetLegacyAreaScope\(container\)/, "Phải có bước tick lại ô phạm vi");
assert.match(source, /async function fillAreaWidgets\(container, data/, "Tách phần điền để gọi lại lần 2");

const start = source.indexOf("async function fillSelectArea(container, f)");
const end = source.indexOf("async function fillAreaWidgets(container, data", start);
assert.ok(start >= 0 && end > start, "Không tách được fillSelectArea");
const wrapper = source.slice(start, end);

// Điền được rồi thì CHỐT: khối giữ viền xanh, không tick lại ô phạm vi, không chọn lại dropdown.
assert.match(
  wrapper,
  /if \(state\.fills && legacyAreaRolesFilled\(container, data\) && legacyAreaDetailFilled\(container, data\)\) \{[\s\S]*?return true;/,
  "Đã điền được thì trả về luôn, không điền lại"
);
// Chưa vào thì tick lại ô phạm vi rồi điền lần 2.
assert.match(wrapper, /await resetLegacyAreaScope\(container\)/);
assert.match(wrapper, /const retried = await fillAreaWidgets\(fresh, data\);/);
// Lượt 1 KHÔNG tô đỏ — còn lượt 2 phía sau, tô đỏ ngay chỉ làm khối nháy đỏ rồi xanh.
assert.match(wrapper, /fillAreaWidgets\(container, data, \{ markMissing: false \}\)/);
assert.match(source, /async function pickInWidget\(root, value, \{ markMissing = true \} = \{\}\)/);
assert.match(source, /if \(markMissing\) markUnfilled\(root\.querySelector\("\.input-field-select"\) \|\| root\);/);
// Không có Tỉnh/Xã để đối chiếu thì không tick lại.
assert.match(wrapper, /if \(!data\.tinh && !data\.xa\) return fillAreaWidgets\(container, data\);/);
// Tick lại có thể thay phần tử → phải lấy lại khối theo name trước khi điền lần 2.
assert.match(wrapper, /if \(!container\.isConnected\)[\s\S]*findNamedElement\("x-select-area", fieldCandidates\(f\)\)/);
// Tối đa HAI lượt điền cho mỗi khối trong một lần fill — bỏ hẳn kiểu retry nhiều lượt của pass sửa lỗi.
assert.match(source, /const LEGACY_AREA_MAX_FILLS = 2;/);
assert.match(wrapper, /if \(state\.fills >= LEGACY_AREA_MAX_FILLS\) return false;/);
assert.match(source, /legacyFillRun\+\+;/, "Mỗi lượt fillForm phải mở lại hạn mức điền");

const widgetStart = source.indexOf("async function fillAreaWidgets(container, data");
const widgetEnd = source.indexOf("async function fillSelectDefault", widgetStart);
const widgets = source.slice(widgetStart, widgetEnd);
// Dropdown đã đúng sẵn thì giữ nguyên (tô xanh), không chọn lại làm cổng load lại tầng dưới.
assert.match(widgets, /if \(legacyChoiceMatches\(before, val\)\) \{[\s\S]*markFilled\([\s\S]*continue;/);
assert.match(widgets, /await pickInWidget\(w, val, \{ markMissing \}\)/);

const scopeStart = source.indexOf("function legacyAreaScopeGroup(container)");
const scopeEnd = source.indexOf("async function clickLegacyRadioOption", scopeStart);
const scope = source.slice(scopeStart, scopeEnd);
// Ô tích phải thuộc khối ngoài (không phải ô tích bên trong chính khối địa chỉ) và có option "Trong nước".
assert.match(scope, /group\.contains\(container\) \|\| container\.contains\(group\)/);
assert.match(scope, /labelOf\(box\)\.includes\("trong nuoc"\)/);
assert.match(scope, /\/khac\|nuoc ngoai\//, "Ưu tiên nhảy sang Khác/Nước ngoài rồi mới quay lại");

console.log("legacy area scope retry passed");
