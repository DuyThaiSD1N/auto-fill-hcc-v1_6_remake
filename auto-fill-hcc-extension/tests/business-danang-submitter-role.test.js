// Ngoại lệ Đà Nẵng: tài khoản gắn tỉnh Đà Nẵng thì vai trò người nộp LUÔN là "Người có thẩm quyền ký
// Giấy đề nghị đăng ký Hộ kinh doanh", chỉ ở 2 thủ tục đăng ký hộ KD (state không gắn workflow) và
// chấm dứt hoạt động (workflow "dissolution").
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ids = new Map();
const selectors = new Map();
const clicked = [];

const sandbox = {
  console: { log() {}, warn() {}, error() {} },
  Event,
  MouseEvent: class {},
  setTimeout,
  clearTimeout,
  CSS: { escape: (value) => String(value) },
  getComputedStyle: () => ({ display: "block", visibility: "visible" }),
  chrome: { storage: { local: { get() {}, set() {}, remove() {} } }, runtime: {} },
  document: {
    getElementById: (id) => ids.get(id) || null,
    querySelector: (selector) => selectors.get(selector) || null,
    querySelectorAll: () => [],
    forms: { namedItem: () => null },
  },
};
sandbox.window = {
  location: { pathname: "/HkdOnline/Forms/APP/Registration.aspx" },
  sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  __HCC__: {
    sleep: async () => {},
    norm: (value) => String(value || "").trim().toLowerCase().replace(/\s+/g, " "),
    fieldCandidates: () => [],
    setNativeValue: () => {},
    waitFor: async () => true,
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
const { forceSelfSubmitter, tickSubmitterSelfRadio, matchAccountWithOwner, submitterAddressFields }
  = sandbox.window.__HCC__;

const daNang = { forceSelfSubmitter: true };

// Chỉ 2 thủ tục được ép: đăng ký hộ KD (luồng 8 trang KHÔNG gắn workflow) và chấm dứt hoạt động.
assert.equal(forceSelfSubmitter({ businessDefaults: daNang }), true, "đăng ký hộ KD phải được ép");
assert.equal(forceSelfSubmitter({ businessDefaults: daNang, workflow: "create" }), true);
assert.equal(forceSelfSubmitter({ businessDefaults: daNang, workflow: "dissolution" }), true,
  "chấm dứt hoạt động phải được ép");

// Thủ tục khác giữ nguyên logic đối chiếu tài khoản với chủ hộ.
assert.equal(forceSelfSubmitter({ businessDefaults: daNang, workflow: "change" }), false);
assert.equal(forceSelfSubmitter({ businessDefaults: daNang, workflow: "reissue" }), false);

// Tài khoản tỉnh khác (popup không gắn cờ) không đổi hành vi.
assert.equal(forceSelfSubmitter({ businessDefaults: null }), false);
assert.equal(forceSelfSubmitter({ businessDefaults: { businessActText: "..." } }), false);
assert.equal(forceSelfSubmitter(null), false);

const SELF = 'input[type="radio"][name="ctl00$C$PERS_SUBGroup"][value="IS_SIGNER_BUTTON"]';

(async () => {
  // Cổng đang tick "Người được ủy quyền" → phải bấm lại radio "Người có thẩm quyền ký".
  selectors.clear();
  clicked.length = 0;
  selectors.set(SELF, { id: "ctl00_C_PERS_SUBGroup_0", checked: false, click: () => clicked.push("self") });
  await tickSubmitterSelfRadio();
  assert.deepEqual(clicked, ["self"], "phải tick lại Người có thẩm quyền ký");

  // Đã đúng vai trò → không bấm (mỗi lần bấm là 1 postback AutoPostBack).
  selectors.clear();
  clicked.length = 0;
  selectors.set(SELF, { id: "ctl00_C_PERS_SUBGroup_0", checked: true, click: () => clicked.push("self") });
  await tickSubmitterSelfRadio();
  assert.deepEqual(clicked, [], "đang đúng vai trò thì không bấm thừa");

  // Không thấy radio (trang khác) → không nổ.
  selectors.clear();
  await tickSubmitterSelfRadio();

  // === Xung đột đã gặp: hồ sơ có CCCD chủ hộ + giấy đăng ký, tài khoản nộp KHÁC chủ hộ ===
  // Ép tick "Người có thẩm quyền ký" KHÔNG được kéo nhân thân/địa chỉ chủ hộ sang khối người nộp.
  const OWNER = { hoTen: "Phan Thị Cúc", soDinhDanh: "048301001234",
    diaChi: { quocGia: "Việt Nam", tinh: "Đà Nẵng", xa: "Phường Hải Châu", diaChi: "12 Bạch Đằng" } };
  const CLERK = { hoTen: "Nguyễn Duy Thái", soDinhDanh: "048999005678",
    diaChi: { quocGia: "Việt Nam", tinh: "Đà Nẵng", xa: "Phường Sơn Trà", diaChi: "99 Ngô Quyền" } };

  const st = {
    businessDefaults: daNang,
    pages: {
      "chu-ho-kinh-doanh": [
        { name: "ctl00$C$OWN_PCtl$PERSCtl$FULL_NAMEFld", value: OWNER.hoTen },
        { name: "ctl00$C$OWN_PCtl$PERSCtl$PERS_DOC_NOFld", value: OWNER.soDinhDanh },
      ],
      "nguoi-nop-ho-so": [
        { name: "__applicantAddress", value: { role: "self", self: OWNER.diaChi } },
        { name: "__identityCandidates", value: [OWNER, CLERK] },
      ],
    },
  };

  // Nút "Sao chép thông tin đăng ký tài khoản" vừa đổ nhân thân TÀI KHOẢN (người nộp) vào form.
  ids.clear();
  ids.set("ctl00_C_PERSCtl_FULL_NAMEFld", { value: CLERK.hoTen });
  ids.set("ctl00_C_PERSCtl_PERS_DOC_NOFld", { value: CLERK.soDinhDanh });

  const match = matchAccountWithOwner(st);
  assert.equal(match.isOwner, false, "tài khoản khác chủ hộ thì phải nhận ra là khác");
  assert.equal(match.ownerUnknown, false, "hồ sơ CÓ nhân thân chủ hộ để đối chiếu");

  const nopFields = st.pages["nguoi-nop-ho-so"];
  const backendAddr = [{ name: "ctl00$C$PERSCtl$ADDRCCtl$CITY_IDFld", comp: "dom-select", value: "Đà Nẵng" }];
  const chosen = submitterAddressFields(st, nopFields, backendAddr, CLERK, match.isOwner);
  const value = (suffix) => (chosen.find((f) => f.name.endsWith(suffix)) || {}).value;
  assert.equal(value("WARD_IDFld"), "Phường Sơn Trà", "phải lấy địa chỉ trên CCCD của người nộp");
  assert.equal(value("STREET_NUMBERFld"), "99 Ngô Quyền");
  assert.ok(!chosen.some((f) => String(f.value).includes("Bạch Đằng")),
    "KHÔNG được điền địa chỉ chủ hộ vào khối người nộp");

  // Không khớp được CCCD nào của người đăng nhập → thà để trống còn hơn ghi nhầm địa chỉ chủ hộ.
  assert.equal(submitterAddressFields(st, nopFields, backendAddr, null, false).length, 0,
    "không khớp CCCD nào thì phải để trống địa chỉ");

  // Chính là cơ chế sinh ra lỗi: chỉ nhìn radio (đang tick "Người có thẩm quyền ký" vì BỊ ÉP) thì
  // hàm tưởng tài khoản là chủ hộ và đổ địa chỉ chủ hộ sang khối người nộp. Nhánh không-ép vẫn phải
  // giữ hành vi này (ở đó radio là kết quả của chính phép đối chiếu nên suy theo radio là đúng).
  selectors.clear();
  selectors.set(SELF, { id: "ctl00_C_PERS_SUBGroup_0", checked: true, click: () => {} });
  const byRadioOnly = submitterAddressFields(st, nopFields, backendAddr, CLERK);
  assert.ok(byRadioOnly.some((f) => String(f.value).includes("Bạch Đằng")),
    "bỏ cờ isOwnerAccount thì hàm suy theo radio — đúng lỗi cũ, nên nhánh ép BẮT BUỘC phải truyền cờ");

  // Tài khoản ĐÚNG là chủ hộ → vẫn lấy địa chỉ trong đơn như cũ.
  const asOwner = submitterAddressFields(st, nopFields, backendAddr, null, true);
  assert.equal((asOwner.find((f) => f.name.endsWith("STREET_NUMBERFld")) || {}).value, "12 Bạch Đằng");

  console.log("business Đà Nẵng: vai trò người nộp luôn là Người có thẩm quyền ký passed");
})();
