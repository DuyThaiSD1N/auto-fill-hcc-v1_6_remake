// Điền đợt 2 trên form SurveyJS (Cổng DVC quốc gia mới): sau lượt điền đầu, BE soát lại ở nền; engine hỏi kết quả rồi
// ghi lại RIÊNG các ô BE sửa — không đè ô đã được sửa tay, không chọn xã trên danh mục của tỉnh cũ, và ghi lại ô
// cổng làm trống khi tra cứu dân cư lại.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const src = fs.readFileSync(path.join(root, "content", "surveyjs-main.js"), "utf8");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8").replace(/^\s*\/\/.*$/gm, "");
const PREFIX = "__HCC_SJS_";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function question(name, { type = "text", choices = [], visible = true, readOnly = false } = {}) {
  const q = {
    name, choices, isVisible: visible, isReadOnly: readOnly, onSet: null, _value: undefined,
    getType: () => type,
    isEmpty() { return this._value === undefined || this._value === null || this._value === ""; },
    get value() { return this._value; },
    set value(v) { const old = this._value; this._value = v; if (this.onSet && old !== v) this.onSet(v); },
  };
  return q;
}

function setup(questions) {
  const event = () => ({ add: () => {} });
  const survey = {
    onValueChanging: event(), onValueChanged: event(),
    getQuestionByName: (n) => questions.find((q) => q.name === n) || null,
    getAllQuestions: () => questions,
  };
  const nodes = questions.map((q) => ({
    getAttribute: () => q.name, offsetParent: {}, __reactFiber$x: { memoizedProps: { model: survey } },
  }));
  let reply = null;
  const ctx = {
    window: { addEventListener: () => {} }, location: { hostname: "dichvucong.gov.vn" },
    document: {
      querySelector: () => null, querySelectorAll: (sel) => (sel === "[data-name]" ? nodes : []),
      addEventListener: () => {}, removeEventListener: () => {},
      dispatchEvent: (e) => { reply = JSON.parse(e.detail); },
    },
    CustomEvent: class { constructor(_type, init) { this.detail = init.detail; } },
    HTMLInputElement: function () {}, CSS: { escape: (s) => s }, console,
    setTimeout, clearTimeout, setInterval: () => 1, clearInterval: () => {},
    requestAnimationFrame: (fn) => setTimeout(fn, 0),
  };
  ctx.HTMLInputElement.prototype = { click() {}, showPicker() {} };
  vm.runInNewContext(src, ctx);
  const call = async (op, fields) => {
    await ctx.window[`${PREFIX}HANDLER__`]({ detail: JSON.stringify({ op, fields, requestId: "t" }) });
    return reply;
  };
  return { call };
}

const reasons = (res) => Object.fromEntries(res.results.map((r) => [r.name, r.ok ? "ok" : r.reason]));

test("chỉ ghi ô còn đúng giá trị lượt đầu hoặc đang trống; ô đã sửa tay, ô ẩn, ô khoá thì giữ nguyên", async () => {
  const name = question("hoTen__1");
  const agency = question("coQuan__1");
  const number = question("soGiay__1");
  const date = question("ngay__1");
  const hidden = question("an__1", { visible: false });
  const locked = question("khoa__1", { readOnly: true });
  locked._value = "cổng đổ";
  const { call } = setup([name, agency, number, date, hidden, locked]);
  await call("setValues", [
    { name: "hoTen", comp: "sjs-text", value: "TRAN VAN MAU" },
    { name: "coQuan", comp: "sjs-text", value: "UBND xã Mẫu" },
    { name: "soGiay", comp: "sjs-text", value: "15/2024" },
  ]);
  agency.value = "cán bộ gõ lại";
  const res = await call("patchValues", [
    { name: "hoTen", comp: "sjs-text", value: "TRẦN VĂN MẪU" },
    { name: "coQuan", comp: "sjs-text", value: "UBND xã Mẫu, tỉnh Mẫu" },
    { name: "soGiay", comp: "sjs-text", value: "07/2009" },
    { name: "ngay", comp: "sjs-date", value: "04/05/2009", code: "2009-05-04" },
    { name: "an", comp: "sjs-text", value: "x" },
    { name: "khoa", comp: "sjs-text", value: "x" },
  ]);
  assert.deepEqual(reasons(res), {
    hoTen: "ok", coQuan: "changed", soGiay: "ok", ngay: "ok", an: "not-found", khoa: "readonly",
  });
  assert.equal(name.value, "TRẦN VĂN MẪU");
  assert.equal(agency.value, "cán bộ gõ lại");
  assert.equal(number.value, "07/2009");
  assert.equal(date.value, "2009-05-04");
  assert.equal(locked.value, "cổng đổ");
  // Lượt ghi này thành mốc mới: sửa tay sau đó vẫn được giữ ở lượt ghi kế tiếp.
  number.value = "cán bộ sửa số";
  const again = await call("patchValues", [{ name: "soGiay", comp: "sjs-text", value: "09/2025" }]);
  assert.deepEqual(reasons(again), { soGiay: "changed" });
});

test("đổi tỉnh thì chờ cổng nạp danh mục xã của tỉnh mới rồi mới chọn xã", async () => {
  const province = question("tinh__1", { type: "dropdown",
    choices: [{ value: "a", text: "Tỉnh A" }, { value: "b", text: "Tỉnh B" }] });
  const ward = question("xa__1", { type: "dropdown", choices: [{ value: "a-1", text: "Xã Mẫu" }] });
  const { call } = setup([province, ward]);
  await call("setValues", [
    { name: "tinh", comp: "sjs-dropdown", value: "Tỉnh A" },
    { name: "xa", comp: "sjs-dropdown", value: "Xã Mẫu" },
  ]);
  assert.equal(ward.value, "a-1");
  // Cổng: đổi tỉnh → xoá xã, một lúc sau danh mục xã của tỉnh mới mới về.
  province.onSet = () => setTimeout(() => {
    ward._value = undefined;
    ward.choices = [{ value: "b-1", text: "Xã Mẫu" }];
  }, 700);
  const res = await call("patchValues", [
    { name: "tinh", comp: "sjs-dropdown", value: "Tỉnh B" },
    { name: "xa", comp: "sjs-dropdown", value: "Xã Mẫu" },
  ]);
  assert.deepEqual(reasons(res), { tinh: "ok", xa: "ok" });
  assert.equal(province.value, "b");
  assert.equal(ward.value, "b-1");
});

test("ô tra cứu dân cư đổi làm cổng xoá ô khác → ghi lại ô engine đã điền", async () => {
  const number = question("soDinhDanh__1");
  const gender = question("gioiTinh__1");
  const { call } = setup([number, gender]);
  await call("setValues", [
    { name: "soDinhDanh", comp: "sjs-text", value: "001080000001", lookup: true },
    { name: "gioiTinh", comp: "sjs-text", value: "Nam" },
  ]);
  number.onSet = () => setTimeout(() => { gender._value = ""; }, 500);  // cổng tra lại không ra → làm trống
  const res = await call("patchValues", [{ name: "soDinhDanh", comp: "sjs-text", value: "001080000002", lookup: true }]);
  assert.deepEqual(reasons(res), { soDinhDanh: "ok" });
  assert.equal(gender.value, "Nam");
});

test("lượt ghi đợt 2 không xoá dấu màu, không cuộn, và hoãn ảnh chụp form tới sau khi ghi", () => {
  const filler = read("content/fill-surveyjs.js");
  const patch = filler.slice(filler.indexOf("async function patchFormSurveyJs"), filler.indexOf("function uploadRows"));
  assert.match(patch, /callMain\(\{ op: "patchValues", fields \}/);
  assert.doesNotMatch(patch, /removeAttribute|followTo|emptyRequired/);
  const content = read("content.js");
  assert.match(content, /if \(msg\.action === "patchFields"\) \{[\s\S]*?H\.formSnapshot\?\.track\?\.\(msg\.formSnapshot,[\s\S]*?sendResponse\(res\);/);
  const popup = read("popup.js");
  assert.match(popup, /if \(cfg\.secondPass && !page\) options\.fillSupports = \["secondPass", "secondPassLegacy"\];/);
  assert.match(popup, /deferSnapshot: secondPass,/);
  assert.match(content, /if \(!res\?\.error && !msg\.deferSnapshot\) H\.formSnapshot\?\.track\?\./);
  assert.match(popup, /if \(secondPass && !fillRes\?\.error\) await applySecondPass\(requestId, allFields, formSnapshot\);/);
  assert.match(popup, /sendToContent\(\{ action: "patchFields", fields, baseFields, formSnapshot \}\)/);
  assert.match(read("api/endpoints.js"), /\/api\/v1\/process\/\$\{encodeURIComponent\(requestId\)\}\/second-pass/);
});
