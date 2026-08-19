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
const { forceSelfSubmitter, tickSubmitterSelfRadio } = sandbox.window.__HCC__;

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

  console.log("business Đà Nẵng: vai trò người nộp luôn là Người có thẩm quyền ký passed");
})();
