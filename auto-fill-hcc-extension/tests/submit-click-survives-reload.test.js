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
const start = src.indexOf("  const SS_PENDING_SUBMIT_KEY");
const end = src.indexOf("\n  }\n", src.indexOf("  if (IS_TOP_FRAME) {\n    const pending = readPendingSubmits()")) + 4;
const snippet = src.slice(start, end);

function page(store, { now = Date.now() } = {}) {
  const sent = [];
  const timers = [];
  const ctx = vm.createContext({
    IS_TOP_FRAME: true, JSON, Number, Array, Date: { now: () => now },
    sessionStorage: {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: (k) => { delete store[k]; },
    },
    chrome: { runtime: { lastError: null, sendMessage: (m, cb) => { sent.push(m); cb && cb(); } } },
    setTimeout: (fn) => { timers.push(fn); return 0; },
  });
  vm.runInContext(`${snippet}\nthis.api = { rememberPendingSubmit, sendSubmitClick };`, ctx);
  return { api: ctx.api, sent, runTimers: () => timers.splice(0).forEach((fn) => fn()) };
}

const click = (id, at) => ({ __tlnd: "submitClicked", host: "hokinhdoanh.dkkd.gov.vn", ref: "", clickId: id, clickedAt: at });

test("bấm nộp → trang tải lại → trang mới gửi lại ĐÚNG cú bấm cũ (mã + giờ bấm), rồi dọn", () => {
  const store = {};
  const t0 = Date.now();
  const p1 = page(store, { now: t0 });
  p1.api.rememberPendingSubmit(click("c-1", t0));
  // Trang bị huỷ trước khi tin đi được — p1.sent không quan trọng. Trang mới nạp lên:
  const p2 = page(store, { now: t0 + 3000 });
  assert.deepEqual(p2.sent.map((m) => [m.clickId, m.clickedAt]), [["c-1", t0]]);
  assert.ok(store.__tlnd_pending_submit, "chưa xoá trước lần gửi thứ hai");
  p2.runTimers();
  assert.equal(p2.sent.length, 2, "gửi lại lần nữa cho sidebar khung trong trang");
  assert.equal(store.__tlnd_pending_submit, undefined);
});

test("cú bấm quá 10 phút không gửi lại (không chấm mốc nộp muộn cho lần khác)", () => {
  const store = {};
  const t0 = Date.now();
  page(store, { now: t0 }).api.rememberPendingSubmit(click("c-old", t0));
  const later = page(store, { now: t0 + 11 * 60 * 1000 });
  assert.equal(later.sent.length, 0);
  assert.equal(store.__tlnd_pending_submit, undefined);
});

test("giữ tối đa 5 cú bấm treo", () => {
  const store = {};
  const t0 = Date.now();
  const p = page(store, { now: t0 });
  for (let i = 0; i < 7; i++) p.api.rememberPendingSubmit(click(`c-${i}`, t0));
  assert.deepEqual(JSON.parse(store.__tlnd_pending_submit).map((c) => c.clickId), ["c-2", "c-3", "c-4", "c-5", "c-6"]);
});

test("cú bấm được GHI trước khi gửi (trang có thể bị huỷ ngay sau đó)", () => {
  const i = src.indexOf('const click = { __tlnd: "submitClicked"');
  const block = src.slice(i, i + 300);
  assert.ok(block.indexOf("rememberPendingSubmit(click);") < block.indexOf("sendSubmitClick(click);"));
});
