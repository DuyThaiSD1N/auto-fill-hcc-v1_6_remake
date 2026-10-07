// Đăng ký lại khai sinh (eForm cũ): đổi "Quan hệ với người được khai sinh" làm eForm chép người yêu cầu
// sang khối con/cha/mẹ và xóa các khối kia. Ô tool đã điền hoặc người dùng đã sửa phải được giữ nguyên.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const src = fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8");
const block = src.slice(src.indexOf("// ---- Đăng ký lại khai sinh: giữ dữ liệu"), src.indexOf("async function fillForm(fields) {"));

test("chỉ cài cho mẫu đăng ký lại khai sinh", () => {
  assert.match(block, /x-radio\[name="QuanHe"\]'\) && !!document\.querySelector\('\[name="soDKTruocDay"\]'\)/);
  assert.match(block, /if \(!isBirthReRegistrationForm\(\)\) return;/);
});

test("giữ ô tool đã điền và ô người dùng sửa; ô chưa ai điền để eForm xử lý", () => {
  assert.match(block, /if \(!filledNames\.has\(field\.name\)\) continue;[\s\S]{0,160}protectedNames\.add\(found\.usedName\)/);
  assert.match(block, /if \(!event\.isTrusted \|\| relationKeeper\.restoring\) return;[\s\S]{0,200}protectedNames\.add\(name\)/);
  assert.match(block, /!relationKeeper\.protectedNames\.has\(name\)\) continue;/);
});

test("chụp TRƯỚC khi eForm xử lý (capture pointerdown/phím), chỉ thao tác thật trên QuanHe", () => {
  assert.match(block, /document\.addEventListener\("pointerdown", onRelation, true\);/);
  assert.match(block, /document\.addEventListener\("keydown", onRelation, true\);/);
  assert.match(block, /closest\?\.\('x-radio\[name="QuanHe"\]'\)/);
});

test("ghi lại cả ô bị xóa lẫn ô bị chép đè, radio/dropdown trước", () => {
  assert.match(block, /if \(!el \|\| keeperSame\(readLegacyComponent\(el\), field\.value\)\) continue;/);
  assert.match(block, /\.\.\.snap\.filter\(\(f\) => RELATION_KEEPER_DRIVERS\.has\(f\.comp\)\),\s*\.\.\.snap\.filter\(\(f\) => !RELATION_KEEPER_DRIVERS\.has\(f\.comp\)\)/);
});

test("cài sau mỗi lượt điền", () => {
  assert.match(src, /armLegacyRelationKeeper\(fields, filledNames\);/);
});
