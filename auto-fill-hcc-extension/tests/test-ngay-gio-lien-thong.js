/**
 * Ô "ngaysinh" của cổng liên thông (khai sinh/khai tử) có mat-select ĐỊNH DẠNG rồi mới tới ô ngày:
 * Ngày/Tháng/Năm · Ngày/Tháng/Năm giờ:phút · Tháng/Năm · Năm.
 * Backend gửi chuỗi, engine phải đọc ra đúng định dạng — sai định dạng là cổng báo "Trường không
 * được để trống" dù đã gõ (mẫu BA dòng 31: "18 giờ 15 phút, ngày 01/08/2026").
 */
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

// fill-angular.js là IIFE gắn hàm vào window.__HCC__; nạp với window giả, chỉ cần hàm thuần.
// new Function ở đây chạy CHÍNH file nguồn trong repo (không có dữ liệu ngoài ghép vào), là cách
// duy nhất nạp được IIFE này khi không có DOM.
function napEngine() {
  const src = fs.readFileSync(path.join(__dirname, "..", "content", "fill-angular.js"), "utf8");
  const window = { __HCC__: {} };
  new Function("window", "document", src)(window, { querySelectorAll: () => [] });
  return window.__HCC__;
}

const { phanTichNgayGio } = napEngine();

test("đủ ngày giờ phút → chọn định dạng có giờ:phút, tách sẵn giờ và phút", () => {
  assert.deepStrictEqual(phanTichNgayGio("01/08/2026 18:15"), {
    dinhDang: "Ngày/Tháng/Năm giờ:phút", ngay: "01/08/2026", gio: "18", phut: "15",
  });
});

test("chỉ có ngày → định dạng Ngày/Tháng/Năm, không đụng ô giờ", () => {
  assert.deepStrictEqual(phanTichNgayGio("07/03/2019"), {
    dinhDang: "Ngày/Tháng/Năm", ngay: "07/03/2019",
  });
});

test("giấy tờ chỉ ghi tháng/năm hoặc năm vẫn điền được nhờ đổi định dạng", () => {
  assert.deepStrictEqual(phanTichNgayGio("8/2026"), { dinhDang: "Tháng/Năm", ngay: "08/2026" });
  assert.deepStrictEqual(phanTichNgayGio("1950"), { dinhDang: "Năm", ngay: "1950" });
});

test("thêm số 0 cho ngày, tháng, giờ, phút viết tắt", () => {
  assert.deepStrictEqual(phanTichNgayGio("1/8/2026 8:5"), {
    dinhDang: "Ngày/Tháng/Năm giờ:phút", ngay: "01/08/2026", gio: "08", phut: "05",
  });
});

test("dạng lạ thì trả null để engine giữ nếp cũ, không đoán định dạng", () => {
  for (const xau of ["", null, undefined, "hôm qua", "2026-08-01", "01/08/26"]) {
    assert.strictEqual(phanTichNgayGio(xau), null, `phải trả null với ${JSON.stringify(xau)}`);
  }
});
