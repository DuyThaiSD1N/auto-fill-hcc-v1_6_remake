const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");
const start = source.indexOf("function detectUrlScopeOk(detect, url)");
const end = source.indexOf("\nfunction setProcedureDetected", start);
assert.ok(start >= 0 && end > start, "Không tách được engine detect thủ tục");
const functionSource = source.slice(start, end);

const sandbox = { selectedKey: "" };
vm.runInNewContext(`
  const PROCEDURES = [
    {key:"dang-ky-kinh-doanh", label:"Đăng ký thành lập hộ kinh doanh", detect:{urlIncludes:["hokinhdoanh.dkkd.gov.vn"], headingDisabled:true}},
    {key:"dang-ky-thay-doi-noi-dung-ho-kinh-doanh", label:"Đăng ký thay đổi nội dung đăng ký hộ kinh doanh", businessWorkflow:"change", detect:{headingDisabled:true}},
    {key:"cham-dut-hoat-dong-ho-kinh-doanh", label:"Chấm dứt hoạt động hộ kinh doanh", businessWorkflow:"dissolution", detect:{headingDisabled:true}},
    {key:"cap-lai-cap-doi-gcn-ho-kinh-doanh", label:"Cấp lại, cấp đổi GCN hộ kinh doanh", businessWorkflow:"reissue", detect:{headingDisabled:true}},
  ];
  function normalizeProcedureSearch(value) {
    return String(value || "").normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").replace(/đ/g, "d").toLowerCase();
  }
  function normDetect(value) { return normalizeProcedureSearch(value).replace(/\\s+/g, " ").trim(); }
  function selectedProcedureConfig() { return PROCEDURES.find((item) => item.key === selectedKey) || null; }
  ${functionSource}
  globalThis.detect = detectProcedureKeyFromSignals;
`, sandbox);

const hkd = "https://hokinhdoanh.dkkd.gov.vn/Registration.aspx";
const detect = (hint) => sandbox.detect({ url: hkd, bodyText: "", headings: [], businessProcedureHint: hint });

sandbox.selectedKey = "";
assert.equal(detect("choice"), "");

sandbox.selectedKey = "dang-ky-thay-doi-noi-dung-ho-kinh-doanh";
assert.equal(detect("choice"), "");

sandbox.selectedKey = "dang-ky-kinh-doanh";
assert.equal(detect("choice"), "");

sandbox.selectedKey = "dang-ky-kinh-doanh";
assert.equal(detect("change"), "dang-ky-thay-doi-noi-dung-ho-kinh-doanh");

sandbox.selectedKey = "cham-dut-hoat-dong-ho-kinh-doanh";
assert.equal(detect("change"), "cham-dut-hoat-dong-ho-kinh-doanh");

sandbox.selectedKey = "dang-ky-thay-doi-noi-dung-ho-kinh-doanh";
assert.equal(detect("dissolution"), "cham-dut-hoat-dong-ho-kinh-doanh");

sandbox.selectedKey = "dang-ky-thay-doi-noi-dung-ho-kinh-doanh";
assert.equal(detect("reissue"), "cap-lai-cap-doi-gcn-ho-kinh-doanh");

sandbox.selectedKey = "cap-lai-cap-doi-gcn-ho-kinh-doanh";
assert.equal(detect("change"), "cap-lai-cap-doi-gcn-ho-kinh-doanh");
assert.equal(detect("shared-business-search"), "cap-lai-cap-doi-gcn-ho-kinh-doanh");
assert.equal(detect("change-exact"), "dang-ky-thay-doi-noi-dung-ho-kinh-doanh");

sandbox.selectedKey = "";
assert.equal(detect("shared-business-search"), "");

sandbox.selectedKey = "dang-ky-thay-doi-noi-dung-ho-kinh-doanh";
assert.equal(detect("create"), "dang-ky-kinh-doanh");
assert.equal(detect(""), "dang-ky-thay-doi-noi-dung-ho-kinh-doanh");

sandbox.selectedKey = "";
assert.equal(detect(""), "dang-ky-kinh-doanh");

assert.match(source, /async function enterBusinessProcedureChoiceMode\(\)/);
assert.match(source, /businessProcedureHint === "choice"[\s\S]*?enterBusinessProcedureChoiceMode\(\)/);
assert.ok(
  (source.match(/await enterBusinessProcedureChoiceMode\(\)/g) || []).length >= 2,
  "Cả nhận diện ban đầu và nhận diện khi chuyển trang phải vào chế độ chọn thủ tục chung",
);
assert.ok(
  (source.match(/autoDetectProcedure\(\{ clearChoiceSelection: false \}\)/g) || []).length >= 3,
  "Các nút xử lý phải giữ thủ tục người dùng vừa chọn tay trên màn HKD dùng chung",
);
assert.match(source, /res\.businessFlow\?\.search \|\| res\.extracted\?\.businessSearch/);
assert.match(source, /businessSearch,/);
assert.match(
  source,
  /const res = await api\.process\(\{ procedure: cfg\.key, options, files: payloadFiles \}\);[\s\S]*?businessFillSupportCode = String\(res\.requestId \|\| res\.sessionId \|\| ""\)\.trim\(\);[\s\S]*?showSupportCode\(businessFillSupportCode\);[\s\S]*?await saveSession\(\);/,
  "Nút fill-all HKD phải hiện và lưu requestId của lượt fill trước khi state machine postback",
);
assert.match(
  source,
  /businessFillSupportCode,\s*\n\s*files:/,
  "Mã fill HKD phải sống cùng session theo tab qua các lần WebForms postback",
);
assert.ok(
  (source.match(/restoreBusinessFillSupportCode\(\);/g) || []).length >= 2,
  "Mở lại panel hoặc đăng nhập lại phải khôi phục mã fill HKD từ session theo tab",
);
assert.doesNotMatch(
  source,
  /businessFillSupportCode\s*=\s*String\(planRes\.requestId/,
  "requestId của attachment plan không được ghi đè mã hỗ trợ của fill HKD",
);

console.log("popup business detection: choice/change/create precedence passed");
