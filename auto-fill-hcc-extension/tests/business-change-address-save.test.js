// Hồ sơ THAY ĐỔI hộ kinh doanh: trang "Địa chỉ" phải được LƯU kể cả khi cổng để nút Lưu disabled.
//
// Vì sao trang này luôn rơi vào thế đó ở lượt chạy sau cascade:
//   - ô "Số nhà" cố ý set value KHÔNG kèm sự kiện (tránh postback thừa),
//   - select địa danh sau postback đã đúng đích nên không bị chạm lại,
//   - ô không postback (điện thoại/email) chỉ điền ở lượt ĐẦU (filledStep).
// ⇒ cổng không thấy form "dirty" → nút Lưu vẫn disabled dù địa chỉ mới đã nằm đúng trên DOM.
// Trước đây engine bỏ qua Lưu trong đúng tình huống này nên hồ sơ đổi trụ sở trượt IM LẶNG.

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const DIA_CHI_FIELDS = [
  { name: "ctl00$C$ADDRCtl$COUNTRY_IDFld", comp: "dom-select", value: "Việt Nam" },
  { name: "ctl00$C$ADDRCtl$CITY_IDFld", comp: "dom-select", value: "Lâm Đồng" },
  { name: "ctl00$C$ADDRCtl$WARD_IDFld", comp: "dom-select", value: "Đơn Dương" },
  { name: "ctl00$C$ADDRCtl$STREET_NUMBERFld", comp: "dom-input", value: "Thửa đất số 533" },
  { name: "ctl00$C$DCONTClt$HO_PHONEFld", comp: "dom-input", value: "0339204115" },
];

function makeSaveButton(clicks, readPhase = () => "") {
  return {
    id: "ctl00_C_BtnSave",
    name: "ctl00$C$BtnSave",
    className: "save-btn",
    value: "Lưu",
    type: "submit",
    disabled: true,
    removeAttribute(attr) { if (attr === "disabled") this.disabled = false; },
    click() { clicks.push({ disabled: this.disabled, phase: readPhase() }); },
  };
}

/** Nạp engine trong sandbox tối thiểu; trả về __HCC__ + các mốc quan sát được. */
function loadEngine({ saveButtons }) {
  const stored = {};
  const sandbox = {
    console: { log() {}, warn() {}, info() {}, error() {} },
    Event,
    MouseEvent: class {},
    setTimeout,
    clearTimeout,
    Date,
    getComputedStyle: () => ({ display: "block", visibility: "visible" }),
    chrome: {
      runtime: {},
      storage: {
        local: {
          get(key, cb) { cb({ [key]: stored[key] }); },
          set(obj, cb) { Object.assign(stored, obj); cb && cb(); },
          remove(key, cb) { delete stored[key]; cb && cb(); },
        },
      },
    },
    document: {
      getElementById: () => null,
      querySelector: () => null,
      // findBusinessSaveButton() lọc mọi input[type=submit] có value "Lưu".
      querySelectorAll: (selector) => (selector === 'input[type="submit"]' ? saveButtons : []),
      forms: { namedItem: () => null },
      createElement: () => ({ remove() {} }),
      documentElement: { appendChild() {} },
    },
  };
  sandbox.window = {
    location: { pathname: "/HkdOnline/Forms/APP/DW_DOCUMENTEdit.aspx" },
    sessionStorage: { setItem() {}, getItem: () => null, removeItem() {} },
    addEventListener() {},
    removeEventListener() {},
    __HCC__: {
      sleep: async () => {},
      norm: (value) => String(value || "").trim().toLowerCase().replace(/\s+/g, " "),
      fieldCandidates: () => [],
      setNativeValue: () => {},
      waitFor: async () => false,
      readAcctContact: () => "",
      fillFormStandard: async () => ({ filled: 0 }),
      findStandardInput: () => null,
      findStandardSelect: () => null,
      // Cascade địa chỉ không chạy được trong sandbox không DOM; test này chỉ soi nhịp LƯU.
      isPostbackAddressField: () => false,
      setFillAllProgress: () => {},
      setRunProgressText: () => {},
      endFillAllUI: () => {},
      clearFillAllState: async () => {},
    },
  };

  const source = fs.readFileSync(
    path.join(__dirname, "..", "content", "procedures", "business-registration.js"),
    "utf8",
  );
  vm.runInNewContext(source, sandbox, { filename: "business-registration.js" });
  return sandbox.window.__HCC__;
}

function makeState(fields) {
  return {
    workflow: "change",
    order: ["dia-chi", "nguoi-nop-ho-so"],
    step: 0,
    // filledStep === step = lượt chạy LẠI sau postback của cascade: không ô nào được điền lại nữa,
    // đúng lúc cổng để nút Lưu disabled.
    filledStep: 0,
    phase: "fill",
    pages: { "dia-chi": fields },
  };
}

(async () => {
  // ── 1. Có field địa chỉ + nút Lưu disabled → vẫn phải bấm Lưu ───────────────────────────────
  {
    const clicks = [];
    const st = makeState(DIA_CHI_FIELDS);
    const H = loadEngine({ saveButtons: [makeSaveButton(clicks, () => st.phase)] });
    assert.equal(typeof H.handleAddressCascadePage, "function",
      "Phải export handleAddressCascadePage để kiểm được nhịp Lưu");

    await H.handleAddressCascadePage(st, "dia-chi");

    assert.equal(clicks.length, 1, "Nút Lưu disabled vẫn phải được bấm — bỏ qua là mất địa chỉ mới");
    assert.equal(clicks[0].disabled, false, "Phải gỡ disabled trước khi bấm, không bấm vào nút còn khoá");
    assert.equal(clicks[0].phase, "saving",
      "Phải persist pha saving TRƯỚC khi bấm, nếu không postback của nút Lưu sẽ làm mất dấu bước đang chạy");
  }

  // ── 2. Trang không có field nào → KHÔNG tự bật nút và KHÔNG bấm Lưu ─────────────────────────
  {
    const clicks = [];
    const H = loadEngine({ saveButtons: [makeSaveButton(clicks)] });
    const st = makeState([]);
    await H.handleAddressCascadePage(st, "dia-chi");

    assert.equal(clicks.length, 0, "Không có gì để lưu thì không được bấm Lưu (tránh submit form rỗng)");
    assert.equal(st.step, 1, "Phải sang trang kế");
  }

  // ── 3. Nút Lưu đã bật sẵn → giữ nguyên hành vi cũ ───────────────────────────────────────────
  {
    const clicks = [];
    const btn = makeSaveButton(clicks);
    btn.disabled = false;
    const H = loadEngine({ saveButtons: [btn] });
    const st = makeState(DIA_CHI_FIELDS);
    await H.handleAddressCascadePage(st, "dia-chi");

    assert.equal(clicks.length, 1, "Nút đã bật thì vẫn bấm Lưu như cũ");
  }

  console.log("business change address save: lưu được cả khi cổng để nút Lưu disabled passed");
  process.exit(0);
})();
