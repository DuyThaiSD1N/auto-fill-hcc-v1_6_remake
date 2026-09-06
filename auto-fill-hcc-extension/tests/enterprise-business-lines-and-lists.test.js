// Hồ sơ thật (CÔNG TY TNHH DỊCH VỤ VẬN TẢI THƯƠNG HUYỀN NHI) trên dangkyquamang.dkkd.gov.vn ra kết
// quả thiếu ở ba mục. Test khoá lại phần engine chịu trách nhiệm:
//  1. Ngành nghề: 11 mã trong Điều lệ nhưng bảng trên cổng chỉ có 1 dòng — engine doanh nghiệp
//     trước đây KHÔNG có vòng lặp thêm mã (chỉ gõ ô mã rồi bấm Lưu).
//  2/3. Thành viên + Người đại diện theo pháp luật: backend trả KHOÁ cho trang nhưng mảng RỖNG;
//     engine vẫn bấm "Tạo mới" rồi mở form trống, đánh dấu xong, không cảnh báo gì.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const enterpriseSource = fs.readFileSync(
  path.join(__dirname, "..", "content", "procedures", "enterprise-registration.js"), "utf8");
const businessSource = fs.readFileSync(
  path.join(__dirname, "..", "content", "procedures", "business-registration.js"), "utf8");

// ---------------------------------------------------------------- 1. pageHasData / runSummary
// Hai hàm này thuần dữ liệu nên tách ra chạy thẳng, không cần dựng cả DOM của cổng.
const specStart = enterpriseSource.indexOf("  const PAGE_SPEC = {");
const specEnd = enterpriseSource.indexOf("\n  const MAX_PAGE_RETRIES", specStart);
const hasDataStart = enterpriseSource.indexOf("  function pageHasData(pages, key) {");
const hasDataEnd = enterpriseSource.indexOf("\n  /** Trang danh sách mà hồ sơ không có dữ liệu", hasDataStart);
assert.ok(specStart >= 0 && specEnd > specStart, "Không tách được PAGE_SPEC");
assert.ok(hasDataStart >= 0 && hasDataEnd > hasDataStart, "Không tách được pageHasData/runSummary");

const box = { console: { log() {}, warn() {} } };
vm.runInNewContext(`
  const ADD_BUTTON_SELECTORS = [];
  ${enterpriseSource.slice(specStart, specEnd)}
  ${enterpriseSource.slice(hasDataStart, hasDataEnd)}
  globalThis.pageHasData = pageHasData;
  globalThis.runSummary = runSummary;
  globalThis.PAGE_SPEC = PAGE_SPEC;
`, box);

const pagesThieu = {
  "nganh-nghe-kinh-doanh": [
    { name: "__businessLines", comp: "raw",
      value: { codes: ["4933", "5224", "4661", "5229", "7710", "4781", "4782", "5210", "4932", "9531", "9532"], main: "4933", items: [] } },
    { name: "ctl00$C$newBusinessLineCode", comp: "dom-input", value: "4933" },
  ],
  // Đúng cảnh trên cổng thật: chỉ ra được 1 trong 2 thành viên...
  "thong-tin-thanh-vien": [{ name: "__members", comp: "raw", value: [{ fullName: "LÊ TỰ SANG" }] }],
  // ...và không ra người đại diện theo pháp luật (backend vẫn trả khoá, mảng rỗng).
  "nguoi-dai-dien-phap-luat": [],
};

assert.equal(box.pageHasData(pagesThieu, "nguoi-dai-dien-phap-luat"), false,
  "Mảng rỗng KHÔNG được coi là có dữ liệu — nếu không engine mở form trống rồi tạo bản ghi rỗng");
assert.equal(box.pageHasData(pagesThieu, "thong-tin-thanh-vien"), true);
assert.equal(box.pageHasData({ "thong-tin-thanh-vien": [{ name: "__members", value: [] }] }, "thong-tin-thanh-vien"),
  false, "Trang thành viên chỉ có __members rỗng thì cũng là KHÔNG có dữ liệu");
assert.equal(box.pageHasData(pagesThieu, "thong-tin-ve-thue"), false, "Trang backend không trả = không có dữ liệu");

const summary = box.runSummary(pagesThieu);
assert.equal(summary.businessLines, 11, "Phải đếm đủ 11 mã ngành để cán bộ đối chiếu với Điều lệ");
assert.equal(summary.members, 1, "Phải nói rõ chỉ đọc được 1 thành viên");
assert.equal(summary.hasLegalRep, false);
// Array dựng trong vm là realm khác nên so bằng deepStrictEqual sẽ trượt ở prototype -> so chuỗi.
assert.equal(Array.from(summary.emptyPages).join(","), "nguoi-dai-dien-phap-luat",
  "Trang có khoá nhưng rỗng phải được nêu tên, đó chính là mục ra 'Danh sách trống!'");

// ---------------------------------------------------------------- 2. Vòng lặp thêm mã ngành
// Trang ngành nghề PHẢI đi nhánh riêng: nhánh điền chung chỉ gõ được ô mã rồi bấm Lưu = 0 ngành.
assert.match(enterpriseSource,
  /if \(onPage === "nganh-nghe-kinh-doanh"\) return void await stepBusinessLines\(state\);/,
  "stepFillOnce phải rẽ trang ngành nghề sang vòng lặp thêm mã");
for (const call of ["ops.addOneCode(code)", "ops.setMainAndUpdate(plan.main)", "ops.fillDescriptions(plan"]) {
  assert.ok(enterpriseSource.includes(call), `Vòng lặp ngành nghề thiếu bước: ${call}`);
}
// Ô mã là ô nhập tạm của vòng lặp; để nhánh điền chung ghi vào đó là bỏ lại một mã lơ lửng trên form.
assert.ok(enterpriseSource.includes('name !== "ctl00$C$newBusinessLineCode"'),
  "Phần điền tĩnh của trang ngành nghề phải loại ô mã ngành ra");

// ---------------------------------------------------------------- 3. Thao tác DOM dùng chung
// Engine hộ kinh doanh phải XUẤT bộ thao tác ngành nghề, và các selector phải nhận CẢ HAI kiểu
// ClientID: HkdOnline sinh "ctl00_C_X", cổng doanh nghiệp sinh "C_X".
for (const key of ["getAddedCodes", "addOneCode", "isMainSet", "setMainAndUpdate", "fillDescriptions"]) {
  assert.ok(new RegExp(`${key}:`).test(businessSource), `H.businessLineOps thiếu ${key}`);
}
assert.ok(businessSource.includes('"#ctl00_C_CtlList tr, #C_CtlList tr"'),
  "Bảng ngành nghề phải khớp cả ClientID ngắn của cổng doanh nghiệp");
assert.ok(!/querySelectorAll\("#ctl00_C_CtlList tr"\)/.test(businessSource),
  "Không được còn chỗ nào chỉ khớp mỗi ClientID dài");

// Nút "Thêm" dò theo nhãn phải khớp ĐÚNG HỆT: khớp kiểu "chứa" sẽ vơ luôn nút
// "Thêm/xóa ngành nghề trong danh sách" nằm ngay cạnh trên cùng trang.
const addBtnStart = businessSource.indexOf("function findBusinessButtonByExactLabel(labels)");
const addBtnEnd = businessSource.indexOf("\n  function addOneBusinessCode", addBtnStart);
assert.ok(addBtnStart >= 0 && addBtnEnd > addBtnStart, "Không tách được findBusinessButtonByExactLabel");
const buttons = [
  { value: "Thêm/xóa ngành nghề trong danh sách", disabled: false },
  { value: "Thêm ngành nghề bằng mã số", disabled: false },
];
const btnBox = {
  console: { log() {}, warn() {} },
  foldBusinessPageText: (v) => String(v || "").trim().toLowerCase().replace(/\s+/g, " "),
  document: { querySelectorAll: () => buttons },
};
vm.runInNewContext(`
  ${businessSource.slice(addBtnStart, addBtnEnd)}
  globalThis.findAdd = findBusinessAddLineButton;
`, Object.assign(btnBox, { document: { querySelector: () => null, querySelectorAll: () => buttons } }));
assert.equal(btnBox.findAdd().value, "Thêm ngành nghề bằng mã số",
  "Phải bắt đúng nút thêm mã, không được vơ nút Thêm/xóa danh sách");

console.log("ok - ngành nghề lặp thêm mã + trang danh sách rỗng được cảnh báo");

// ---------------------------------------------------------------- 4. Vòng lặp PHẢI luôn tiến tới
// Trên cổng thật engine chỉ thêm được 1 mã rồi dừng. Nguyên nhân: bảng kết quả của cổng doanh nghiệp
// nằm trong <div id="C_PnlListResult">, không mang id CtlList — đọc hụt bảng thì mã vừa thêm vẫn bị
// coi là "chưa có", nó mãi đứng đầu hàng đợi và tiêu hết lượt của cả trang.
// Test dựng lại đúng cảnh xấu nhất đó: getAddedCodes() LUÔN trả rỗng. Yêu cầu: mọi mã đều phải được
// thử, không được dồn hết lượt vào mã đầu.
const loopStart = enterpriseSource.indexOf("  async function stepBusinessLines(state) {");
const loopEnd = enterpriseSource.indexOf("\n  /** Danh sách thành viên backend gửi kèm", loopStart);
assert.ok(loopStart >= 0 && loopEnd > loopStart, "Không tách được stepBusinessLines");

const attempts = [];
const loopBox = {
  console: { log() {}, warn() {} },
  PAGE_SPEC: { "nganh-nghe-kinh-doanh": { label: "Ngành nghề kinh doanh", save: "x" } },
  progress() {},
  toast() {},
  setFillState: async () => {},
  scheduleStepFill() {},
  clickSaveDetectReload: async () => false,
  sleep: async () => {},
  saveBusinessLinePage: async () => { loopBox.saved = true; },
  businessLinePlan: () => ({ codes: ["4933", "5224", "4661"], main: "4933", items: [] }),
  H: {
    businessLineOps: {
      getAddedCodes: () => [],            // cảnh xấu nhất: không đọc được dòng nào trong bảng
      // TRẢ TRUE = cổng postback tải lại trang, đúng như thật. Đây là chỗ mấu chốt: khi có postback,
      // nhánh "không thêm được thì bỏ qua mã" KHÔNG chạy, nên mã hỏng chỉ bị loại nhờ đếm lượt.
      addOneCode: async (code) => { attempts.push(code); return true; },
      isMainSet: () => true,
      setMainAndUpdate: async () => false,
      fillDescriptions: () => 0,
      findUpdateButton: () => null,
    },
  },
};
vm.runInNewContext(`
  ${enterpriseSource.slice(loopStart, loopEnd)}
  globalThis.step = stepBusinessLines;
`, loopBox);

(async () => {
  const state = { pages: {}, done: [] };
  // Mỗi vòng lặp = một lần cổng tải lại trang sau postback; state sống qua các lần đó (chrome.storage).
  for (let i = 0; i < 20 && !loopBox.saved; i += 1) await loopBox.step(state);

  assert.ok(attempts.includes("5224") && attempts.includes("4661"),
    `Mã thứ 2 và 3 phải được thử, không được dồn hết lượt vào mã đầu. Đã thử: ${attempts.join(",")}`);
  const firstCodeAttempts = attempts.filter((c) => c === "4933").length;
  assert.ok(firstCodeAttempts <= 2,
    `Mã đầu chỉ được thử tối đa 2 lượt rồi phải nhường mã sau, thực tế ${firstCodeAttempts}`);
  assert.ok(loopBox.saved, "Vòng lặp phải kết thúc được (chuyển sang lưu trang), không treo");

  console.log("ok - vòng lặp ngành nghề luôn tiến tới mã kế dù không đọc được bảng");
})();
