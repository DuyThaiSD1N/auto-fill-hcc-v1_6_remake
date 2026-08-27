// Vai trò người nộp ở thủ tục "Đăng ký thay đổi nội dung hộ kinh doanh" khi hồ sơ CHỈ có tờ đơn xin
// thay đổi (không CCCD rời, không Giấy ủy quyền): căn cứ duy nhất là HỌ TÊN chủ hộ ghi trong đơn.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

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
// Object trả về nằm ở realm của vm → so sánh qua bản JSON thuần.
const plain = (value) => JSON.parse(JSON.stringify(value));

/** Dữ liệu nút "Sao chép thông tin đăng ký tài khoản" vừa đổ vào khối người nộp. */
function setAccount(hoTen, soDinhDanh) {
  ids.clear();
  ids.set("ctl00_C_PERSCtl_FULL_NAMEFld", { value: hoTen });
  ids.set("ctl00_C_PERSCtl_PERS_DOC_NOFld", { value: soDinhDanh });
}

function changeState(owner, extra = {}) {
  return { workflow: "change", businessFlow: { wizardType: "change", owner, ...extra } };
}

// --- Nhận diện hồ sơ "chỉ có tờ đơn" (cờ formOnly do backend gắn) ---------------------------------
const owner = { hoTen: "Nguyễn Văn A", soDinhDanh: "012345678901" };
assert.equal(H.isChangeFormOnlyDossier(changeState(owner, { formOnly: true })), true);
assert.equal(H.isChangeFormOnlyDossier(changeState(owner)), false, "không có cờ → giữ logic cũ");
assert.equal(
  H.isChangeFormOnlyDossier({ workflow: "create", businessFlow: { formOnly: true } }),
  false,
  "cờ formOnly chỉ áp cho luồng thay đổi",
);
assert.equal(H.isChangeFormOnlyDossier(null), false);

// --- Khác tên chủ hộ → người được ủy quyền, KỂ CẢ khi số định danh trong đơn trùng tài khoản -------
// (đơn hay thiếu số hoặc OCR lẫn số người ký với số chủ hộ, mà không có CCCD nào để phản chứng)
setAccount("TRẦN THỊ B", "012345678901");
const st = changeState(owner, { formOnly: true });
assert.deepEqual(
  plain(H.matchAccountWithOwner(st, { nameOnly: true })),
  { isOwner: false, ownerUnknown: false, idMatches: false, nameMatches: false },
);
// Cùng dữ liệu nhưng KHÔNG phải hồ sơ chỉ-có-đơn: số định danh vẫn được tính như cũ.
assert.equal(H.matchAccountWithOwner(st).isOwner, true);

// --- Trùng tên chủ hộ → chủ hộ tự nộp, giữ nguyên tick --------------------------------------------
setAccount("NGUYỄN VĂN A", "999999999999");
assert.deepEqual(
  plain(H.matchAccountWithOwner(st, { nameOnly: true })),
  { isOwner: true, ownerUnknown: false, idMatches: false, nameMatches: true },
);
// Bỏ dấu/hoa-thường không làm lệch phép so tên.
setAccount("nguyen van a", "");
assert.equal(H.matchAccountWithOwner(st, { nameOnly: true }).isOwner, true);

// --- Thiếu căn cứ → KHÔNG kết luận (giữ nguyên vai trò cổng đang tick) ----------------------------
setAccount("", "");
assert.equal(H.matchAccountWithOwner(st, { nameOnly: true }).ownerUnknown, true,
  "chưa sao chép được tên tài khoản → chưa đối chiếu");
setAccount("TRẦN THỊ B", "012345678901");
const noName = changeState({ hoTen: "", soDinhDanh: "012345678901" }, { formOnly: true });
assert.equal(H.matchAccountWithOwner(noName, { nameOnly: true }).ownerUnknown, true,
  "đơn không ghi tên chủ hộ → chưa đối chiếu");
// Cùng hồ sơ đó ở nhánh cũ vẫn kết luận được bằng số định danh.
assert.equal(H.matchAccountWithOwner(noName).isOwner, true);


// --- Đơn không kê khai chủ hộ → phải đi đọc chủ hộ THẬT trên cổng ---------------------------------
// (đơn chỉ ghi TÊN HỘ KINH DOANH + mã số; tên hộ kinh doanh KHÔNG phải tên chủ hộ)
const blankOwner = { hoTen: "", soDinhDanh: "" };
const noOwnerState = {
  workflow: "change",
  order: ["dia-chi", "nguoi-nop-ho-so"], // hồ sơ KHÔNG đổi chủ hộ → không có trang chủ hộ trong order
  businessFlow: {
    wizardType: "change", formOnly: true, owner: blankOwner,
    search: { method: "businessNumber", value: "038094024254" },
  },
};
assert.equal(H.needsOwnerProbe(noOwnerState), true);
assert.equal(H.needsOwnerProbe({ ...noOwnerState, ownerPageVisited: true }), false,
  "đã ghé một lượt rồi → không mở lại trang chủ hộ lần nữa");
assert.equal(
  H.needsOwnerProbe({ ...noOwnerState, order: ["chu-ho-kinh-doanh", "chu-ho-kinh-doanh", "nguoi-nop-ho-so"] }),
  false,
  "hồ sơ đổi chủ hộ → handleChangeOwnerPage đã lo Loại/Lý do + nhân thân",
);
assert.equal(H.needsOwnerProbe({ ...noOwnerState, workflow: "create" }), false);

// Loại/Lý do thay đổi thông tin chủ hộ LUÔN cố định, không lấy theo dữ liệu LLM đọc được.
assert.deepEqual(plain(H.OWNER_CHANGE_TYPE_FIELDS), [
  {
    name: "ctl00$C$CHANGE_OWNER_TYPE_TITLE_IDFld", comp: "dom-select",
    value: "Cập nhật thông tin chủ hộ kinh doanh",
  },
  { name: "ctl00$C$CHANGE_OWNER_TYPE_IDFld", comp: "dom-select", value: "Khác" },
]);

// Đọc ô nhân thân chủ hộ trên trang "Thông tin về chủ hộ kinh doanh" (ô khoá → span _Vw).
ids.clear();
ids.set("ctl00_C_OWN_PCtl_PERSCtl_FULL_NAMEFld_Vw", { textContent: "  MAI VĂN  TUẤN " });
ids.set("ctl00_C_OWN_PCtl_PERSCtl_PERS_DOC_NOFld", { value: "038094024254" });
assert.deepEqual(plain(H.readPortalOwner()), { hoTen: "MAI VĂN TUẤN", soDinhDanh: "038094024254" });

// Có chủ hộ đọc trên cổng → chốt được vai trò dù hồ sơ không kê khai gì.
const probed = { ...noOwnerState, portalOwner: { hoTen: "MAI VĂN TUẤN", soDinhDanh: "038094024254" } };
setAccount("NGUYỄN DUY THÁI", "001204018566");
assert.deepEqual(
  plain(H.matchAccountWithOwner(probed, { nameOnly: true })),
  { isOwner: false, ownerUnknown: false, idMatches: false, nameMatches: false },
  "khác tên chủ hộ → Người được ủy quyền",
);
setAccount("Mai Văn Tuấn", "111111111111");
assert.equal(H.matchAccountWithOwner(probed, { nameOnly: true }).isOwner, true, "trùng tên chủ hộ");
// Số định danh do CHÍNH CỔNG cung cấp vẫn được dùng kể cả ở nhánh nameOnly (không phải số OCR).
setAccount("MAI V. TUẤN", "038094024254");
assert.deepEqual(
  plain(H.matchAccountWithOwner(probed, { nameOnly: true })),
  { isOwner: true, ownerUnknown: false, idMatches: true, nameMatches: false },
);

console.log("business-change-submitter-role.test.js OK");
