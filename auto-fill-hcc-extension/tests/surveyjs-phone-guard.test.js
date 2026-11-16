// Cổng DVC quốc gia mới: đổi SĐT người nộp (gõ tay hay engine điền) làm cổng gọi API tra công dân; API lỗi thì cổng ghi
// rỗng giấy tờ, ngày cấp, nơi cấp, nơi cư trú của người nộp. Engine chụp khối trước khi SĐT đổi rồi ghi lại ô bị làm trống.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const src = fs.readFileSync(path.join(__dirname, "..", "content", "surveyjs-main.js"), "utf8");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function fakeEvent() {
  const fns = [];
  return { add: (fn) => fns.push(fn), fire: (opt) => fns.forEach((fn) => fn(null, opt)) };
}

function question(name, value, readOnly = false) {
  return { name, value, isReadOnly: readOnly, isVisible: true, getType: () => "text",
    isEmpty() { return this.value === undefined || this.value === null || this.value === ""; } };
}

function setup() {
  const phone = question("citizenPhone__1", "");
  const block = {
    name: question("citizenName__1", "NGUYEN VAN A", true),
    idType: question("citizenNycGiaytotuythan__1", "1"),
    issueDate: question("citizenIssueDate__1", "2021-07-02"),
    issuePlace: question("citizenIssuePlace__1", "Cục Cảnh sát"),
  };
  const all = [block.name, phone, block.idType, block.issueDate, block.issuePlace];
  const panel = { isPanel: true, questions: all };
  all.forEach((q) => { q.parent = panel; });
  const survey = {
    onValueChanging: fakeEvent(), onValueChanged: fakeEvent(),
    getQuestionByName: (n) => all.find((q) => q.name === n) || null,
    getAllQuestions: () => all,
  };
  const node = { getAttribute: () => phone.name, __reactFiber$x: { memoizedProps: { model: survey } } };
  let tick = null;
  const ctx = {
    window: { addEventListener: () => {} }, location: { hostname: "dichvucong.gov.vn" },
    document: {
      querySelector: (sel) => (sel.includes("citizenPhone") ? node : null), querySelectorAll: () => [],
      addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => {},
    },
    CustomEvent: class {}, HTMLInputElement: function () {}, CSS: { escape: (s) => s }, console,
    setTimeout, clearTimeout, setInterval: (fn) => { tick = fn; return 1; }, clearInterval: () => {},
  };
  ctx.HTMLInputElement.prototype = { click() {}, showPicker() {} };
  vm.runInNewContext(src, ctx);
  tick();  // vòng dò thấy ô SĐT → cài bộ giữ
  const typePhone = (value) => {
    survey.onValueChanging.fire({ name: phone.name, value, oldValue: phone.value });
    phone.value = value;
    survey.onValueChanged.fire({ name: phone.name, value });
  };
  return { block, typePhone };
}

test("cổng xoá khối người nộp sau khi đổi SĐT → ghi lại đúng giá trị cũ; ô cổng đổ giá trị mới thì giữ", async () => {
  const { block, typePhone } = setup();
  typePhone("0900000000");
  await sleep(300);  // API tra công dân trả lỗi → cổng ghi rỗng
  block.idType.value = "";
  block.issueDate.value = "";
  block.issuePlace.value = "Nơi cấp cổng đổ mới";
  await sleep(2000);
  assert.equal(block.idType.value, "1");
  assert.equal(block.issueDate.value, "2021-07-02");
  assert.equal(block.issuePlace.value, "Nơi cấp cổng đổ mới");
  assert.equal(block.name.value, "NGUYEN VAN A");
});

test("engine điền cũng cài bộ giữ SĐT", () => {
  assert.match(src, /installRelationGuards\(survey\);\s*installPhoneGuard\(survey\);/);
});
