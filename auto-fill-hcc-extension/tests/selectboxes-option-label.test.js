/**
 * Nhóm selectboxes Form.io (mục "Đã được cấp Chứng chỉ hành nghề thú y", 12 phạm vi hành nghề).
 *
 * MỌI option dùng chung name "data[deNghi][]", chỉ khác value ("a", "b", …) do Form.io tự sinh và
 * nhãn hiển thị. Backend không đoán được value nên gửi kèm optionLabel; test chốt rằng
 * findStandardCheckbox chọn đúng ô theo NHÃN, kể cả khi BE gửi tên không có đuôi "[]".
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");

function slice(startMarker, endMarker) {
  const start = source.indexOf(startMarker);
  assert.ok(start >= 0, `Không tìm thấy ${startMarker}`);
  const end = source.indexOf(endMarker, start);
  assert.ok(end > start, `Không tìm thấy ${endMarker}`);
  return source.slice(start, end);
}

const helpers = [
  slice("  function standardNameVariants(names) {", "  function formioStableRadioName"),
  slice("  function foldChoiceText(value) {", "  function stripAdminPrefix"),
  slice("  // Nhãn của MỘT option trong nhóm selectboxes", "  function findStandardRadio("),
].join("\n");

// ---------------------------------------------------------------- DOM tối giản
const OPTIONS = [
  ["a", "Tiêm phòng, chữa bệnh, tiểu phẫu (thiến, cắt đuôi) động vật, tư vấn các hoạt động liên quan đến lĩnh vực thú y."],
  ["b", "Khám bệnh, chẩn đoán bệnh, phẫu thuật động vật, xét nghiệm bệnh động vật."],
  ["c", "Buôn bán thuốc thú y dùng trong thú y cho động vật trên cạn."],
  ["d", "Buôn bán thuốc thú y dùng trong thú y cho động vật thủy sản."],
];

function buildForm() {
  return OPTIONS.map(([value, label]) => {
    const input = {
      nodeType: 1,
      tagName: "INPUT",
      type: "checkbox",
      value,
      checked: false,
      getAttribute: (name) => (name === "name" ? "data[deNghi][]" : null),
    };
    const labelNode = { nodeType: 1, tagName: "LABEL", textContent: `  ${label}  ` };
    input.closest = (selector) => (selector === "label" ? labelNode : null);
    input.parentElement = labelNode;
    return input;
  });
}

const inputs = buildForm();
const context = {
  CSS: { escape: (value) => value },
  document: {
    querySelectorAll: (selector) =>
      selector === 'input[type="checkbox"][name="data[deNghi][]"]' ||
      selector === 'input[type="checkbox"][name]'
        ? inputs
        : [],
    querySelector: () => null,
  },
  FIELD_NAME_ALIASES: {},
};
vm.createContext(context);
vm.runInContext(
  `const norm = (s) => (s || "").trim().toLowerCase().replace(/\\s+/g, " ");\n` +
    `const nodeText = (el) => String((el && el.textContent) || "").replace(/\\s+/g, " ").trim();\n` +
    `${helpers}\n` +
    "globalThis.findStandardCheckbox = findStandardCheckbox;",
  context
);

const { findStandardCheckbox } = context;

// BE gửi "data[deNghi][]" + nhãn đầy đủ → đúng ô thứ ba, không phải ô đầu danh sách.
const onLand = findStandardCheckbox(["data[deNghi][]"], null, "Buôn bán thuốc thú y dùng trong thú y cho động vật trên cạn.");
assert.equal(onLand && onLand.value, "c", "Phải tick đúng option 'trên cạn'");

// Hai option chỉ khác đuôi "trên cạn" / "thủy sản" — không được lẫn sang nhau.
const aquatic = findStandardCheckbox(["data[deNghi][]"], null, "Buôn bán thuốc thú y dùng trong thú y cho động vật thủy sản.");
assert.equal(aquatic && aquatic.value, "d", "Phải tick đúng option 'thủy sản'");

// Nhãn thiếu dấu chấm cuối (đơn giấy hay ghi vậy) vẫn khớp.
const noDot = findStandardCheckbox(["data[deNghi][]"], null, "Khám bệnh, chẩn đoán bệnh, phẫu thuật động vật, xét nghiệm bệnh động vật");
assert.equal(noDot && noDot.value, "b", "Bỏ dấu chấm cuối vẫn phải khớp");

// BE gửi tên không có đuôi "[]" → standardNameVariants phải tự thử dạng mảng của Form.io.
const viaPlainName = findStandardCheckbox(["data[deNghi]"], null, "Buôn bán thuốc thú y dùng trong thú y cho động vật trên cạn.");
assert.equal(viaPlainName && viaPlainName.value, "c", "Tên không có [] vẫn phải tìm ra ô");

// Nhãn không có trên form → không tick bừa ô nào.
assert.equal(
  findStandardCheckbox(["data[deNghi][]"], null, "Nuôi trồng thủy sản trong lồng bè."),
  null,
  "Nhãn lạ thì phải trả null"
);

console.log("selectboxes-option-label: OK");
