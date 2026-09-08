// Trang "Thông tin về thuế" (cổng HkdOnline, thủ tục đăng ký kinh doanh).
// Lỗi thật: tick "Giống địa chỉ trụ sở chính" rồi Lưu thì cổng ẩn khối địa chỉ đi nhưng KHÔNG chép
// địa chỉ trụ sở vào — hồ sơ đi với khối thuế rỗng. Đảo radio ngay trong lượt điền cũng hỏng: tick
// "Địa chỉ khác" là cổng reset khối địa chỉ về mặc định (Phường/Xã + Số nhà TRỐNG).
// Cách chạy được: xong hết các trang (kể cả người nộp hồ sơ) thì QUAY LẠI trang thuế, tick "Địa chỉ
// khác" — không điền gì — rồi tick lại "Giống địa chỉ trụ sở chính", Lưu, mới sang đính kèm.
// Test khoá đúng trình tự đó.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const TAX_MODE_FIELD = "ctl00$C$UC_DW_TAXEditCtl$REP_RECV_ADDR_TYPEFld";

// State machine của trang chuyển nhịp bằng `return void handleX(st)` (không await) để sống qua
// postback, nên test phải CHỜ nhịp chạy xong thay vì assert ngay sau lời gọi.
function waitUntil(cond, timeout = 2000) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeout;
    const tick = () => {
      if (cond()) return resolve();
      if (Date.now() > deadline) return reject(new Error("hết giờ chờ state machine"));
      setTimeout(tick, 10);
    };
    tick();
  });
}

function makeHarness() {
  const calls = { radio: [], filled: [], saves: 0 };
  const leaveHandlers = [];
  const saveButton = {
    id: "ctl00_C_btnSave", name: "ctl00$C$btnSave", className: "save-btn",
    value: "Lưu", type: "submit", disabled: false,
    click() { calls.saves += 1; leaveHandlers.splice(0).forEach((fn) => fn()); },
  };
  const sandbox = {
    console: { log() {}, warn() {}, error() {} },
    setTimeout,
    clearTimeout,
    Event,
    chrome: {
      runtime: {},
      storage: { local: { get(_k, cb) { cb && cb({}); }, set(_v, cb) { cb && cb(); }, remove() {} } },
    },
    document: {
      getElementById: () => null,
      querySelector: () => null,
      querySelectorAll: (sel) => (sel === 'input[type="submit"]' ? [saveButton] : []),
      forms: { namedItem: () => null },
      createElement: () => ({ remove() {} }),
    },
  };
  sandbox.window = {
    location: { pathname: "/HkdOnline/Forms/APP/Registration.aspx" },
    sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    addEventListener(type, fn) { if (type === "beforeunload" || type === "pagehide") leaveHandlers.push(fn); },
    removeEventListener() {},
    __HCC__: {
      sleep: async () => {},
      norm: (v) => String(v || "").trim().toLowerCase().replace(/\s+/g, " "),
      fieldCandidates: (f) => [f.name],
      setNativeValue: () => {},
      waitFor: async () => false,
      readAcctContact: () => "",
      findStandardInput: () => null,
      findStandardSelect: () => null,
      isPostbackAddressField: (f) => /ADDRCtl/.test(f.name || ""),
      fillFormStandard: async (fields) => {
        for (const f of fields) {
          if (f.name === TAX_MODE_FIELD) calls.radio.push(String(f.value));
          else calls.filled.push(f.name);
        }
      },
      setFillAllProgress() {},
      endFillAllUI() {},
      setRunProgressText() {},
    },
  };
  const source = fs.readFileSync(
    path.join(__dirname, "..", "content", "procedures", "business-registration.js"), "utf8");
  vm.runInNewContext(source, sandbox, { filename: "business-registration.js" });
  return { H: sandbox.window.__HCC__, calls };
}

const sameAddressPage = [
  // "1" = Giống địa chỉ trụ sở chính (giá trị backend gửi ở pipeline dang_ky_kinh_doanh).
  { name: TAX_MODE_FIELD, comp: "dom-radio", value: "1" },
  { name: "ctl00$C$UC_DW_TAXEditCtl$TOTAL_OF_LABORSFld", comp: "dom-input", value: "3" },
];

// ---------------------------------------------------------------- 1. nhận diện nhánh "giống trụ sở"
{
  const { H } = makeHarness();
  const modeField = (value) => ({ name: TAX_MODE_FIELD, comp: "dom-radio", value });
  assert.equal(H.taxWantsSameAsHeadOffice([modeField("1")]), true);
  assert.equal(H.taxWantsSameAsHeadOffice([modeField("0")]), false,
    '"Địa chỉ khác" đã điền cascade tay → KHÔNG cần lượt chốt');
  assert.equal(H.taxWantsSameAsHeadOffice([]), false);
  // Chỉ được nhìn đúng radio địa chỉ thuế: "Số lượng lao động" = 1 mà tính là "giống trụ sở" thì
  // mọi hồ sơ đều bị chèn thêm một lượt Lưu thừa ở cuối.
  assert.equal(
    H.taxWantsSameAsHeadOffice([{ name: "ctl00$C$UC_DW_TAXEditCtl$TOTAL_OF_LABORSFld", value: "1" }]),
    false, "field khác mang value 1 KHÔNG phải radio địa chỉ thuế");
}

// ---------------------------------------------------------------- 2. lượt điền thường: Lưu MỘT lần
{
  const { H, calls } = makeHarness();
  const st = {
    step: 6,
    order: ["thong-tin-ve-thue", "nguoi-nop-ho-so", "thong-tin-ve-thue"],
    pages: { "thong-tin-ve-thue": sameAddressPage },
  };
  (async () => {
    await H.handleTaxPage(st);
    await waitUntil(() => calls.saves >= 1);
    assert.equal(calls.radio.join(","), "1", "lượt điền chỉ tick đúng lựa chọn backend kê, không đảo");
    assert.equal(calls.saves, 1, "và Lưu một lần như cũ");
    assert.equal(st.phase, "saving");
  })();
}

// ---------------------------------------------------------------- 3. lượt CHỐT ở cuối order
const { H, calls } = makeHarness();
const st = {
  // Bước cuối cùng của order, trùng key với bước 0 → đây là lượt chốt.
  step: 2,
  order: ["thong-tin-ve-thue", "nguoi-nop-ho-so", "thong-tin-ve-thue"],
  pages: { "thong-tin-ve-thue": sameAddressPage },
};

(async () => {
  await H.handleTaxPage(st);
  await waitUntil(() => calls.saves >= 1);
  assert.equal(calls.radio.join(","), "0,1",
    'lượt chốt: tick "Địa chỉ khác" rồi tick LẠI "Giống địa chỉ trụ sở chính"');
  assert.equal(calls.filled.join(","), "",
    "KHÔNG điền lại field nào ở lượt chốt — khối địa chỉ lúc tick Khác đang rỗng, điền vào là hỏng");
  assert.equal(calls.saves, 1, "rồi Lưu");
  assert.equal(st.phase, "saving", "Lưu xong mới được sang bước kế (đính kèm)");

  console.log("OK business-tax-address-same-retoggle");
})();

// ---------------------------------------------------------------- 4. order phải có lượt chốt
// Nhịp chốt chỉ chạy khi content.js xếp thêm một bước "thong-tin-ve-thue" ở CUỐI order. Không có
// bước đó thì handleTaxPage không bao giờ vào nhánh chốt và lỗi quay lại y như cũ.
{
  const contentSource = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");
  const start = contentSource.indexOf("  function withFinalTaxPass(order, pages) {");
  const end = contentSource.indexOf("  // readAcctContact:", start);
  assert.ok(start >= 0 && end > start, "Không tách được withFinalTaxPass khỏi content.js");

  const { H } = makeHarness();
  const box = { H };
  vm.runInNewContext(`${contentSource.slice(start, end)}
    globalThis.withFinalTaxPass = withFinalTaxPass;`, box);

  const base = ["dia-chi", "thong-tin-ve-thue", "nguoi-nop-ho-so"];
  assert.equal(
    box.withFinalTaxPass([...base], { "thong-tin-ve-thue": sameAddressPage }).join(","),
    "dia-chi,thong-tin-ve-thue,nguoi-nop-ho-so,thong-tin-ve-thue",
    "lượt chốt phải nằm SAU trang người nộp hồ sơ, ngay trước đính kèm");

  const otherAddressPage = [{ name: TAX_MODE_FIELD, comp: "dom-radio", value: "0" }];
  assert.equal(
    box.withFinalTaxPass([...base], { "thong-tin-ve-thue": otherAddressPage }).join(","),
    base.join(","), '"Địa chỉ khác" không được chèn lượt Lưu thừa');
  assert.equal(
    box.withFinalTaxPass(["nguoi-nop-ho-so"], { "thong-tin-ve-thue": sameAddressPage }).join(","),
    "nguoi-nop-ho-so", "luồng không đi qua trang thuế thì giữ nguyên order");
}
