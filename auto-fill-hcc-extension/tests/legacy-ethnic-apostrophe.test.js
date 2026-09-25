// req_1b8b17a7b4d9 — "OCR là K'Ho rõ ràng mà vẫn điền dân tộc Họ"
//
// Dropdown dân tộc của eForm hộ tịch không có option "K'Ho" (option chuẩn là "Cơ Ho"). Khi không
// khớp chính xác, pickInWidget quay sang khớp LỎNG theo ranh giới từ và thử cả chiều ngược
// (option nằm trọn trong giá trị cần điền). Dấu nháy vốn là ký tự KHÔNG phải chữ/số nên "k'ho"
// bị cắt thành hai từ "k" + "ho" → option ngắn "Họ" khớp trọn vẹn và được chọn, tô xanh như đã
// điền đúng. Fold phải xoá dấu nháy để "k'ho" thành MỘT từ "kho".
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8");
const start = source.indexOf("function foldLegacyChoice(value)");
const end = source.indexOf("async function pickInWidget(", start);
assert.ok(start >= 0 && end > start, "Không tách được nhóm hàm khớp option legacy");

const sandbox = {};
vm.runInNewContext(
  `${source.slice(start, end)}
   globalThis.fold = foldLegacyChoice;
   globalThis.hasWord = legacyChoiceHasWord;`,
  sandbox,
);
const { fold, hasWord } = sandbox;

// Khớp lỏng đúng như pickInWidget: chỉ nhận khi CHỈ MỘT option khớp.
function looseHits(options, value) {
  const foldedWant = fold(value);
  return options.filter((opt) => {
    const foldedOption = fold(opt);
    return hasWord(foldedOption, foldedWant) || hasWord(foldedWant, foldedOption);
  });
}

// Danh mục thật của dropdown (rút gọn phần liên quan) — có cả option ngắn dễ lọt.
const OPTIONS = ["Kinh", "Cơ Ho", "Co", "Hoa", "Họ", "Mông", "Mông (Hmông)", "Mnông", "Kháng"];

// --- Dấu nháy phải dính liền, không tách thành ranh giới từ ---
assert.equal(fold("K'Ho"), "kho");
assert.equal(fold("K’Ho"), "kho", "Dấu nháy cong của OCR cũng phải xoá");
assert.equal(fold("H'Mông"), "hmong");
assert.equal(fold("M'Nông"), "mnong");

// --- Không được bốc nhầm option "Họ" cho "K'Ho" ---
assert.deepEqual(looseHits(OPTIONS, "K'Ho"), [], 'Không option nào được khớp lỏng với "K\'Ho"');

// --- Giá trị backend đã chuẩn hoá thì khớp bình thường ---
assert.equal(fold("Cơ Ho"), "co ho");
assert.ok(OPTIONS.some((opt) => fold(opt) === fold("Cơ Ho")), '"Cơ Ho" phải khớp chính xác');

// --- "M'Nông" nay khớp đúng option "Mnông" thay vì trượt ---
assert.deepEqual(looseHits(OPTIONS, "M'Nông"), ["Mnông"]);

// --- Không phá các rào cũ: "Hán" vẫn không được chọn nhầm "Kháng" ---
assert.deepEqual(looseHits(OPTIONS, "Hán"), []);
// "Cơ Ho" đụng nhiều option ở nhánh lỏng ("Co", "Cơ Ho", "Họ") → pickInWidget bỏ qua khớp lỏng,
// để bước khớp CHÍNH XÁC ở trên quyết định.
assert.ok(looseHits(OPTIONS, "Cơ Ho").length > 1);

console.log("legacy ethnic apostrophe passed");
