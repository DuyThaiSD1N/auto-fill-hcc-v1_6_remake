// Chọn cơ quan CẤP XÃ trong hộp thoại cổng bộ (form#ngSelectAgencyForm1).
// Thủ tục "Hưởng trợ cấp khi người có công đang hưởng trợ cấp ưu đãi từ trần" (Bộ Nội vụ) giải
// quyết ở cấp xã: radio "Phường/Xã" (value "0") + chọn xã, KHÔNG gạt "Sở/Ban ngành".
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const mae = strip(read("content/portal-mae.js"));
const sidebar = strip(read("sidebar.js"));

test("engine nhận agencyLevel + ward từ BE", () => {
  assert.match(mae, /agencyLevel/, "thiếu tham số agencyLevel");
  assert.match(mae, /ward:\s*msg\.ward\s*\|\|\s*""/, "listener không chuyển ward xuống engine");
  assert.match(mae, /agencyLevel:\s*msg\.agencyLevel\s*\|\|\s*""/);
});

test("nhánh cấp xã gạt radio value 0 rồi chọn xã", () => {
  const branch = mae.slice(mae.indexOf('agencyLevel === "ward"'), mae.indexOf("Radio \"Sở/Ban ngành\""));
  assert.ok(branch.length > 100, "không tìm thấy nhánh cấp xã");
  assert.match(branch, /clickLevelRadio\("0"\)/, 'cấp xã phải gạt radio value "0"');
  assert.match(branch, /matSelect\("agency"\)/, "xã nằm ở ô formcontrolname agency");
  assert.match(branch, /findAgreeButton/, "phải bấm Đồng ý và tiếp tục");
  assert.ok(!/procedureProcess/.test(branch), "hộp thoại cấp xã không có Trường hợp giải quyết");
});

test("nhánh Sở cũ giữ nguyên radio value 1", () => {
  assert.match(mae, /clickLevelRadio\("1"\)/, "nhánh Sở phải gạt radio value 1");
});

test("cấp xã thiếu tên xã thì báo lỗi, không bấm bừa", () => {
  assert.match(mae, /Tài khoản chưa gắn phường\/xã/);
});

test("sidebar khai cờ và chuyển tiếp ward/agencyLevel", () => {
  assert.match(sidebar, /supportsMaeWardAgency:\s*true/, "thiếu capability");
  const block = sidebar.slice(sidebar.indexOf('action: "fillMaeAgency"'));
  assert.match(block.slice(0, 500), /ward:\s*a\.ward\s*\|\|\s*""/);
  assert.match(block.slice(0, 500), /agencyLevel:\s*a\.agencyLevel\s*\|\|\s*""/);
});
