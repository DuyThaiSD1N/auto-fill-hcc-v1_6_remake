// Cổng nộp bằng TẢI LẠI CẢ TRANG (HkdOnline: <input type="submit" onclick="return confirm(…)"> rồi
// postback ASP.NET): sendMessage chưa kịp mở kênh thì trang đã bị huỷ → mốc nộp mất ở mọi hồ sơ.
// Content script ghi cú bấm vào sessionStorage TRƯỚC khi gửi, trang kế tiếp gửi lại đúng cú bấm đó.
// Chạy THẬT đoạn code của content.js trong vm, mô phỏng "bấm → trang tải lại".
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const src = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");
const start = src.indexOf("    function sendSubmitClick(click) {");
const endMarker = "      pending.forEach(sendSubmitClick);\n    }\n";
const end = src.indexOf(endMarker, start) + endMarker.length;
const snippet = src.slice(start, end);

function page(store, { now = Date.now() } = {}) {
  const sent = [];
  const ctx = vm.createContext({
    SS_PENDING_SUBMIT_KEY: "__autofill_pending_submit", PENDING_SUBMIT_TTL_MS: 10 * 60 * 1000,
    JSON, Number, Array, Date: { now: () => now },
    sessionStorage: {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: (k) => { delete store[k]; },
    },
    chrome: { runtime: { lastError: null, sendMessage: (m, cb) => { sent.push(m); cb && cb(); } } },
  });
  vm.runInContext(`${snippet}\nthis.api = { rememberPendingSubmit };`, ctx);
  return { api: ctx.api, sent };
}

const click = (id, at) => ({ action: "dossierSubmitClicked", host: "hokinhdoanh.dkkd.gov.vn", ref: "", clickId: id, clickedAt: at });

test("bấm nộp → trang tải lại → trang mới gửi lại ĐÚNG cú bấm cũ (mã + giờ bấm) một lần rồi dọn", () => {
  const store = {};
  const t0 = Date.now();
  page(store, { now: t0 }).api.rememberPendingSubmit(click("c-1", t0));
  const p2 = page(store, { now: t0 + 3000 });
  assert.deepEqual(p2.sent.map((m) => [m.action, m.clickId, m.clickedAt]), [["dossierSubmitClicked", "c-1", t0]]);
  assert.equal(store.__autofill_pending_submit, undefined);
  assert.equal(page(store, { now: t0 + 6000 }).sent.length, 0, "trang sau nữa không gửi lại");
});

test("cú bấm quá 10 phút không gửi lại", () => {
  const store = {};
  const t0 = Date.now();
  page(store, { now: t0 }).api.rememberPendingSubmit(click("c-old", t0));
  assert.equal(page(store, { now: t0 + 11 * 60 * 1000 }).sent.length, 0);
});

test("cú bấm được GHI trước khi gửi (trang có thể bị huỷ ngay sau đó)", () => {
  const i = src.indexOf('const click = { action: "dossierSubmitClicked"');
  const block = src.slice(i, i + 300);
  assert.ok(block.indexOf("rememberPendingSubmit(click);") < block.indexOf("sendSubmitClick(click);"));
});
