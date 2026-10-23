// Cổng Bộ Nội vụ dùng CÙNG hộp thoại chọn cơ quan iGate (form#ngSelectAgencyForm1: UBND tỉnh →
// Sở/Ban ngành → Sở Nội vụ) với cổng Bộ NN&MT. Phải nằm trong danh sách cổng bộ thì content mới
// báo maeAgencyBlock và nhận ra bước wizard; thiếu là bot đứng im ở hộp thoại.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
const portalMae = fs.readFileSync(path.join(root, "content", "portal-mae.js"), "utf8");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));

test("cổng Bộ Nội vụ được nhận là cổng bộ iGate", () => {
  const list = content.match(/const maeHost = \[([\s\S]*?)\]\.includes\(location\.hostname\)/);
  assert.ok(list, "không tìm thấy danh sách maeHost");
  assert.match(list[1], /"dichvucongbnv\.moha\.gov\.vn"/);
});

test("engine hộp thoại không khoá theo tên miền và được nạp trên cổng Bộ Nội vụ", () => {
  assert.doesNotMatch(portalMae, /location\.hostname/, "portal-mae.js không được lọc theo host");
  const block = manifest.content_scripts.find((c) => c.js.includes("content/portal-mae.js"));
  assert.ok(block.matches.includes("https://dichvucongbnv.moha.gov.vn/*"));
});
