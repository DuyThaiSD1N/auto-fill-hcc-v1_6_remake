// Thông báo lưu trú (Cổng DVC Bộ Công an): danh sách người lưu trú thêm từng người qua modal "Thêm mới người lưu trú".
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const read = (file) => fs.readFileSync(path.join(__dirname, "..", file), "utf8").replace(/^\s*\/\/.*$/gm, "");
const core = read("content/fill-core.js");
const content = read("content.js");
const sidebar = read("sidebar.js");
const FILE_STD = "content/fill-core.js";

test("vòng điền chuẩn giao comp bca-guest-list cho engine modal, không coi là ô thường", () => {
  assert.match(core, /f\.comp === "bca-guest-list"\)\s*\{\s*await fillBcaGuestList\(f, result\);\s*continue;/);
});

test("mỗi người: mở modal bằng nút Thêm mới, điền theo id, Lưu, chỉ tính thành công khi bảng có người đó", () => {
  const fn = core.slice(core.indexOf("async function fillBcaGuest("), core.indexOf("async function fillBcaGuestList("));
  assert.match(fn, /#btnAddPersonLT/);
  assert.match(fn, /btnSaveNLT/);
  assert.match(fn, /!bcaVisible\(modal\) && bcaGuestListed\(guest\)/);
  // Ngày đi qua API datepicker ở MAIN world (gõ chữ làm lịch treo).
  assert.match(fn, /bcaSetPickerDates\(dates\)/);
  assert.match(core, /action: "bcaSetDatepickers"/);
});

test("lỗi ở một người thì dừng, không mở modal chồng; người đã có trong bảng không thêm lại", () => {
  const fn = core.slice(core.indexOf("async function fillBcaGuestList("), core.indexOf("async function retryStandardAreaSelects("));
  assert.match(fn, /if \(bcaGuestListed\(guest\)\)/);
  assert.match(fn, /result\.notFound\.push[\s\S]*return;/);
});

test("người khai là người lưu trú thì tích ô của cổng, ô bị khoá không ghi đè", () => {
  assert.match(core, /chkIS_CHANGED_PERSON/);
  assert.match(core, /txtIDENTIFIER_NUMBER/);
  const fn = core.slice(core.indexOf("async function bcaFillGuestField("), core.indexOf("async function fillBcaGuest("));
  assert.match(fn, /if \(el\.disabled\) return true;/);
});

test("trang lưu trú được nhận là form standard và khối cơ quan nhận cặp id accomStay_*", () => {
  assert.match(core, /document\.getElementById\("btnAddPersonLT"\)\)\)\s*\{\s*return "standard";/);
  assert.match(content, /\["accomStay_cboPROVINCE_ID", "accomStay_cboADDRESS_ID"\]/);
  assert.match(content, /\["cboRECEIVE_ADDR_CITY_CODE", "cboRECEIVE_ADDR_VILLAGE_CODE"\]/);
});

test("sidebar khai cờ supportsBcaGuestList", () => {
  assert.match(sidebar, /supportsBcaGuestList: true/);
});

test("cơ quan thực hiện: một ô bca-agency, chọn Tỉnh rồi chờ danh sách Xã đổi mới chọn Xã, đã chọn thì giữ", () => {
  const src = fs.readFileSync(path.join(__dirname, "..", FILE_STD), "utf8");
  assert.match(src, /f\.comp === "bca-agency"\)\s*\{\s*await fillBcaAgencyField\(f, result\);\s*continue;/);
  const fn = src.slice(src.indexOf("async function fillBcaAgencyField("), src.indexOf("async function fillBcaGuestList("));
  assert.match(fn, /accomStay_cboPROVINCE_ID/);
  assert.match(fn, /accomStay_cboADDRESS_ID/);
  assert.match(fn, /if \(f\.onlyIfEmpty && picked\(city\) && picked\(ward\)\) return;/);
  assert.match(fn, /signature\(\) !== before/);
});

test("thường trú: ô cơ quan theo cặp id BE gửi + chờ readySelect; bảng dòng bca-rows bấm Thêm ở dòng cuối", () => {
  const src = fs.readFileSync(path.join(__dirname, "..", FILE_STD), "utf8");
  assert.match(src, /document\.getElementById\(f\.value\?\.cityId \|\| "accomStay_cboPROVINCE_ID"\)/);
  assert.match(src, /f\.value\?\.readySelect/);
  assert.match(src, /f\.comp === "bca-rows"\)\s*\{\s*await fillBcaRows\(f, result\);\s*continue;/);
  const fn = src.slice(src.indexOf("async function fillBcaRows("), src.indexOf("async function fillBcaGuestList("));
  assert.match(fn, /buttons\[buttons\.length - 1\]\?\.click\(\)/);
});

test("thường trú: khối cơ quan nhận cặp id _ID, cờ supportsBcaThuongTru, nút Thêm dòng cuối + ô txtNAME_FILE", () => {
  assert.match(content, /\["cboRECEIVE_ADDR_CITY_ID", "cboRECEIVE_ADDR_VILLAGE_ID"\]/);
  assert.match(sidebar, /supportsBcaThuongTru: true/);
  const attach = read("content/attach-core.js");
  assert.match(attach, /a\[title="Thêm"\], #add_gtdk/);
  assert.match(attach, /input\[id\^="txtNAME_FILE"\]/);
});
