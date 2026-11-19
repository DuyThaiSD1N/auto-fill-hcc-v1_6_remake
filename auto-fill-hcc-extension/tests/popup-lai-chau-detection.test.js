const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");
const start = source.indexOf("function detectUrlScopeOk(detect, url)");
const end = source.indexOf("\nfunction setProcedureDetected", start);
assert.ok(start >= 0 && end > start, "Không tách được engine detect thủ tục");

const sandbox = {};
vm.runInNewContext(`
  const PROCEDURES = [{
    key: "dinh-chinh-sai-sot",
    label: "[Lai Châu] Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót",
    detect: {
      urlScope: ["dichvucong.laichau.gov.vn"],
      textIncludes: ["đính chính giấy chứng nhận đã cấp lần đầu có sai sót"],
      headingDisabled: true,
    },
  }];
  function normalizeProcedureSearch(value) {
    return String(value || "").normalize("NFD").replace(/[\\u0300-\\u036f]/g, "")
      .replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();
  }
  function normDetect(value) { return normalizeProcedureSearch(value).replace(/\\s+/g, " ").trim(); }
  function selectedProcedureConfig() { return null; }
  ${source.slice(start, end)}
  globalThis.detect = detectProcedureKeyFromSignals;
`, sandbox);

const title = "Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót";

assert.equal(sandbox.detect({
  url: "https://dichvucong.laichau.gov.vn/dich-vu-cong/ho-so?sid=abc",
  bodyText: title,
  headings: [],
}), "dinh-chinh-sai-sot");

assert.equal(sandbox.detect({
  url: "https://dichvucong.lamdong.gov.vn/dich-vu-cong/ho-so",
  bodyText: title,
  headings: [],
}), "");

assert.equal(sandbox.detect({
  url: "https://dichvucong.laichau.gov.vn/",
  bodyText: "Thành phần hồ sơ",
  headings: [],
}), "");

// Cổng Bộ Công an (detect.codeOnPage): mã TTHC in trên trang thắng, là nhận diện mạnh (đổi được khi panel còn tệp).
const strongStart = source.indexOf("function hasStrongProcedureIdentity(key, signals)");
const strongEnd = source.indexOf("\nfunction commitProcedureSearch", strongStart);
assert.ok(strongStart >= 0 && strongEnd > strongStart, "Không tách được hasStrongProcedureIdentity");
const bca = {};
vm.runInNewContext(`
  const PROCEDURES = [
    { key: "cap-ho-chieu-pho-thong-o-trong-nuoc", label: "Cấp hộ chiếu phổ thông ở trong nước (thực hiện tại cấp tỉnh)",
      detect: { urlScope: ["dichvucong.bocongan.gov.vn"], textIncludes: ["hộ chiếu phổ thông"], headingDisabled: true,
                textPriority: true, codeOnPage: true } },
    { key: "cap-doi-the-can-cuoc", label: "Cấp đổi thẻ căn cước",
      detect: { urlScope: ["dichvucong.bocongan.gov.vn"], textIncludes: ["cấp đổi thẻ căn cước"], headingDisabled: true,
                textPriority: true } },
  ];
  const CODES = { "cap-ho-chieu-pho-thong-o-trong-nuoc": "1.001456", "cap-doi-the-can-cuoc": "2.001195" };
  function procedureCode(key) { return CODES[key] || ""; }
  function normalizeProcedureSearch(value) {
    return String(value || "").normalize("NFD").replace(/[\\u0300-\\u036f]/g, "")
      .replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();
  }
  function normDetect(value) { return normalizeProcedureSearch(value).replace(/\\s+/g, " ").trim(); }
  function selectedProcedureConfig() { return null; }
  ${source.slice(start, end)}
  ${source.slice(strongStart, strongEnd)}
  globalThis.detect = detectProcedureKeyFromSignals;
  globalThis.strong = hasStrongProcedureIdentity;
`, bca);

const bcaUrl = "https://dichvucong.bocongan.gov.vn/bo-cong-an/tiep-nhan-online/nhap-thong-tin-nguoi-nop-ho-so?sid=1";
// Tên thủ tục nằm sau 6000 ký tự đầu (bodyText bị cắt) nhưng mã vẫn có trong pageProcedureCodes.
const bcaSignals = { url: bcaUrl, bodyText: "Quy trình thực hiện dịch vụ công trực tuyến", headings: [],
                     pageProcedureCodes: ["1.001456"] };
assert.equal(bca.detect(bcaSignals), "cap-ho-chieu-pho-thong-o-trong-nuoc");
assert.equal(bca.strong("cap-ho-chieu-pho-thong-o-trong-nuoc", bcaSignals), true);
// Chỉ khớp chữ (không có mã) → vẫn nhận nhưng là tín hiệu yếu như cũ.
const textOnly = { url: bcaUrl, bodyText: "1.001456 - Cấp hộ chiếu phổ thông ở trong nước", headings: [] };
assert.equal(bca.detect(textOnly), "cap-ho-chieu-pho-thong-o-trong-nuoc");
assert.equal(bca.strong("cap-ho-chieu-pho-thong-o-trong-nuoc", textOnly), false);
// Sai cổng → mã không có tác dụng; thủ tục không khai codeOnPage → mã không làm nhận diện mạnh.
assert.equal(bca.detect({ ...bcaSignals, url: "https://dichvucong.gov.vn/p/home" }), "");
assert.equal(bca.strong("cap-doi-the-can-cuoc", { ...bcaSignals, pageProcedureCodes: ["2.001195"] }), false);

console.log("popup Lai Châu detection: scoped URL + exact procedure text passed");
console.log("popup BCA detection: procedure code on page passed");
