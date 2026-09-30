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
