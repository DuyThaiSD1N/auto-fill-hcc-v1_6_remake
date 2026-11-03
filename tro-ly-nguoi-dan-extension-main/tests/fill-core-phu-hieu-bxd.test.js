// Cổng Bộ XD, cấp phù hiệu: BE phát nút dom-click ("Thêm phương tiện" / "Thêm"), ô Choices tìm từ xa
// (searchOnce) và Tỉnh/Xã của đơn vị KDVT. Engine handfree trước không có các nhánh này → 18 ô "chưa khớp".
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const src = fs.readFileSync(path.join(__dirname, "..", "content", "fill-core.js"), "utf8");

function fnSource(name) {
  const start = src.search(new RegExp(`(async )?function ${name}\\(`));
  assert.ok(start >= 0, `thiếu hàm ${name}`);
  const end = src.indexOf("\n}\n", start);
  return src.slice(start, end + 2);
}

test("Tỉnh/Phường-xã của đơn vị KDVT là ô địa chỉ (điền sau, chờ cascade)", () => {
  const ctx = {};
  vm.runInNewContext(`${fnSource("isAreaSelectName")}; this.f = isAreaSelectName;`, ctx);
  assert.equal(ctx.f("data[T_DonViKinhDoanh][DiaChiHoatDong][TinhThanh]"), true);
  assert.equal(ctx.f("data[T_DonViKinhDoanh][DiaChiHoatDong][XaPhuong]"), true);
  // Ô "Tại" của giấy đề nghị KHÔNG phải ô địa chỉ (BE gắn searchOnce).
  assert.equal(ctx.f("data[TinhThanh]"), false);
});

test("vòng điền có nhánh dom-click và searchOnce", () => {
  const body = fnSource("fillFormStandard");
  assert.match(body, /f\.comp === "dom-click"\) \{\s*ok = await clickStandardButton\(f, candidates\);/);
  assert.match(body, /else if \(f\.searchOnce\) \{[\s\S]{0,260}?fillChoicesSearchOnce\(el, f\.value\)/);
  // Xe đã có trong danh sách (điền lại) → bỏ nút + ô panel, không thêm trùng.
  assert.match(body, /standardListHasText\(f\.skipIfListed\)/);
  assert.match(body, /if \(inListedPanel\(f\)\) \{/);
});

test("điền lại ô trống KHÔNG đổ lại panel đã bấm Thêm", () => {
  const body = fnSource("reapplyEmptyStandardTextFields");
  assert.match(body, /f\.comp === "dom-click" && !f\.waitName/);
  assert.match(body, /!committed\.some\(/);
});

test("khối cha panel: theo ô chờ, hoặc theo chính tên nút Thêm", () => {
  const ctx = {};
  vm.runInNewContext(`${fnSource("standardClickPanelPrefix")}; this.f = standardClickPanelPrefix;`, ctx);
  const pt = "data[ThamDinh][ThemPhuongTienRaw]";
  assert.equal(ctx.f({ name: "data[ThamDinh][themPhuongTien]", waitName: `${pt}[BienDangKy]` }), pt);
  assert.equal(ctx.f({ name: `${pt}[add]` }), pt);
});
