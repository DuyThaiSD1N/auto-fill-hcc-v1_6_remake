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

console.log("agency select flow state: DVCQG detail route is not portal home");
