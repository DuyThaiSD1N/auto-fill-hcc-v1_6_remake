const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8");

function functionSource(name, nextName) {
  const start = source.indexOf(`function ${name}`);
  let end = source.indexOf(`\nfunction ${nextName}`, start);
  if (end < 0) end = source.indexOf(`\nasync function ${nextName}`, start);
  assert.ok(start >= 0 && end > start, `Không tách được helper ${name}`);
  return source.slice(start, end);
}

const sandbox = {
  setNativeValue(input, value, options) {
    input.value = value;
    input.options = options;
  },
  markFilled(element) {
    element.marked = true;
  },
};

vm.runInNewContext(`
  ${functionSource("hasDivorceDecisionAreaValue", "selectAreaTextControls")}
  ${functionSource("fillDivorceDecisionAreaByKnownNames", "fillDivorceDecisionArea")}
  globalThis.hasStructuredValue = hasDivorceDecisionAreaValue;
  globalThis.fillStructuredValue = fillDivorceDecisionAreaByKnownNames;
`, sandbox);

const wrapper = {};
const spouseInput = { value: "", parentElement: wrapper };
const container = {
  querySelector(selector) {
    return selector === 'input[name="voChongHoTen"]' ? spouseInput : null;
  },
};
const value = { voChongHoTen: "VŨ HỮU NINH" };

assert.equal(
  sandbox.hasStructuredValue(value),
  true,
  "Object chỉ có tên vợ/chồng vẫn phải được nhận diện là vùng tình trạng hôn nhân động",
);
// Hàm trả về BÁO CÁO chi tiết (any + used + cờ từng ô) để tầng gọi biết ô nào còn phải
// khớp theo nhãn / theo vị trí, thay vì một cờ boolean gộp.
const report = sandbox.fillStructuredValue(container, value);
assert.equal(report.any, true);
assert.equal(report.numberHandled, false, "Vùng =2 không có ô số bản án");
assert.ok(report.used.has(spouseInput), "Ô đã điền phải nằm trong used để tầng sau bỏ qua");
assert.equal(spouseInput.value, "VŨ HỮU NINH");
assert.equal(spouseInput.options.typing, true);
assert.equal(spouseInput.options.commit, true);
assert.equal(wrapper.marked, true, "Ô tên vợ/chồng phải được đánh dấu đã điền");

console.log("marital status spouse field: structured value fills voChongHoTen");
