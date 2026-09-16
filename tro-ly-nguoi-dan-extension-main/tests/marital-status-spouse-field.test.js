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
// fillDivorceDecisionAreaByKnownNames trả {any, used, numberHandled, dateHandled, agencyHandled}
// — `any` mới là cờ "đã điền được gì chưa"; các khóa còn lại để tầng nhãn/vị trí biết ô nào
// đã xong mà không điền đè.
assert.equal(sandbox.fillStructuredValue(container, value).any, true);
assert.equal(spouseInput.value, "VŨ HỮU NINH");
assert.equal(spouseInput.options.typing, true);
assert.equal(spouseInput.options.commit, true);
assert.equal(wrapper.marked, true, "Ô tên vợ/chồng phải được đánh dấu đã điền");

console.log("marital status spouse field: structured value fills voChongHoTen");
