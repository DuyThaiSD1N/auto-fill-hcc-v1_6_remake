// Cổng DVC quốc gia mới là ứng dụng một trang: chuyển hồ sơ / dựng lại biểu mẫu thì tạo MODEL SurveyJS mới mà trang
// không tải lại. Engine phải luôn làm việc trên model đang gắn với các ô hiển thị — giữ model cũ thì giá trị ghi vào
// model không còn trên màn hình (ô viền xanh mà trống, ô bắt buộc trống không bị tô đỏ).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const src = fs.readFileSync(path.join(__dirname, "..", "content", "surveyjs-main.js"), "utf8");

function fakeSurvey(emptyRequiredNames) {
  const qs = ["citizenField1", "citizenField2"].map((name) => ({
    name, isReadOnly: false, isRequired: true, isVisible: true, isEmpty: () => emptyRequiredNames.includes(name),
  }));
  return {
    getQuestionByName: (n) => qs.find((q) => q.name === n) || null,
    getAllQuestions: () => qs,
  };
}

function loadEngine() {
  const listeners = {};
  const nodes = ["citizenField1", "citizenField2"].map((name) => ({
    name, offsetParent: {}, getAttribute: () => name, querySelector: () => null, querySelectorAll: () => [],
  }));
  const bind = (survey) => nodes.forEach((n) => { n.__reactFiber$x = { memoizedProps: { model: survey } }; });
  const document = {
    querySelectorAll: (sel) => (sel === "[data-name]" ? nodes : []),
    querySelector: (sel) => (/data-name="citizenField1"/.test(sel) ? nodes[0] : /data-name="citizenField2"/.test(sel) ? nodes[1] : null),
    addEventListener: (type, fn) => { listeners[type] = fn; },
    removeEventListener: () => {},
    dispatchEvent: (ev) => { listeners[ev.type]?.(ev); },
  };
  class CustomEvent { constructor(type, init) { this.type = type; this.detail = init?.detail; } }
  const ctx = {
    window: { addEventListener: () => {} }, document, CustomEvent, location: { hostname: "dichvucong.gov.vn" },
    HTMLInputElement: function () {}, CSS: { escape: (s) => s }, setTimeout, clearTimeout, console,
  };
  ctx.HTMLInputElement.prototype = { click() {}, showPicker() {} };
  vm.runInNewContext(src, ctx);
  const call = (payload) => new Promise((resolve) => {
    listeners.__HCC_SJS_RESULT__ = (ev) => resolve(JSON.parse(ev.detail));
    listeners.__HCC_SJS_REQUEST__({ detail: JSON.stringify({ ...payload, requestId: "1" }) });
  });
  return { bind, call };
}

test("cổng thay model (chuyển hồ sơ trong cùng tab) → engine đọc model mới, không giữ model cũ", async () => {
  const { bind, call } = loadEngine();
  bind(fakeSurvey([]));                       // hồ sơ trước: đã điền đủ
  assert.deepEqual((await call({ op: "emptyRequired" })).names, []);
  bind(fakeSurvey(["citizenField2"]));        // hồ sơ mới: model mới, ô bắt buộc còn trống
  assert.deepEqual((await call({ op: "emptyRequired" })).names, ["citizenField2"]);
});

test("không còn cache model vĩnh viễn; điền lại một lần khi model bị thay giữa lượt", () => {
  assert.doesNotMatch(src, /cachedSurvey/);
  assert.match(src, /res = await setValuesOn\(survey, fields\);\s*const now = findSurvey\(\);\s*if \(!now \|\| now === survey\) return res;\s*survey = now;/);
});
