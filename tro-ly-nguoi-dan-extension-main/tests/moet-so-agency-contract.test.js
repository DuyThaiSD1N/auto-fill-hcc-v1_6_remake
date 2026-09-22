// Contract cổng Bộ GD&ĐT (dvc.moet.gov.vn — nền iGate như MAE) + chế độ chọn "Sở" trên
// DVCQG (select_agency soMode): chọn Tỉnh → gạt toggle "Sở" (không chọn sở) → Đồng ý →
// "Nộp trực tuyến" kết quả ĐẦU TIÊN của danh sách.
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const manifest = JSON.parse(read("manifest.json"));
const sidebar = read("sidebar.js");
const content = read("content.js");
const portalDvc = read("content/portal-dvc.js");

test("manifest khai đủ cổng moet: host_permissions + content script match", () => {
  assert.ok(manifest.host_permissions.includes("https://dvc.moet.gov.vn/*"),
    "thiếu host_permissions cho dvc.moet.gov.vn (dọn cookie/phiên cần quyền này)");
  assert.ok(manifest.content_scripts[0].matches.includes("https://dvc.moet.gov.vn/*"));
});

test("content.js nhận moet + moc là host iGate (wizard 4 bước dùng chung với MAE)", () => {
  // Kiểm THÀNH VIÊN, không khoá nguyên văn: danh sách còn thêm cổng bộ khác (vd Bộ Nội vụ).
  const list = content.match(/const maeHost = \[([\s\S]*?)\]\.includes\(location\.hostname\)/);
  assert.ok(list, "không tìm thấy danh sách maeHost");
  for (const host of ["dichvucongnnmt.mae.gov.vn", "dvc.moet.gov.vn", "dvc.moc.gov.vn"]) {
    assert.ok(list[1].includes(`"${host}"`),
      `${host} phải nằm trong danh sách host iGate để phát wizardStep/attachmentTarget`);
  }
});

test("manifest khai đủ cổng moc (Bộ Xây dựng — NOXH)", () => {
  assert.ok(manifest.host_permissions.includes("https://dvc.moc.gov.vn/*"));
  assert.ok(manifest.content_scripts[0].matches.includes("https://dvc.moc.gov.vn/*"));
});

test("sidebar truyền soMode từ action select_agency xuống content script", () => {
  assert.ok(sidebar.includes("soMode: a.soMode === true"));
});

test("fill-core đồng bộ engine standard từ auto-fill: đủ mảnh cho cổng GD&ĐT", () => {
  const fillCore = read("content/fill-core.js");
  // Checkbox "Người nộp là chủ hồ sơ" của moet là data[isOwnerDossier] (KHÔNG phải
  // isOwnerDossierCheck) — thiếu là tick tự-nộp không copy Phần I sang chủ hồ sơ.
  assert.ok(fillCore.includes('fieldCandidates(f).includes("data[isOwnerDossier]")'));
  // Cascade Tỉnh/Phường-xã Phần VIII của moet dùng key riêng tinhtp/px1/tinhthanhpho/quanhuyen.
  assert.match(fillCore, /isAreaSelectName[\s\S]{0,1500}tinhtp\|px1/);
  // Máy chọn select Form.io (dataSrc url — identityAgency value là OBJECT, không được bịa).
  assert.ok(fillCore.includes("function fillFormioSelectComponent"));
  assert.ok(fillCore.includes("function formioOptionToValue"));
  assert.ok(fillCore.includes("function orderStandardFields"));
  // Fold gộp mọi dấu gạch (en-dash OCR vs hyphen option) cho select địa bàn.
  assert.match(fillCore, /foldChoiceText[\s\S]{0,600}\[-–—‐‑\]/);
  // Const engine THAM CHIẾU (không phải lời gọi) — thiếu là mọi select tỉnh/xã ném
  // ReferenceError bị try/catch per-field nuốt ("text điền được, select chết").
  assert.ok(fillCore.includes("const STANDARD_AREA_FIELD_BUDGET_MS"));
  assert.ok(fillCore.includes("const STANDARD_AREA_STABILIZE_BUDGET_MS"));
  assert.ok(fillCore.includes("const searchedStandardSelects = new WeakSet()"));
  assert.ok(fillCore.includes("function _cellMatches"));
  assert.ok(fillCore.includes("function _fillDatagridVehicleRow"));
  // norm của tro-ly GIỮ normalize("NFC") (option NFD vs value NFC) — không được hạ cấp
  // theo bản auto-fill.
  assert.match(fillCore, /const norm = \(s\) => \(s \|\| ""\)\.normalize\("NFC"\)/);
});

test("portal-dvc: soMode CHỈ gạt toggle Sở rồi Đồng ý — không chọn sở trong combo", () => {
  assert.ok(portalDvc.includes("async function switchToSoToggle"));
  // Toggle khớp text fold ĐÚNG "so" (không match từ dài hơn).
  assert.ok(portalDvc.includes('fold(el.textContent) === "so"'));
  // "Cái đầu tiên" = kết quả đầu của DANH SÁCH sau Đồng ý (clickNopTrucTuyen),
  // KHÔNG phải option đầu của dropdown Sở → cấm mọi bước chọn combo trong nhánh soMode.
  assert.ok(!portalDvc.includes("pickComboFirst"));
  assert.ok(/if \(soMode\) \{[\s\S]{0,400}switchToSoToggle\(block\)[\s\S]{0,200}\} else \{/.test(portalDvc));
  // Nhánh cũ (chọn xã) giữ nguyên cho các thủ tục tư pháp đang phát hành.
  assert.ok(portalDvc.includes('await pickCombo(combos[1], ward, { force: true, timeout: 8000 })'));
  // Listener truyền tham số mới.
  assert.ok(portalDvc.includes("soMode: msg.soMode === true"));
});
