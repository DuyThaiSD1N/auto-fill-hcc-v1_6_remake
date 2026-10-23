// Contract luồng "[BN] Đăng ký biện pháp bảo đảm QSDĐ" (dichvucong.bacninh.gov.vn, Liferay
// eForm 2 tab CÙNG TRANG): engine fill-bacninh đồng bộ bản auto-fill (có activateBacNinhTab),
// fill/attach tự mở đúng tab trước khi thao tác, manifest + background phủ host Bắc Ninh.
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const engine = read("content/fill-bacninh.js");
const fillCore = read("content/fill-core.js");
const attachCore = read("content/attach-core.js");
const manifest = JSON.parse(read("manifest.json"));
const background = read("background.js");

test("activateBacNinhTab chuyển tab CHẮC CHẮN: click href thật rồi fallback toggle class hide/active", () => {
  // Cổng có thể chặn CSP điều hướng javascript: → link.click() im lặng, tab không đổi.
  // Phải có fallback tự bật/tắt class "hide" trên pane + "active" trên nút như Liferay làm.
  assert.ok(engine.includes("function bacNinhTabSection(li)"),
    "thiếu helper map li→pane (TabsId→TabsSection)");
  assert.ok(engine.includes("link.click()"), "phải thử hàm thật của cổng trước");
  assert.ok(engine.includes('sec.classList.toggle("hide", !isTarget)'),
    "thiếu fallback toggle class 'hide' khi click javascript: bị chặn");
  assert.ok(engine.includes('a.classList.toggle("active", isTarget)'));
});

test("fill-bacninh đồng bộ bản auto-fill: tab helper + khớp class eform-element + select2 async", () => {
  assert.ok(engine.includes("async function activateBacNinhTab(tabName)"));
  // Khớp ô theo CLASS ngữ nghĩa ổn định (nhiều ô trùng title "Số"/"cấp ngày" → bắt buộc có).
  assert.ok(engine.includes("function findElementByClass(name)"));
  assert.ok(engine.includes("findElementByClass(name) || findElementByName(name) || findElementByLabel"));
  // Select cascade Tỉnh/Xã nạp option qua AJAX → phải có bản chờ bất đồng bộ.
  assert.ok(engine.includes("async function fillSelect2ByTextAsync"));
  // Tick radio ƯU TIÊN TRÙNG KHỚP CHÍNH XÁC — "Bên thế chấp" không được dính option dài hơn.
  assert.match(engine, /const exact = labeled\.filter\(\(x\) => x\.lbl === w\);/);
  assert.ok(engine.includes("window.__TLND__"), "namespace phải là __TLND__ sau khi port");
  assert.ok(!engine.includes("window.__HCC__"));
});

test("fill: trước khi điền form Bắc Ninh phải mở tab 'Nhập đơn đăng ký'", () => {
  const i = fillCore.indexOf('formKind === "bacninh"');
  assert.ok(i > 0);
  assert.ok(fillCore.includes('H.activateBacNinhTab("nhapdondangky")'),
    "thiếu bước mở tab nhapdondangky — ô đơn nằm trong pane ẩn, công dân không thấy bot điền");
});

test("attach: engine Bắc Ninh phải mở tab 'Tải thành phần hồ sơ' trước khi đính", () => {
  const i = attachCore.indexOf("H.attachBacNinhByPlan");
  assert.ok(i > 0);
  const block = attachCore.slice(Math.max(0, i - 600), i + 200);
  assert.ok(block.includes('H.activateBacNinhTab("taithanhphan")'),
    "thiếu bước mở tab taithanhphan trước attachBacNinhByPlan");
});

test("manifest + background phủ host dichvucong.bacninh.gov.vn (inject + dọn phiên đăng xuất)", () => {
  const bn = "https://dichvucong.bacninh.gov.vn/*";
  assert.ok(manifest.content_scripts[0].matches.includes(bn));
  assert.ok(manifest.host_permissions.includes(bn));
  assert.ok(background.includes('"dichvucong.bacninh.gov.vn"'), "CITIZEN_COOKIE_HOSTS thiếu Bắc Ninh");
  assert.ok(background.includes('"https://dichvucong.bacninh.gov.vn"'),
    "CITIZEN_STORAGE_ORIGINS thiếu Bắc Ninh");
  assert.ok(background.includes('"https://dichvucong.bacninh.gov.vn/*"'),
    "CITIZEN_TAB_URL_PATTERNS thiếu Bắc Ninh");
});
