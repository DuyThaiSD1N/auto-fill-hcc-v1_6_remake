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

// Trang thông tin DVCQG in tên thủ tục khác ở cột "Tìm kiếm nhiều nhất" → không được khớp theo chữ/heading.
const solarName = "Thông báo phát triển nguồn điện mặt trời mái nhà tự sản xuất, tự tiêu thụ đấu nối với hệ thống điện quốc gia tại cấp điện áp hạ áp";
const linkedUrl = "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-3fac-7489-b53b-a15eb239a6fe";
const textSandbox = { URL, linkedUrl };
vm.runInNewContext(`
  const PROCEDURES = [{
    key: "thong-bao-dien-mat-troi",
    label: ${JSON.stringify(solarName)},
    detect: {
      textIncludes: ["Thông báo phát triển nguồn điện mặt trời mái nhà tự sản xuất", "cấp điện áp hạ áp"],
      headingDisabled: true,
      textPriority: true,
    },
  }, {
    key: "ket-hon",
    label: "Thủ tục đăng ký kết hôn",
    detect: { textIncludes: ["đăng ký kết hôn"] },
  }];
  function keKhaiLinks() { return [{ key: "ket-hon", url: linkedUrl }]; }
  function normalizeProcedureSearch(value) {
    return String(value || "").normalize("NFD").replace(/[\\u0300-\\u036f]/g, "")
      .replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();
  }
  function normDetect(value) { return normalizeProcedureSearch(value).replace(/\\s+/g, " ").trim(); }
  function selectedProcedureConfig() { return null; }
  ${source.slice(start, end)}
  globalThis.detect = detectProcedureKeyFromSignals;
`, textSandbox);

const sidebarBody = `Công nhận đăng kiểm viên tàu biển Tìm kiếm nhiều nhất ${solarName} Bộ Công thương`;
for (const url of [
  "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-0000-7000-8000-000000000001",
  "https://dichvucong.gov.vn/",
  "https://dichvucong.gov.vn/danh-sach-thu-tuc?q=dien",
]) {
  assert.equal(textSandbox.detect({ url, bodyText: sidebarBody, headings: [solarName] }), "", url);
}
assert.equal(
  textSandbox.detect({ url: `${linkedUrl}/`, bodyText: sidebarBody, headings: [] }),
  "ket-hon",
  "Trang chi tiết khớp đúng UUID link Đi đến thủ tục thì nhận thủ tục đó",
);
assert.equal(
  textSandbox.detect({ url: "https://dichvucong.gov.vn/nop-ho-so?formalityId=1", bodyText: solarName, headings: [] }),
  "thong-bao-dien-mat-troi",
  "Biểu mẫu /nop-ho-so vẫn nhận diện theo chữ như cũ",
);
assert.equal(
  textSandbox.detect({ url: "https://motcua-tthc.moit.gov.vn/form", bodyText: solarName, headings: [] }),
  "thong-bao-dien-mat-troi",
  "Cổng khác không bị ảnh hưởng",
);

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
