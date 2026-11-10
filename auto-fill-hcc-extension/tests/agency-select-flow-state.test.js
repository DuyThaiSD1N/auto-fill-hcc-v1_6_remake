const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "..", "content", "agency-select.js"),
  "utf8",
);
const start = source.indexOf("function isProcedureDetailPage(");
const end = source.indexOf("\n\n  function flowState()", start);
assert.ok(start >= 0 && end > start, "Không tách được bộ nhận diện trang chi tiết DVCQG");

const sandbox = { URL };
vm.runInNewContext(`
  ${source.slice(start, end)}
  globalThis.isProcedureDetailPage = isProcedureDetailPage;
`, sandbox);

const detailUrl = "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-8e22-77ef-819f-e49460350904";
assert.equal(sandbox.isProcedureDetailPage(detailUrl), true);
assert.equal(sandbox.isProcedureDetailPage(`${detailUrl}?source=extension#detail`), true);
assert.equal(sandbox.isProcedureDetailPage("https://dichvucong.gov.vn/thu-tuc-hanh-chinh"), false);
assert.equal(sandbox.isProcedureDetailPage("https://dichvucong.gov.vn/danh-sach-thu-tuc"), false);
assert.equal(sandbox.isProcedureDetailPage("https://example.com/thu-tuc-hanh-chinh/uuid"), false);

assert.match(
  source,
  /const onProcedurePage = isProcedureDetailPage\(\) \|\| !!findAgencyCard\(\);/,
  "flowState phải coi route chi tiết là trang thủ tục ngay cả khi DOM chưa render thẻ cơ quan",
);

// Ô Phường/Xã ra hai dòng cùng tên, cổng lỗi: Bắc Nha Trang (Khánh Hòa) bấm dòng trên rồi dòng dưới,
// xã khác vẫn dòng đầu.
const foldStart = source.indexOf("function fold(");
const foldEnd = source.indexOf("function areaLabel(", foldStart);
const wardStart = source.indexOf("const WARD_PICKS");
const wardEnd = source.indexOf("/** Gõ vào ô tìm kiếm", wardStart);
assert.ok(foldStart >= 0 && foldEnd > foldStart && wardStart >= 0 && wardEnd > wardStart,
  "Không tách được bảng dòng trùng tên + matchOption");
const wardBox = {};
vm.runInNewContext(`
  ${source.slice(foldStart, foldEnd)}
  ${source.slice(wardStart, wardEnd)}
  globalThis.wardPicks = wardPicks;
  globalThis.matchOption = matchOption;
`, wardBox);
// Mảng tạo trong vm khác realm → so qua JSON.
const picksOf = (p, w) => JSON.stringify(wardBox.wardPicks(p, w));
assert.equal(picksOf("Tỉnh Khánh Hòa", "Phường Bắc Nha Trang"), "[1,2]", "cổng lỗi: dòng trên trước, dòng dưới sau");
assert.equal(picksOf("Khánh Hòa", "Bắc Nha Trang"), "[1,2]");
assert.equal(picksOf("Tỉnh Khánh Hòa", "Phường Nha Trang"), "[1]");
assert.equal(picksOf("Tỉnh Bắc Ninh", "Phường Bắc Nha Trang"), "[1]");
const opt = (text) => ({ textContent: text });
const tren = opt("Phường Bắc Nha Trang");
const duoi = opt("Phường Bắc Nha Trang");
const wardList = [tren, duoi, opt("Phường Nha Trang"), opt("Phường Tây Nha Trang")];
assert.equal(wardBox.matchOption(wardList, "Phường Bắc Nha Trang", 1), tren);
assert.equal(wardBox.matchOption(wardList, "Phường Bắc Nha Trang", 2), duoi);
assert.equal(wardBox.matchOption(wardList, "Bắc Nha Trang", 2), duoi, "tên trần vẫn ra dòng dưới");
assert.equal(wardBox.matchOption(wardList, "Phường Bắc Nha Trang"), tren, "không khai thì giữ dòng đầu như cũ");
const mot = opt("Phường Bắc Nha Trang");
assert.equal(wardBox.matchOption([mot, opt("Phường Nha Trang")], "Phường Bắc Nha Trang", 2), mot,
  "cổng gộp còn một dòng thì lấy dòng đó");
assert.match(source, /const picks = wardPicks\(arm\.province, arm\.ward\);\s*for \(const occurrence of picks\) \{\s*if \(!await pickCombo\(card, 1, arm\.ward, "Phường\/Xã", occurrence, picks\.length > 1\)\)/,
  "xã cổng lỗi phải bấm lần lượt từng dòng trong WARD_PICKS");
assert.match(source, /if \(done\(\) && !force\)/,
  "bấm lần lượt: chữ trên ô đúng chưa chắc đúng dòng, phải mở danh sách bấm lại");

console.log("agency select flow state: DVCQG detail route is not portal home");
