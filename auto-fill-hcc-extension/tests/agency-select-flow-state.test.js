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

// Thủ tục BCA không có trang DVCQG (1.013066 đăng ký xe nhập khẩu…): link mở thẳng tthc?matt=58712, URL không
// mang MaTTHC → chặng "bca" đọc mã ở mục "Mã thủ tục" trên trang để chỉ bấm "Nộp hồ sơ" đúng thủ tục.
const bcaStart = source.indexOf("function bcaPageCode(");
const bcaEnd = source.indexOf("\n\n  async function bcaStage(", bcaStart);
assert.ok(bcaStart >= 0 && bcaEnd > bcaStart, "Không tách được bcaPageCode");
const tthcItem = (title, detail) => ({
  querySelector: (sel) => (sel === ".item-title" ? { textContent: title }
    : sel === ".tthc-list-item-detail" ? { textContent: detail } : null),
});
let tthcItems = [];
const bcaBox = {
  URLSearchParams,
  location: { search: "?matt=58712" },
  document: { querySelectorAll: (sel) => (sel === ".tthc-list-item" ? tthcItems : []) },
};
vm.runInNewContext(`
  ${source.slice(foldStart, foldEnd)}
  ${source.slice(bcaStart, bcaEnd)}
  globalThis.bcaPageCode = bcaPageCode;
`, bcaBox);
assert.equal(bcaBox.bcaPageCode(), "", "trang chưa dựng mục Mã thủ tục -> chưa có mã, giữ cờ");
tthcItems = [tthcItem("Mã thủ tục", "\n   1.013066    "), tthcItem("Lĩnh vực", "Đăng ký, quản lý phương tiện")];
assert.equal(bcaBox.bcaPageCode(), "1.013066");
tthcItems = [tthcItem("Lĩnh vực", "1.999999"), tthcItem("Mã thủ tục", "2.000311")];
assert.equal(bcaBox.bcaPageCode(), "2.000311", "chỉ lấy đúng mục Mã thủ tục");
bcaBox.location = { search: "?matt=40852&MaTTHC=2.001428" };
assert.equal(bcaBox.bcaPageCode(), "2.001428", "đi vòng từ DVCQG: mã trên URL vẫn được ưu tiên");
assert.match(source, /const code = await waitFor\(bcaPageCode, \d+, \d+\) \|\| "";/,
  "bcaStage phải chờ trang dựng mục Mã thủ tục (script chạy ở document_start)");

// Popup: link bcaSubmit trỏ thẳng cổng Bộ Công an -> lên đạn luôn chặng "bca"; để trống stage thì agency-select.js
// bên dichvucong.gov.vn bấm nhầm "Nộp hồ sơ" của trang DVCQG mở kế tiếp.
const popup = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");
const opensStart = popup.indexOf("function opensOnBcaPortal(");
const opensEnd = popup.indexOf("\n}\n", opensStart) + 2;
assert.ok(opensStart >= 0 && opensEnd > opensStart, "Không tách được opensOnBcaPortal");
const popupBox = { URL };
vm.runInNewContext(`${popup.slice(opensStart, opensEnd)}\nglobalThis.opensOnBcaPortal = opensOnBcaPortal;`, popupBox);
assert.equal(popupBox.opensOnBcaPortal({ url: "https://dichvucong.bocongan.gov.vn/bocongan/bothutuc/tthc?matt=58712" }), true);
assert.equal(popupBox.opensOnBcaPortal({ url: "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bf7-adfd-753a-8621-335a5395a571" }), false);
assert.equal(popupBox.opensOnBcaPortal({ url: "" }), false);
assert.match(popup, /\.\.\.\(link\.bcaSubmit && opensOnBcaPortal\(link\) \? \{ stage: "bca" \} : \{\}\),/,
  "openKeKhaiPage phải lên đạn chặng bca cho link trỏ thẳng cổng Bộ Công an");

console.log("agency select flow state: DVCQG detail route is not portal home");
