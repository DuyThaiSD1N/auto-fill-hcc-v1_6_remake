// Vòng lặp DANH SÁCH THÀNH VIÊN của thủ tục TNHH hai thành viên trở lên.
//
// Lỗi trên cổng thật: sau khi bấm Lưu ở form chi tiết, cổng KHÔNG tự quay ra trang danh sách mà giữ
// nguyên form vừa lưu. Engine cũ hễ thấy form chi tiết là điền người kế tiếp -> người sau bị điền
// ĐÈ lên form của người trước, danh sách ra bản ghi trùng ("lặp lại 2 người").
//
// Hợp đồng mới: mỗi người ĐÚNG MỘT lượt điền -> Lưu -> bấm "Trở về" -> danh sách -> người kế; hết
// người thì chuyển mục. Test dựng lại vòng đời đó bằng một cổng giả có đủ hai trang.
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// File nguồn xuống dòng lẫn CRLF/LF -> chuẩn hoá trước khi cắt, nếu không marker nhiều dòng trượt.
const source = fs.readFileSync(
  path.join(__dirname, "..", "content", "procedures", "enterprise-registration.js"), "utf8")
  .split(String.fromCharCode(13)).join("");

/**
 * Bất biến của cả luồng: MỖI lần "Lưu" phải đứng ngay sau một lần "Tạo mới".
 * Hai lần "Lưu" liền nhau nghĩa là người thứ hai bị điền lên form của người thứ nhất — đúng cái lỗi
 * "lặp lại 2 người". Đây là thứ phải kiểm, không phải chỉ đếm số dòng cổng nhận được.
 */
function assertEachSaveOnFreshForm(log) {
  log.forEach((action, i) => {
    if (action !== "Lưu") return;
    assert.strictEqual(log[i - 1], "Tạo mới",
      `Lần Lưu thứ ${i} không nằm trên form vừa mở mới (trước nó là "${log[i - 1]}"): ${log.join(" > ")}`);
  });
}

function sliceFn(name, endMarker) {
  const start = source.indexOf(`  async function ${name}(state`);
  assert.ok(start >= 0, `không tách được ${name}`);
  const end = source.indexOf(endMarker, start);
  assert.ok(end > start, `không tìm được mốc kết thúc của ${name}`);
  return source.slice(start, end);
}

const MEMBERS = [
  { fullName: "LÊ TỰ SANG", fields: [{ name: "a", value: "1" }] },
  { fullName: "TRẦN THỊ HOÀI THƯƠNG", fields: [{ name: "a", value: "2" }] },
];

// ---- cổng giả: hai trang (danh sách / form chi tiết) + các nút thật của cổng ----
function makePortal() {
  return {
    page: "listing",
    savedRows: [],      // danh sách thành viên cổng đang giữ
    openForm: null,     // dữ liệu đang gõ trên form chi tiết
    log: [],
    clickNew() { this.page = "detail"; this.openForm = null; this.log.push("Tạo mới"); return true; },
    fill(value) { this.openForm = value; },
    clickSave() {
      this.log.push("Lưu");
      // ĐÚNG HÀNH VI CỔNG THẬT: lưu xong VẪN đứng ở form chi tiết, không tự quay ra danh sách.
      this.savedRows.push(this.openForm);
      return true;
    },
    clickBack() { this.page = "listing"; this.openForm = null; this.log.push("Trở về"); return true; },
  };
}

function runLoop(portal, { hasBackButton = true } = {}) {
  const box = {
    console: { log() {}, warn() {} },
    PAGE_SPEC: { "thong-tin-thanh-vien": { label: "Thông tin về thành viên", save: "x" } },
    MAX_FILL_TRIES: 3,
    progress() {},
    toast(message) { box.toasts.push(message); },
    toasts: [],
    sleep: async () => {},
    setFillState: async () => {},
    scheduleStepFill() {},
    skipEmptyListPage: async () => { box.skippedEmpty = true; },
    memberList: () => MEMBERS,
    findAddButton: () => ({ click: () => portal.clickNew() }),
    findBackButton: () => (hasBackButton ? { click: () => portal.clickBack() } : null),
    findMenuLink: () => (hasBackButton ? null : { menu: true }),
    openMenuLink: () => portal.clickBack(),
    buttonText: () => "",
    waitForSaveButton: async () => ({ click: () => portal.clickSave() }),
    // Điền = ghi thẳng giá trị người đang điền vào form đang mở của cổng.
    H: { fillFormStandard: async (fields) => portal.fill(fields[0].value) },
    clickSaveDetectReload: async (btn) => btn.click(),
  };
  vm.runInNewContext(`
    ${sliceFn("skipMemberPage", "\n  /** Trang DANH SÁCH")}
    ${sliceFn("stepMemberListing", "\n  /**\n   * Rời form chi tiết")}
    ${sliceFn("leaveMemberDetail", "\n  /**\n   * FORM CHI TIẾT")}
    ${sliceFn("stepMemberDetail", "\n  function progress(")}
    globalThis.listing = stepMemberListing;
    globalThis.detail = stepMemberDetail;
  `, box);
  return box;
}

// ---------------------------------------------------------------- 1. Hai người, không trùng ai
(async () => {
  const portal = makePortal();
  const box = runLoop(portal);
  const state = { pages: { "thong-tin-thanh-vien": [] }, done: [], fillTries: {}, order: ["thong-tin-thanh-vien"], memberIndex: 0 };

  // Mỗi vòng = một lần cổng tải lại trang; engine chọn nhánh theo trang đang đứng, y như stepFillOnce.
  for (let i = 0; i < 20 && !state.done.includes("thong-tin-thanh-vien"); i += 1) {
    if (portal.page === "detail") await box.detail(state);
    else await box.listing(state);
  }

  assert.deepStrictEqual(portal.savedRows, ["1", "2"],
    `Mỗi người phải được lưu ĐÚNG MỘT lần, không trùng. Cổng nhận: ${JSON.stringify(portal.savedRows)}`);
  assert.deepStrictEqual(portal.log,
    ["Tạo mới", "Lưu", "Trở về", "Tạo mới", "Lưu", "Trở về"],
    `Sai trình tự thao tác: ${portal.log.join(" > ")}`);
  assert.ok(state.done.includes("thong-tin-thanh-vien"), "Hết người thì phải đánh dấu xong mục để sang bước kế");
  console.log("ok - 2 thành viên: điền 1 người > Lưu > Trở về > người kế, không trùng");
})();

// ---------------------------------------------------------------- 2. KHÔNG được điền lại một người
// Chốt riêng cái lỗi đã gặp: nếu engine điền tiếp khi form cũ còn mở thì savedRows sẽ có bản ghi
// mang dữ liệu người sau ghi đè, hoặc số dòng nhiều hơn số người.
(async () => {
  const portal = makePortal();
  const box = runLoop(portal);
  const state = { pages: { "thong-tin-thanh-vien": [] }, done: [], fillTries: {}, order: ["thong-tin-thanh-vien"], memberIndex: 0 };
  for (let i = 0; i < 20 && !state.done.includes("thong-tin-thanh-vien"); i += 1) {
    if (portal.page === "detail") await box.detail(state);
    else await box.listing(state);
  }
  assert.strictEqual(portal.savedRows.length, MEMBERS.length,
    `Số dòng cổng nhận (${portal.savedRows.length}) phải bằng đúng số người trong hồ sơ (${MEMBERS.length})`);
  assert.strictEqual(portal.log.filter((x) => x === "Lưu").length, MEMBERS.length,
    "Số lần bấm Lưu phải bằng đúng số người — bấm dư là đang đẻ bản ghi trùng");
  assertEachSaveOnFreshForm(portal.log);
  console.log("ok - không có người nào bị điền/lưu hai lần");
})();

// ---------------------------------------------------------------- 3. Thiếu nút Trở về vẫn phải thoát
// Cổng đổi giao diện, mất nút Trở về: engine phải quay ra danh sách bằng mục menu, TUYỆT ĐỐI không
// được điền người kế lên form đang mở.
(async () => {
  const portal = makePortal();
  const box = runLoop(portal, { hasBackButton: false });
  const state = { pages: { "thong-tin-thanh-vien": [] }, done: [], fillTries: {}, order: ["thong-tin-thanh-vien"], memberIndex: 0 };
  for (let i = 0; i < 20 && !state.done.includes("thong-tin-thanh-vien"); i += 1) {
    if (portal.page === "detail") await box.detail(state);
    else await box.listing(state);
  }
  assert.deepStrictEqual(portal.savedRows, ["1", "2"],
    `Mất nút Trở về vẫn phải lưu đúng 2 người khác nhau, nhận: ${JSON.stringify(portal.savedRows)}`);
  // Điểm mấu chốt của nhánh này: KHÔNG được điền người kế lên form đang mở, phải rời trang trước.
  assertEachSaveOnFreshForm(portal.log);
  console.log("ok - mất nút Trở về thì quay ra danh sách bằng mục menu, vẫn không trùng");
})();
