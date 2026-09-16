// Hai tính năng port từ auto-fill-hcc-extension:
//   1. Xác nhận TTHN vùng =5 — "Thời điểm bắt đầu/kết thúc của khoảng thời gian mong muốn xác nhận
//      chưa đăng ký kết hôn với ai" (BE gửi thoiDiemBatDau/thoiDiemKetThuc).
//   2. Ô ghi tay của option "Khác" trong dropdown — dân tộc ngoài danh mục, vd "Cill"
//      (BE gửi field DanTocKhac<Ben> kèm khóa otherOf = name dropdown gốc).
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

// ---------------------------------------------------------------------------
// 1. Vùng =5: nhận diện giá trị + tìm ô ngày theo NHÃN
// ---------------------------------------------------------------------------
const sandbox = {
  norm: (s) => (s || "").normalize("NFC").trim().toLowerCase().replace(/\s+/g, " "),
};
vm.runInNewContext(`
  ${functionSource("hasDivorceDecisionAreaValue", "selectAreaTextControls")}
  ${functionSource("findLabelledDateControl", "setGenericDateControl")}
  globalThis.hasArea = hasDivorceDecisionAreaValue;
  globalThis.findByLabel = findLabelledDateControl;
`, sandbox);

assert.equal(
  sandbox.hasArea({ thoiDiemBatDau: "04/05/2019" }),
  true,
  "Chỉ có mốc bắt đầu vẫn phải vào nhánh vùng động, nếu không cả khối bị bỏ qua",
);
assert.equal(sandbox.hasArea({ thoiDiemKetThuc: "23/10/2025" }), true);
assert.equal(sandbox.hasArea({}), false, "Object rỗng không được nhận nhầm là vùng động");

// DOM giả của vùng =5: ba ô ngày nằm trong một khối bọc chung.
function dateControl(label) {
  const control = { label };
  const row = { textContent: label, children: [control] };
  const wrapper = {
    textContent:
      "Ngày cấp giấy chứng nhận kết hôn " +
      "Thời điểm bắt đầu của khoảng thời gian mong muốn xác nhận chưa đăng ký kết hôn với ai " +
      "Thời điểm kết thúc của khoảng thời gian mong muốn xác nhận chưa đăng ký kết hôn với ai",
    parentElement: null,
  };
  row.parentElement = wrapper;
  control.parentElement = row;
  return control;
}

const ngayCap = dateControl("Ngày cấp giấy chứng nhận kết hôn");
const batDau = dateControl("Thời điểm bắt đầu của khoảng thời gian mong muốn xác nhận chưa đăng ký kết hôn với ai");
const ketThuc = dateControl("Thời điểm kết thúc của khoảng thời gian mong muốn xác nhận chưa đăng ký kết hôn với ai");
const controls = [ngayCap, batDau, ketThuc];

assert.equal(
  sandbox.findByLabel(controls, "thời điểm bắt đầu"),
  batDau,
  "Mốc bắt đầu phải khớp đúng ô của nó, không rơi vào ô Ngày cấp đứng trước",
);
assert.equal(sandbox.findByLabel(controls, "thời điểm kết thúc"), ketThuc);
// Khối bọc chứa CẢ HAI nhãn: leo tới đó phải DỪNG, nếu không mọi ô đều "khớp" và hàm
// trả về ô đầu danh sách (ô Ngày cấp) — chính là lỗi lệch ô đã gặp trên cổng thật.
assert.equal(
  sandbox.findByLabel([ngayCap], "thời điểm bắt đầu"),
  null,
  "Không được khớp ở khối bọc gộp mọi nhãn",
);

// Khối điền hai mốc phải loại ô "Ngày cấp giấy chứng nhận kết hôn" (do field raw ngayCapGiayTo-*
// điền ở tầng trên nên KHÔNG nằm trong `used` của vùng này).
assert.match(
  source,
  /input\[name\^="ngayCapGiayTo"\], input\[id\^="ngayCapGiayTo"\]/,
  "Ô Ngày cấp phải bị loại khỏi danh sách suy theo vị trí (lọc cả name lẫn id)",
);
assert.match(source, /\["thời điểm bắt đầu", data\.thoiDiemBatDau\]/);
assert.match(source, /\["thời điểm kết thúc", data\.thoiDiemKetThuc\]/);

// ---------------------------------------------------------------------------
// 2. Ô ghi tay của option "Khác" (dân tộc ngoài danh mục, vd "Cill")
// ---------------------------------------------------------------------------
function makeDoc(names) {
  const nodes = names.map(([tagName, name]) => ({
    tagName,
    getAttribute: (attr) => (attr === "name" ? name : null),
  }));
  return { querySelectorAll: () => nodes };
}

function runGuess(names, field) {
  const box = { document: makeDoc(names) };
  vm.runInNewContext(`
    ${functionSource("guessOtherTextOfSelect", "fillForm")}
    globalThis.guess = guessOtherTextOfSelect;
  `, box);
  return box.guess(field);
}

const field = { name: "DanTocKhacBenNu", value: "Cill", otherOf: "DanTocBenNu" };
for (const variant of ["DanTocKhacBenNu", "DanTocBenNuKhac", "DanTocBenNu_Khac"]) {
  const hit = runGuess([["INPUT", "HoTenBenNu"], ["INPUT", variant]], field);
  assert.ok(hit, `Không tìm ra ô ghi tay "${variant}" theo dropdown gốc DanTocBenNu`);
  assert.equal(hit.getAttribute("name"), variant);
}
assert.equal(
  runGuess([["INPUT", "DanTocBenNu"], ["INPUT", "GhiChuBenNu"]], field),
  null,
  'Không có ô nào chứa "khac" thì phải trả null, tuyệt đối không ghi bừa sang ô khác',
);
assert.equal(
  runGuess([["INPUT", "DanTocKhacBenNam"]], field),
  null,
  "Ô của BÊN NAM không được nhận cho dropdown bên nữ",
);
assert.equal(runGuess([["INPUT", "DanTocKhacBenNu"]], { name: "X" }), null, "Thiếu otherOf → bỏ qua");

// Ô "Khác" render động nên lượt đầu hay hụt → pass sửa lỗi phải nhận lại field có otherOf.
assert.match(
  source,
  /eligibleNames\.has\(field\.name\) \|\| !!field\.otherOf/,
  'Ô ghi tay "Khác" của dropdown phải được thử lại dù lượt đầu chưa thấy ô nhập',
);
// eForm để ô ẩn tới khi dropdown đổi sang "Khác"; ghi lúc còn ẩn thì bị xóa trắng khi ô hiện ra.
assert.match(source, /async function fillPlainTextSelectArea\(container, f\)/);
assert.match(source, /return el && isVisible\(el\)/, "Phải chờ ô hiện rồi mới ghi");

console.log("TTHN period dates + other-ethnicity text box: OK");
