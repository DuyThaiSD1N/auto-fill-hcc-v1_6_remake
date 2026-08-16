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

console.log("popup Lai Châu detection: scoped URL + exact procedure text passed");
