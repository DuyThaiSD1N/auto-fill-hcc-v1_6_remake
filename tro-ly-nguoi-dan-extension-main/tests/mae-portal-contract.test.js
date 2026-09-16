// Contract luồng cổng Bộ NN&MT (dichvucongnnmt.mae.gov.vn) — thủ tục Cấp/cấp lại GP khai
// thác thủy sản: engine portal-mae + tín hiệu maeAgencyBlock + attach attp-row + attach_step.
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const manifest = JSON.parse(read("manifest.json"));
const sidebar = read("sidebar.js");
const content = read("content.js");
const portalMae = read("content/portal-mae.js");
const attachCore = read("content/attach-core.js");

test("manifest khai đủ cổng MAE: host_permissions + content script portal-mae", () => {
  assert.ok(manifest.host_permissions.includes("https://dichvucongnnmt.mae.gov.vn/*"),
    "thiếu host_permissions cho dichvucongnnmt.mae.gov.vn (dọn cookie/phiên cần quyền này)");
  const cs = manifest.content_scripts[0];
  assert.ok(cs.matches.includes("https://dichvucongnnmt.mae.gov.vn/*"));
  const jsList = cs.js;
  assert.ok(jsList.includes("content/portal-mae.js"), "portal-mae.js chưa được inject");
  assert.ok(jsList.indexOf("content/portal-mae.js") > jsList.indexOf("content/fill-core.js"),
    "portal-mae phải nạp SAU fill-core");
});

test("content.js phát tín hiệu maeAgencyBlock và null formKind trên trang chọn cơ quan MAE", () => {
  assert.ok(content.includes('form#ngSelectAgencyForm1'), "nhận trang MAE theo id form ổn định");
  assert.ok(content.includes("maeAgencyBlock,"), "getPageContext phải trả maeAgencyBlock");
  assert.ok(/formKind:\s*\(loginPage \|\| infoModal \|\| maeAgencyBlock/.test(content),
    "maeAgencyBlock phải null formKind (3 radio của form MAE gây dương tính giả standard)");
  assert.ok(content.includes('"thong tin ho so", "thanh phan ho so", "thong tin phi", "nop ho so"'),
    "wizard MAE 4 nhãn riêng");
});

test("sidebar chuyển maeAgencyBlock lên BE: pageSignal + payload page_status + watcher sig", () => {
  assert.ok(/pageSignal = \(c\) =>[\s\S]{0,400}c\.maeAgencyBlock/.test(sidebar),
    "pageSignal thiếu maeAgencyBlock — watcher sẽ không đánh thức BE trên trang MAE");
  assert.ok(sidebar.includes("maeAgencyBlock: !!c.maeAgencyBlock"),
    "page_status payload thiếu maeAgencyBlock");
  assert.ok(/const sig = `[^`]*maeAgencyBlock[^`]*`/.test(sidebar),
    "chữ ký watcher thiếu maeAgencyBlock — đổi trang MAE sẽ không được báo lại");
});

test("sidebar thi hành fill_mae_agency và báo lỗi qua __event:mae_agency_failed", () => {
  assert.ok(sidebar.includes('a.type === "fill_mae_agency"'));
  assert.ok(sidebar.includes('action: "fillMaeAgency"'));
  assert.ok(sidebar.includes("__event:mae_agency_failed:"));
});

test("portal-mae dùng selector ổn định (formcontrolname), không dựa id mat-* động", () => {
  for (const marker of [
    'form#ngSelectAgencyForm1',
    'mat-select[formcontrolname="${control}"]',
    '"agency1"', '"agency"', '"procedureProcess"',
    'mat-radio-group[formcontrolname="selectedLevel"]',
    "dong y va tiep tuc",
  ]) {
    assert.ok(portalMae.includes(marker), `portal-mae thiếu marker: ${marker}`);
  }
  assert.ok(!/#mat-select-\d|#mat-radio-\d/.test(portalMae), "cấm selector id mat-* động");
  assert.ok(portalMae.includes('r.value === "1"'), "radio Sở/Ban ngành khớp theo input value=1");
});

test("attach-core có engine attp-row: khớp dòng theo componentName, chống trùng, set file cuối dòng", () => {
  assert.ok(attachCore.includes("async function attachFilesByAttpRow"));
  assert.ok(/item\.target === "attp-row"/.test(attachCore), "dispatcher phải nhận target attp-row");
  assert.ok(attachCore.includes("attpRowHasDoc"), "thiếu chống đính trùng theo fingerprint tên tài liệu");
  // Header bảng MAE ("Tên giấy tờ" + "Đính kèm giấy tờ") — GIỮ NGUYÊN 2 biến thể cũ.
  assert.ok(attachCore.includes('"ten thanh phan ho so", "dinh kem tep tin"'));
  assert.ok(attachCore.includes('"ten giay to", "so ban", "tep tin"'));
  assert.ok(attachCore.includes('"ten giay to", "dinh kem giay to"'));
});

test("runAttachPlan gate theo attach_step BE gửi (MAE bước 2, tư pháp mặc định 3)", () => {
  assert.ok(sidebar.includes("Number(a.attach_step) || 3"),
    "gate wizard phải đọc attach_step từ action attach_plan, thiếu thì mặc định 3");
  assert.ok(sidebar.includes("pre.wizardStep !== attachStep"),
    "so sánh bước hiện tại với attachStep, không hardcode 3");
});
