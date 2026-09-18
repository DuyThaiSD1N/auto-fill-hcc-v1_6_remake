// Khối địa chỉ liên thông khai sinh: bỏ dở ô Tỉnh/Phường-Xã mà KHÔNG dọn dẹp thì cán bộ không
// chọn tay được nữa — panel dropdown còn mở phủ lên form, chữ ta gõ còn nằm trong ô lọc nên danh
// sách mở ra rỗng ("treo, không bấm vào chọn hẳn tỉnh và phường/xã"). Bài kiểm chốt hành vi dọn
// dẹp: trả lại chữ cũ của cổng, bắn Escape, blur, đóng overlay.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-angular.js"), "utf8");

// --- Hợp đồng nguồn -----------------------------------------------------------------------------
// Cả ba đường bỏ dở (autocomplete, ng-select, mat-select) đều phải đi qua một chỗ dọn dẹp.
assert.match(source, /async function ngAbortCombobox\(input, restore = ""\) \{/);
assert.match(source, /await ngAbortCombobox\(input, before\);/, "autocomplete trượt phải trả lại chữ cũ");
assert.match(source, /await ngAbortCombobox\(ng\.querySelector\("input\[type=text\]"\)\);/,
  "ng-select không commit được cũng phải dọn");
assert.match(source, /await ngAbortCombobox\(null\);/, "mat-select không khớp phải đóng overlay");
// Chưa chọn được Tỉnh thì KHÔNG gõ vào ô Xã (danh sách xã chưa bao giờ nạp).
assert.match(source, /if \(data\.xa && \(tinhOk \|\| !data\.tinh\)\) \{/);
// Ô là ng-select thì đi đường fillNgSelect (có verify commit) thay vì coi mọi thứ là autocomplete.
assert.match(source, /const host = input\.closest\("ng-select"\);/);

// --- Chạy thật phần dọn dẹp ---------------------------------------------------------------------
const start = source.indexOf("async function ngAbortCombobox(input, restore = \"\") {");
const end = source.indexOf("// Chọn một cấp địa bàn", start);
assert.ok(start >= 0 && end > start, "Không tách được khối dọn dẹp combobox");

function makeEnv({ optionTexts = [], hasBackdrop = false, hasNgPanel = false } = {}) {
  const log = [];
  const input = {
    value: "",
    focus() { log.push(["input", "focus"]); },
    blur() { log.push(["input", "blur"]); },
    dispatchEvent(e) { log.push(["input", e.type, e.key || ""]); return true; },
  };
  const options = optionTexts.map((textContent) => ({
    textContent,
    dispatchEvent(e) { log.push(["option:" + textContent, e.type]); return true; },
    click() { log.push(["option:" + textContent, "click"]); },
  }));
  const backdrop = { click() { log.push(["backdrop", "click"]); } };
  const document = {
    body: { dispatchEvent(e) { log.push(["body", e.type]); return true; } },
    querySelectorAll(sel) {
      if (sel.includes("cdk-overlay-backdrop")) return hasBackdrop ? [backdrop] : [];
      if (sel.includes("mat-option")) return options;
      return [];
    },
    querySelector(sel) {
      if (sel === "ng-dropdown-panel") return hasNgPanel ? {} : null;
      return null;
    },
  };
  const sandbox = {
    document,
    console: { warn() { }, log() { } },
    KeyboardEvent: class { constructor(type, init) { Object.assign(this, init); this.type = type; } },
    MouseEvent: class { constructor(type) { this.type = type; } },
    Event: class { constructor(type) { this.type = type; } },
    sleep: () => Promise.resolve(),
    norm: (v) => String(v || "").trim().toLowerCase(),
    setNativeValue: (el, v) => { el.value = String(v ?? ""); log.push(["input", "setValue:" + el.value]); },
    waitFor: async (fn, _timeout) => fn() || null,
    panelOptions: () => [],
  };
  sandbox.globalThis = sandbox;
  vm.runInNewContext(`
    ${source.slice(start, end)}
    globalThis.api = { ngAbortCombobox, ngPickAutocomplete };
  `, sandbox);
  return { api: sandbox.api, input, log };
}

(async () => {
  // 1. Option không khớp: ô phải sạch chữ ta gõ, có Escape + blur, overlay bị đóng.
  const miss = makeEnv({ optionTexts: ["Tỉnh Lào Cai", "Tỉnh Lai Châu"], hasBackdrop: true, hasNgPanel: true });
  assert.equal(await miss.api.ngPickAutocomplete(miss.input, "Tỉnh Không Có"), false);
  assert.equal(miss.input.value, "", "chữ đã gõ phải được xoá, nếu không danh sách mở ra sẽ rỗng");
  assert.ok(miss.log.some(([who, type, key]) => who === "input" && type === "keydown" && key === "Escape"));
  assert.ok(miss.log.some(([who, type]) => who === "input" && type === "blur"));
  assert.ok(miss.log.some(([who, type]) => who === "backdrop" && type === "click"), "phải đóng overlay mat-*");
  assert.ok(miss.log.some(([who, type]) => who === "body" && type === "click"), "ng-select đóng bằng click ra ngoài");

  // 2. Cổng đã đổ sẵn tỉnh (VNeID) mà giá trị ta cần không có trong danh sách → KHÔNG được xoá
  //    trắng dữ liệu đúng của cổng, phải trả lại nguyên văn.
  const keep = makeEnv({ optionTexts: ["Tỉnh Lào Cai"] });
  keep.input.value = "Thành phố Hà Nội";
  assert.equal(await keep.api.ngPickAutocomplete(keep.input, "Tỉnh Không Có"), false);
  assert.equal(keep.input.value, "Thành phố Hà Nội");

  // 3. Dòng "Không có dữ liệu"/"Đang tải" không được tính là option khớp lỏng.
  const loading = makeEnv({ optionTexts: ["Không có dữ liệu"] });
  assert.equal(await loading.api.ngPickAutocomplete(loading.input, "Tỉnh Lào Cai"), false);
  assert.equal(loading.input.value, "");

  // 4. Khớp: chọn option (mousedown + click), KHÔNG dọn dẹp/không xoá gì.
  const hit = makeEnv({ optionTexts: ["Tỉnh Lào Cai"], hasBackdrop: true });
  assert.equal(await hit.api.ngPickAutocomplete(hit.input, "Tỉnh Lào Cai"), true);
  assert.ok(hit.log.some(([who, type]) => who === "option:Tỉnh Lào Cai" && type === "mousedown"));
  assert.ok(hit.log.some(([who, type]) => who === "option:Tỉnh Lào Cai" && type === "click"));
  assert.ok(!hit.log.some(([who, type]) => who === "backdrop" && type === "click"),
    "chọn được rồi thì không được đóng overlay bằng backdrop (Angular tự đóng)");

  console.log("angular area combobox abort passed");
})();
