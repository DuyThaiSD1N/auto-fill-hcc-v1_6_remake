const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const fillCore = fs.readFileSync(path.join(root, "content/fill-core.js"), "utf8");

test("trợ lý gửi formContext vào chat giống auto-fill", () => {
  assert.match(fillCore, /msg\.action === "collectFormContext"/);
  assert.match(fillCore, /const formContext = collectFormContext\(\);/);
  // eForm Bộ Tư pháp: gộp dữ liệu VNeID của tài khoản (getDataEform) như auto-fill.
  assert.match(fillCore, /collectMojAccountContext\(\)\s*\.then\(\(account\) => sendResponse\(\{ ok: true, formContext: \{ \.\.\.formContext, \.\.\.account \} \}\)\)/);
  assert.match(fillCore, /api\/eform-service\/eform\/getDataEform/);
  assert.match(sidebar, /sendToContent\(\{ action: "collectFormContext" \}\)/);
  assert.match(sidebar, /form_context: formResult\?\.formContext \|\| \{\}/);
  assert.match(sidebar, /attachment_context: attachmentResult\?\.attachmentContext \|\| \{\}/);
  // preferredLang: ngôn ngữ máy quầy (tiếng Mông) để phiên MỚI chào đúng tiếng ngay lượt đầu.
  assert.match(sidebar, /apiAskRetrying\(message, \{ source, displayText, clientContext, preferredLang \}, source\)/);
});

test("cổng Bộ Công an: mốc tài khoản lấy từ ô KHOÁ Phần I (CongDan_tenCongDan / CongDan_soCmnd)", () => {
  // User 20/11/2026 (1.013066): trợ lý điền giấy tờ của người khác vào hồ sơ của chủ tài khoản VNeID vì không có mốc.
  assert.match(fillCore, /readLizAccountValue\(\["ten nguoi"\]\) \|\|\s*readBcaAccountValue\("CongDan_tenCongDan"\)/);
  assert.match(fillCore,
    /readLizAccountValue\(\["cmnd", "so dinh danh"\]\) \|\|\s*readBcaAccountValue\("CongDan_soCmnd"\)/);
  const vm = require("node:vm");
  const start = fillCore.indexOf("function readBcaAccountValue(");
  const end = fillCore.indexOf("\nfunction collectFormContext(", start);
  assert.ok(start >= 0 && end > start, "Không tách được readBcaAccountValue");
  const inputs = {
    CongDan_tenCongDan: { value: " NGUYỄN VĂN AN ", readOnly: true },
    CongDan_soCmnd: { value: "001090000001", readOnly: false, disabled: false },
  };
  const box = {
    CSS: { escape: (s) => s },
    isPlaceholderText: () => false,
    location: { hostname: "dichvucong.bocongan.gov.vn" },
    document: { querySelector: (sel) => inputs[/name="([^"]+)"/.exec(sel)[1]] || null },
  };
  vm.runInNewContext(`${fillCore.slice(start, end)}\nthis.read = readBcaAccountValue;`, box);
  assert.equal(box.read("CongDan_tenCongDan"), "NGUYỄN VĂN AN");
  assert.equal(box.read("CongDan_soCmnd"), "", "ô cổng cho sửa là dữ liệu kê khai, không phải mốc tài khoản");
  inputs.CongDan_soCmnd.disabled = true;
  assert.equal(box.read("CongDan_soCmnd"), "001090000001");
  box.location = { hostname: "dichvucong.laocai.gov.vn" };
  assert.equal(box.read("CongDan_tenCongDan"), "", "chỉ cổng Bộ Công an");
});

test("formContext báo đơn xin nhận con nuôi đang mở (eForm trong Thành phần hồ sơ)", () => {
  // BE chỉ điền khi formVariant khớp declarationEforms của thủ tục nuôi con nuôi trong nước.
  assert.match(fillCore, /const adoptionSignature = \["HoVaTenCN", "truongHopNhanNuoi"\];/);
  assert.match(fillCore, /formVariant = "adoption_application";/);
  assert.match(fillCore, /\.\.\.\(combinedVariant \|\| \{\}\),/);
});

test("cổng Bộ VHTTDL (liz): nạp fill-liz.js sau fill-core, dispatcher gọi fillFormLiz, đọc người nộp theo nhãn", () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));
  const scripts = manifest.content_scripts[0].js;
  assert.ok(scripts.indexOf("content/fill-liz.js") > scripts.indexOf("content/fill-core.js"));
  assert.ok(scripts.indexOf("content/fill-liz.js") < scripts.indexOf("content.js"));
  const fillLiz = fs.readFileSync(path.join(root, "content/fill-liz.js"), "utf8");
  assert.match(fillLiz, /const H = window\.__TLND__ \|\| \(window\.__TLND__ = \{\}\);/);
  assert.match(fillLiz, /H\.fillFormLiz = fillFormLiz;/);
  assert.match(fillCore, /formKind === "liz" \? H\.fillFormLiz/);
  assert.match(fillCore, /readBacNinhAccountValue\("hoTen"\) \|\|\s*readLizAccountValue\(\["ten nguoi"\]\)/);
  assert.match(fillCore, /readBacNinhAccountValue\("soDinhDanh"\) \|\|\s*readLizAccountValue\(\["cmnd", "so dinh danh"\]\)/);
});
