// Field `clear` (BE xoá giá trị cổng đổ sẵn) là ô TRỐNG: không được giữ viền xanh "đã điền";
// `markEmpty` thì tô đỏ để cán bộ nhập tay.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const src = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");

test("vòng điền standard gọi markStandardCleared cho field clear", () => {
  assert.match(src, /if \(ok && f\.clear\) markStandardCleared\(f, candidates, occurrence, root\);/);
});

test("markStandardCleared bỏ viền xanh và chỉ tô đỏ khi markEmpty", () => {
  const body = src.slice(src.indexOf("function markStandardCleared"), src.indexOf("function isStandardEmptyControl"));
  assert.match(body, /classList\.remove\("autofill-filled"\)/);
  assert.match(body, /if \(f\.markEmpty\) target\.classList\.add\("autofill-not-filled"\)/);
});

test("vòng điền lại ô text trống bỏ qua field clear (không tô xanh đè màu đỏ)", () => {
  const body = src.slice(src.indexOf("async function reapplyEmptyStandardTextFields"), src.indexOf("async function reapplyOwnerDossierCopy"));
  assert.match(body, /!f\.clear\)/);
});

test("field enableInput: bỏ disabled của component trước khi ghi (ô khoá VNeID, chế độ tờ khai)", () => {
  assert.match(src, /if \(f\.enableInput\) enableStandardFieldInputs\(f, candidates, occurrence, root\);/);
  const body = src.slice(src.indexOf("function enableStandardFieldInputs"), src.indexOf("function markStandardCleared"));
  assert.match(body, /closest\?\.\("\.formio-component"\)/);
  assert.match(body, /node\.removeAttribute\("disabled"\)/);
});

test("Bắc Ninh: ô chữ ghi Thành phố Bắc Ninh, ô chọn giữ Tỉnh Bắc Ninh để khớp option cổng", () => {
  const start = src.indexOf("  const TEXT_FIELD_COMP");
  const body = src.slice(start, src.indexOf("  function handleAutofillMessage"));
  const doiTen = new Function(`${body}; return tenTinhBacNinhTrongOChu;`)();
  const [diaChi, tinhChon, congAn, diaChiCu, chuThuong, tinhKhac] = doiTen([
    { comp: "dom-input", value: "Số 12, Phường Kinh Bắc, Tỉnh Bắc Ninh" },
    { comp: "dom-select", value: "Tỉnh Bắc Ninh" },
    { comp: "bn-input", value: "Công an tỉnh Bắc Ninh" },
    { comp: "x-input", value: "Phường Vũ Ninh, Thành phố Bắc Ninh, Tỉnh Bắc Ninh" },
    { comp: "bn-textarea", value: "thôn Đông, xã Tiên Du, tỉnh Bắc Ninh." },
    { comp: "liz-input", value: "Phường Hà Đông, Thành phố Hà Nội" },
  ]);
  assert.strictEqual(diaChi.value, "Số 12, Phường Kinh Bắc, Thành phố Bắc Ninh");
  assert.strictEqual(tinhChon.value, "Tỉnh Bắc Ninh");
  assert.strictEqual(congAn.value, "Công an tỉnh Bắc Ninh");
  assert.strictEqual(diaChiCu.value, "Phường Vũ Ninh, Thành phố Bắc Ninh, Tỉnh Bắc Ninh");
  assert.strictEqual(chuThuong.value, "thôn Đông, xã Tiên Du, thành phố Bắc Ninh.");
  assert.strictEqual(tinhKhac.value, "Phường Hà Đông, Thành phố Hà Nội");
  // Cả hai lối điền (tờ khai + người được ủy quyền Bắc Ninh) đều đi qua bước đổi tên.
  assert.strictEqual((src.match(/tenTinhBacNinhTrongOChu\(Array\.isArray\(msg\.fields\)/g) || []).length, 2);
});
