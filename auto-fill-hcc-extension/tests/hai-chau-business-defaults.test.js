// Nghiệp vụ riêng phường Hải Châu — thành phố Đà Nẵng, và vai trò người nộp ở thủ tục CHẤM DỨT.
//  1. popup.js: tài khoản Hải Châu/Đà Nẵng mới có default "Lý do giải thể" + "Địa chỉ nhận kết quả".
//  2. content script: hai default đó được ghi đè/thêm vào đúng trang, đúng ô.
//  3. Thủ tục chấm dứt KHÔNG còn ép "Người có thẩm quyền ký" → tự đối chiếu tài khoản với chủ hộ.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const REASON_FIELD = "ctl00$C$UC_DW_DISSOLUTIONCtl$REASON_DESCFld";
const POSTAL_FIELD = "ctl00$C$POSTAL_SERVICEFld";
const REASON = "Chấm dứt hoạt động kinh doanh";
const POSTAL =
  "Trung tâm Phục vụ Hành chính công phường Hải Châu - 15 Lê Hồng Phong, thành phố Đà Nẵng (Quầy số 5 - khu A)";

// ===== 1. popup.js — ai được áp default =====
const popupSource = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");
const start = popupSource.indexOf("const XUAN_HUONG_BUSINESS_ACT_TEXT");
const end = popupSource.indexOf("\nfunction selectedProcedureConfig", start);
assert.ok(start >= 0 && end > start, "Không tách được khối default theo tài khoản HKD");

const popupBox = {};
vm.runInNewContext(`
  function normalizeProcedureSearch(value) {
    return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase().trim();
  }
  ${popupSource.slice(start, end)}
  globalThis.buildDefaults = buildBusinessDefaults;
`, popupBox);
const buildDefaults = popupBox.buildDefaults;

const haiChau = buildDefaults({ username: "haichautest", xa: "Hải Châu", tinh: "Đà Nẵng" });
assert.equal(haiChau.dissolutionReason, REASON);
assert.equal(haiChau.postalServiceAddress, POSTAL);
assert.equal(haiChau.forceSelfSubmitter, true, "vẫn giữ ngoại lệ Đà Nẵng sẵn có");

// Phường khác của Đà Nẵng: chỉ có ngoại lệ Đà Nẵng cũ, KHÔNG có default của Hải Châu.
const sonTra = buildDefaults({ xa: "Sơn Trà", tinh: "Đà Nẵng" });
assert.equal(sonTra.dissolutionReason, undefined);
assert.equal(sonTra.postalServiceAddress, undefined);
// "Xã Hải Châu" của Thanh Hóa KHÔNG được ăn theo.
assert.equal(buildDefaults({ xa: "Hải Châu", tinh: "Thanh Hóa" }), null);
assert.equal(buildDefaults(null), null);

// ===== 2 + 3. content script =====
const ids = new Map();
const sandbox = {
  console: { log() {}, warn() {}, error() {} },
  Event,
  MouseEvent: class {},
  setTimeout,
  clearTimeout,
  getComputedStyle: () => ({ display: "block", visibility: "visible" }),
  chrome: { storage: { local: { get() {}, set() {}, remove() {} } }, runtime: {} },
  document: {
    getElementById: (id) => ids.get(id) || null,
    querySelector: () => null,
    querySelectorAll: () => [],
    forms: { namedItem: () => null },
  },
};
sandbox.window = {
  location: { pathname: "/HkdOnline/Forms/APP/Registration.aspx" },
  __HCC__: {
    sleep: async () => {},
    norm: (value) => String(value || "").trim().toLowerCase().replace(/\s+/g, " "),
    fieldCandidates: () => [],
    setNativeValue: () => {},
    waitFor: async () => false,
    readAcctContact: () => "",
    fillFormStandard: async () => {},
    findStandardInput: () => null,
    findStandardSelect: () => null,
    isPostbackAddressField: () => false,
  },
  addEventListener() {},
};
vm.runInNewContext(
  fs.readFileSync(path.join(__dirname, "..", "content", "procedures", "business-registration.js"), "utf8"),
  sandbox,
  { filename: "business-registration.js" },
);
const H = sandbox.window.__HCC__;
const apply = H.applyBusinessLocalDefaults;
const valueOf = (fields, name) => (fields.find((f) => f.name === name) || {}).value;

// --- Trang "Chấm dứt hoạt động": ghi đè lý do đọc từ hồ sơ ---
const dossier = [
  { name: "ctl00$C$UC_DW_DISSOLUTIONCtl$DISSOLUTION_TYPE_IDFld", comp: "dom-select", value: "OTHER" },
  { name: REASON_FIELD, comp: "dom-input", value: "Chấm dứt hiệu lực mã số thuế 048176007007..." },
];
const forced = apply(dossier, haiChau, "cham-dut-hoat-dong");
assert.equal(valueOf(forced, REASON_FIELD), REASON);
assert.equal(forced.length, 2, "không nhân đôi ô lý do");
assert.equal(valueOf(forced, "ctl00$C$UC_DW_DISSOLUTIONCtl$DISSOLUTION_TYPE_IDFld"), "OTHER",
  "loại hình chấm dứt giữ nguyên");
assert.notEqual(valueOf(dossier, REASON_FIELD), REASON, "không sửa mảng gốc");

// Backend không trả ô lý do → tự thêm (ô bắt buộc trên cổng).
const added = apply([], haiChau, "cham-dut-hoat-dong");
assert.equal(added.length, 1);
assert.equal(valueOf(added, REASON_FIELD), REASON);
assert.equal(added[0].comp, "dom-input");

// --- Trang "Người nộp hồ sơ": thêm Địa chỉ nhận kết quả, cho MỌI thủ tục HKD ---
const submitter = apply([{ name: "ctl00$C$PERS_SUBGroup", comp: "dom-radio", value: "x" }],
  haiChau, "nguoi-nop-ho-so");
assert.equal(submitter.length, 2);
assert.equal(valueOf(submitter, POSTAL_FIELD), POSTAL);

// --- Ngoài phạm vi: không đụng gì ---
assert.equal(apply(dossier, sonTra, "cham-dut-hoat-dong").length, 2);
assert.equal(valueOf(apply(dossier, sonTra, "cham-dut-hoat-dong"), REASON_FIELD), dossier[1].value);
assert.equal(apply([], sonTra, "nguoi-nop-ho-so").length, 0);
assert.equal(apply([], haiChau, "thong-tin-ve-von").length, 0, "trang khác không có default nào");
assert.equal(apply([], null, "cham-dut-hoat-dong").length, 0);
assert.equal(apply(null, haiChau, "cham-dut-hoat-dong").length, 1);

// --- Vai trò người nộp: chấm dứt KHÔNG còn bị ép "Người có thẩm quyền ký" ---
const daNang = { forceSelfSubmitter: true };
assert.equal(H.forceSelfSubmitter({ workflow: "dissolution", businessDefaults: daNang }), false,
  "chấm dứt phải tự đối chiếu tài khoản với chủ hộ");
assert.equal(H.forceSelfSubmitter({ workflow: "create", businessDefaults: daNang }), true,
  "đăng ký hộ KD mới vẫn giữ ngoại lệ cũ");
assert.equal(H.forceSelfSubmitter({ businessDefaults: daNang }), true, "không có workflow = create");
assert.equal(H.forceSelfSubmitter({ workflow: "change", businessDefaults: daNang }), false);
assert.equal(H.forceSelfSubmitter({ workflow: "dissolution", businessDefaults: null }), false);

// Với chấm dứt, tài khoản KHÁC chủ hộ ⇒ matchAccountWithOwner báo không phải chủ hộ → nhánh
// "Người được ủy quyền" ở handleCopyPersonPage.
ids.set("ctl00_C_PERSCtl_FULL_NAMEFld", { value: "NGUYỄN DUY THÁI" });
ids.set("ctl00_C_PERSCtl_PERS_DOC_NOFld", { value: "001204018566" });
const state = {
  workflow: "dissolution",
  businessDefaults: daNang,
  businessFlow: { owner: { hoTen: "MAI VĂN TUẤN", soDinhDanh: "038094024254" } },
};
const match = H.matchAccountWithOwner(state);
assert.equal(match.isOwner, false);
assert.equal(match.ownerUnknown, false);

console.log("hai-chau-business-defaults: OK");
