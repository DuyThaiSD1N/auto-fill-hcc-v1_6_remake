const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");
const start = source.indexOf("function detectUrlScopeOk(detect, url)");
const end = source.indexOf("\nfunction setProcedureDetected", start);
assert.ok(start >= 0 && end > start, "Không tách được engine detect thủ tục");

const entryUrl = "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-8e22-77ef-819f-e49460350904";
const sandbox = { entryUrl, URL };
vm.runInNewContext(`
  const PROCEDURES = [{
    key: "chung-thuc-ban-sao",
    label: "Chứng thực bản sao từ bản chính giấy tờ, văn bản",
    detect: { urlIncludes: [entryUrl] },
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

assert.equal(sandbox.detect({
  url: entryUrl,
  bodyText: "",
  headings: [],
}), "chung-thuc-ban-sao");

assert.equal(sandbox.detect({
  url: `${entryUrl}?source=extension#detail`,
  bodyText: "",
  headings: [],
}), "chung-thuc-ban-sao");

assert.equal(sandbox.detect({
  url: "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-867a-70eb-bc54-effd523ebc99",
  bodyText: "Thủ tục đăng ký lại khai sinh có yếu tố nước ngoài",
  headings: ["Thủ tục đăng ký lại khai sinh có yếu tố nước ngoài"],
}), "");

assert.match(
  source,
  /if \(isDvcqgProcedureDetailUrl\(res\?\.signals\?\.url\)\) \{\s*await enterUnknownDvcqgProcedureMode\(\);/,
  "Nhận diện ban đầu phải xóa lựa chọn cũ khi UUID DVCQG chưa được hỗ trợ",
);
assert.match(
  source,
  /else if \(isDvcqgProcedureDetailUrl\(res\?\.signals\?\.url\)\) \{\s*await enterUnknownDvcqgProcedureMode\(\);/,
  "Chuyển SPA sang UUID DVCQG chưa hỗ trợ cũng phải xóa lựa chọn cũ",
);

console.log("popup DVCQG detail detection: exact URL only, unknown UUID stays blank");
