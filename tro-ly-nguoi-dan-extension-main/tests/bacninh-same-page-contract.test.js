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

// ── Khối "Thông tin trong trường hợp được ủy quyền": chạy THẬT fill-bacninh.js trong vm, DOM giả ──
const vm = require("node:vm");
const PFX = "_org_bn_hoso_noptructuyen_";

function loadBacNinhEngine({ hasBlock = true } = {}) {
  const order = [];
  let blockOpen = false;
  const inputs = new Map();
  const input = (name) => {
    if (!inputs.has(name)) {
      inputs.set(name, {
        tagName: "INPUT", value: "",
        getAttribute: (a) => (a === "type" ? "text" : a === "name" ? name : null),
        dispatchEvent() {},
      });
    }
    return inputs.get(name);
  };
  const checkbox = { checked: false, click() { this.checked = true; order.push("tick"); }, dispatchEvent() {} };
  const typeSelect = {
    tagName: "SELECT", value: "", getAttribute: () => null,
    options: [{ textContent: "-- Chọn --", value: "" },
      { textContent: "Cá nhân khác là Công dân Việt Nam", value: "2" }],
    dispatchEvent() { if (this.value === "2") { blockOpen = true; order.push("chon-loai"); } },
  };
  const document = {
    querySelectorAll: () => [],
    querySelector(sel) {
      if (sel === `input[type="checkbox"][name="${PFX}boSungDoituongKhac"]`) return hasBlock ? checkbox : null;
      if (sel === `select[name="${PFX}loaiDoiTuongKhac"]`) return hasBlock ? typeSelect : null;
      const m = /^\[name="([^"]+)"\]$/.exec(sel);
      if (!m) return null;
      // Ô doiTuongKhac* chỉ mọc ra sau khi chọn loại đối tượng (AJAX trên cổng thật).
      if (m[1].startsWith(`${PFX}doiTuongKhac`)) return blockOpen ? input(m[1]) : null;
      return m[1] === `${PFX}element_75701` ? input(m[1]) : null;
    },
  };
  const H = {
    setNativeValue(el, value) { el.value = value; order.push(el.getAttribute("name").replace(PFX, "")); },
    markFilled() {},
    injectAutofillStyles() {},
  };
  const ctx = {
    document, console, setTimeout, __TLND__: H,
    CSS: { escape: (s) => s },
    Event: class { constructor(type) { this.type = type; } },
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(engine, ctx);
  return { H, order, inputs };
}

const AUTH_FIELDS = [
  { name: "element_75701", comp: "bn-input", value: "Đơn hỏa táng" },
  { name: "loaiDoiTuongKhac", comp: "bn-doi-tuong-khac", value: "Cá nhân khác là Công dân Việt Nam" },
  { name: "doiTuongKhachoTen", comp: "bn-input", value: "Nguyễn Văn A" },
];

test("khối ủy quyền: điền đơn trước, tick ô bổ sung + chọn loại đối tượng rồi mới điền doiTuongKhac*", async () => {
  const { H, order, inputs } = loadBacNinhEngine();
  const res = await H.fillFormBacNinh(AUTH_FIELDS);
  assert.deepEqual(order, ["element_75701", "tick", "chon-loai", "doiTuongKhachoTen"]);
  assert.equal(inputs.get(`${PFX}doiTuongKhachoTen`).value, "Nguyễn Văn A");
  assert.equal(res.ok, true);
  assert.equal(res.filled, 3);
  assert.deepEqual([...res.unmatched], []);
  assert.deepEqual([...res.errors], []);
});

test("khối ủy quyền: trang không có khối → đơn vẫn điền, ô ủy quyền vào unmatched kèm lỗi", async () => {
  const { H, order } = loadBacNinhEngine({ hasBlock: false });
  const res = await H.fillFormBacNinh(AUTH_FIELDS);
  assert.deepEqual(order, ["element_75701"]);
  assert.equal(res.filled, 1);
  assert.deepEqual([...res.unmatched], ["loaiDoiTuongKhac", "doiTuongKhachoTen"]);
  assert.match(res.errors[0], /Không thấy khối Thông tin trong trường hợp được ủy quyền/);
});

// ── Đính kèm: ô "Số lượng" Bản chính (`thanhPhanHoSo<id>banChinhsoBo`) = số tệp đã đính ──
function loadBacNinhAttach({ landedBefore = 0 } = {}) {
  const ID = "50511";
  const qty = { value: "1", getAttribute: () => "number" };
  const fileInput = { files: [], multiple: true, hasAttribute: () => true, closest: () => null };
  const landed = { querySelectorAll: () => Array.from({ length: landedBefore }, () => ({})) };
  const row = { textContent: "TP-H05.000026 Mẫu số 18. Đơn đăng ký biến động đất đai" };
  const checkbox = {
    checked: true, getAttribute: (a) => (a === "name" ? `${PFX}thanhPhanHoSo${ID}` : null),
    closest: (s) => (s === "tr" ? row : null),
  };
  const ids = { [`${PFX}thanhPhanHoSo${ID}banChinhsoBo`]: qty, [`${PFX}thanhPhanHoSobanChinh${ID}`]: landed };
  const document = {
    querySelectorAll: (sel) => (sel.includes("thanhPhanHoSo") && sel.includes("checkbox") ? [checkbox] : []),
    querySelector: (sel) => (sel.includes(`filethanhPhanHoSobanChinh${ID}`) ? fileInput : null),
    getElementById: (id) => ids[id] || null,
  };
  const H = {
    setNativeValue(el, value) { el.value = value; },
    setFilesOnInput: () => true,
    dataUrlToFile: (p, name) => ({ name }),
    sleep: () => Promise.resolve(),
  };
  // slotHasFile: lượt trước đã lên tệp → input.files giữ tệp (giả lập ô đã có file).
  if (landedBefore) fileInput.files = [{}];
  const ctx = { document, console, setTimeout, __TLND__: H, CSS: { escape: (s) => s }, Event: class {} };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(engine, ctx);
  return { H, qty };
}

const ATTACH_PLAN = ["Đơn 18.pdf", "Phiếu đo đạc.pdf", "Hồ sơ kỹ thuật.pdf", "Căn cước.pdf"].map((n, i) => ({
  fileIndex: i, componentName: "Mẫu số 18. Đơn đăng ký biến động", slotKey: "banChinh", documentName: n,
}));

test("đính 4 tệp vào Bản chính → ô Số lượng ghi 4 thay mặc định 1", async () => {
  const { H, qty } = loadBacNinhAttach();
  const res = await H.attachBacNinhByPlan(["a", "b", "c", "d"], ATTACH_PLAN);
  assert.equal(res.attached, 4);
  assert.equal(qty.value, "4");
});

test("ô đã có tệp từ lượt trước → bỏ qua đính lại nhưng vẫn sửa Số lượng theo số tệp đang có", async () => {
  const { H, qty } = loadBacNinhAttach({ landedBefore: 4 });
  const res = await H.attachBacNinhByPlan(["a", "b", "c", "d"], ATTACH_PLAN);
  assert.equal(res.skipped, 4);
  assert.equal(qty.value, "4");
});

test("sidebar khai cờ supportsBacNinhAuthorizedPerson để BE chạy lượt người ủy quyền", () => {
  assert.match(read("sidebar.js"), /supportsBacNinhAuthorizedPerson: true,/);
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
