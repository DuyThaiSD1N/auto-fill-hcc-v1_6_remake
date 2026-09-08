// Vai trò "Người được ủy quyền" ở thủ tục ĐĂNG KÝ KINH DOANH (cổng HkdOnline).
//
// Lỗi thật: bản trong repo này là nhánh cũ, thiếu nhịp "ghé trang chủ hộ đọc họ tên" mà extension
// chính (auto-fill-hcc-extension) đã có. Hồ sơ THAY ĐỔI NỘI DUNG HKD không đổi chủ hộ thì backend
// KHÔNG xếp trang "chu-ho-kinh-doanh" vào order ⇒ trong state không có nhân thân chủ hộ nào; đơn
// xin thay đổi cũng chỉ ghi TÊN HỘ KINH DOANH + mã số, không phải tên chủ hộ.
// ⇒ matchAccountWithOwner luôn trả ownerUnknown ⇒ nhánh tick "Người được ủy quyền" KHÔNG BAO GIỜ
// chạy, cán bộ phải tự tick tay.
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");

const SOURCE = fs.readFileSync(
  path.join(__dirname, "..", "content", "procedures", "business-registration.js"), "utf8");

/** Nạp module với dữ liệu nút "Sao chép thông tin đăng ký tài khoản" đã đổ vào khối người nộp. */
function load({ accountName = "NGUYỄN VĂN B", accountId = "001099000222" } = {}) {
  const stub = {
    sleep: async () => {},
    norm: (v) => String(v || "").trim().toLowerCase().replace(/\s+/g, " "),
    fieldCandidates: (f) => [f.name],
    setNativeValue() {}, waitFor: async () => false, readAcctContact: () => "",
    isVisible: () => true, fillFormStandard: async () => {},
    findStandardInput: () => null, findStandardSelect: () => null,
    isPostbackAddressField: () => false,
  };
  const sandbox = {
    console: { log() {}, warn() {}, error() {} },
    Event, MouseEvent: class {}, setTimeout, clearTimeout,
    getComputedStyle: () => ({ display: "block", visibility: "visible", opacity: "1" }),
    chrome: { storage: { local: { get: async () => ({}), set: async () => {}, remove: async () => {} } }, runtime: {} },
    CSS: { escape: (s) => s },
    MutationObserver: class { constructor(cb) { this.cb = cb; } observe() {} disconnect() {} },
    document: {
      body: {}, forms: { namedItem: () => null },
      getElementById: (id) => ({
        ctl00_C_PERSCtl_FULL_NAMEFld: { value: accountName },
        ctl00_C_PERSCtl_PERS_DOC_NOFld: { value: accountId },
      }[id] || null),
      querySelector: () => null, querySelectorAll: () => [],
    },
  };
  sandbox.window = {
    location: { pathname: "/HkdOnline/Forms/APP/Registration.aspx", hostname: "hokinhdoanh.dkkd.gov.vn" },
    __TLND__: stub, addEventListener() {}, removeEventListener() {},
  };
  vm.runInNewContext(SOURCE, sandbox, { filename: "business-registration.js" });
  return sandbox.window.__TLND__;
}

/** Hồ sơ thay đổi nội dung HKD, KHÔNG đổi chủ hộ, chỉ có tờ đơn. */
function changeState(extra = {}) {
  return {
    workflow: "change",
    order: ["nganh-nghe-kinh-doanh", "nguoi-nop-ho-so"],
    pages: { "nguoi-nop-ho-so": [] },
    businessFlow: {
      wizardType: "change", formOnly: true,
      search: { method: "businessNumber", value: "8888888888" },
    },
    ...extra,
  };
}

test("phải ghé trang chủ hộ khi order không có trang đó", () => {
  const H = load();
  assert.equal(typeof H.needsOwnerProbe, "function", "thiếu hàm là mất luôn nhịp đọc chủ hộ");
  assert.equal(H.needsOwnerProbe(changeState()), true);
});

test("ghé đúng MỘT lượt cho cả phiên", () => {
  const H = load();
  assert.equal(H.needsOwnerProbe(changeState({ ownerPageVisited: true })), false);
});

test("order đã có trang chủ hộ thì không cần ghé", () => {
  const H = load();
  const st = changeState();
  st.order = ["chu-ho-kinh-doanh", "nguoi-nop-ho-so"];
  assert.equal(H.needsOwnerProbe(st), false);
});

test("luồng đăng ký mới không ghé (đã có trang chủ hộ trong hồ sơ)", () => {
  const H = load();
  assert.equal(H.needsOwnerProbe({ ...changeState(), workflow: "create" }), false);
});

test("CHƯA đọc được chủ hộ → ownerUnknown, giữ nguyên radio", () => {
  const H = load();
  const r = H.matchAccountWithOwner(changeState());
  assert.equal(r.ownerUnknown, true);
  assert.equal(r.isOwner, false);
});

test("ĐỌC ĐƯỢC chủ hộ trên cổng, khác tài khoản → tick Người được ủy quyền", () => {
  const H = load({ accountName: "NGUYỄN VĂN B" });
  const st = changeState({ portalOwner: { hoTen: "TRẦN THỊ A", soDinhDanh: "001099000111" } });
  const r = H.matchAccountWithOwner(st, { nameOnly: true });
  assert.equal(r.ownerUnknown, false, "đã có căn cứ để so");
  assert.equal(r.isOwner, false, "khác chủ hộ ⇒ nhánh tick Người được ủy quyền");
});

test("ĐỌC ĐƯỢC chủ hộ, TRÙNG tên tài khoản → giữ Người có thẩm quyền ký", () => {
  const H = load({ accountName: "TRẦN THỊ A" });
  const st = changeState({ portalOwner: { hoTen: "TRẦN THỊ A", soDinhDanh: "001099000111" } });
  const r = H.matchAccountWithOwner(st, { nameOnly: true });
  assert.equal(r.isOwner, true);
});

test("hồ sơ chỉ có tờ đơn: KHÔNG dùng số định danh đọc từ giấy tờ làm căn cứ", () => {
  // Số trong đơn hay bị OCR lẫn giữa người ký và chủ hộ; chỉ số do CHÍNH CỔNG cấp mới đáng tin.
  const H = load({ accountId: "001099000222" });
  const st = changeState();
  st.businessFlow.owner = { hoTen: "", soDinhDanh: "001099000222" };
  assert.equal(H.matchAccountWithOwner(st, { nameOnly: true }).isOwner, false,
    "số đọc từ hồ sơ không được tự nhận là chủ hộ");
  assert.equal(H.matchAccountWithOwner(st).isOwner, true,
    "hồ sơ có CCCD rời thì vẫn so bằng số như cũ");
});

test("isChangeFormOnlyDossier chỉ bật cho hồ sơ thay đổi có cờ formOnly", () => {
  const H = load();
  assert.equal(H.isChangeFormOnlyDossier(changeState()), true);
  const noFlag = changeState();
  noFlag.businessFlow.formOnly = false;
  assert.equal(H.isChangeFormOnlyDossier(noFlag), false);
});
