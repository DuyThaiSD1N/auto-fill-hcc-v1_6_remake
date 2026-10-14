// Mốc "bấm Gửi hồ sơ" do BACKGROUND gửi thẳng lên BE — không phụ thuộc sidebar còn sống.
// Sidebar là iframe trong trang cổng: cổng chuyển hẳn trang lúc bấm nộp thì iframe chết trước khi
// kịp gửi, mốc mất và (vì phiếu đánh giá bật từ chính mốc đó) không để lại dấu vết nào.
// Chạy THẬT api/config.js + lib/submitClickReporter.js trong vm với chrome + fetch giả.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const read = (f) => fs.readFileSync(path.join(root, f), "utf8");
const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

function harness({ responses = [], onRefresh, journeys = { 5: { conversation_id: "conv-A" } } } = {}) {
  const store = {
    tlnd_auth: { access: "a0", refresh: "r0", user: { id: "u1" } },
    tlnd_journey: journeys,
  };
  const calls = [];
  const alarms = [];
  const cb = (fn, v) => { if (fn) fn(v); };
  const chrome = {
    runtime: { lastError: null, onStartup: { addListener() {} } },
    storage: {
      local: {
        get(keys, done) {
          const out = {};
          for (const k of [].concat(keys)) if (k in store) out[k] = structuredClone(store[k]);
          cb(done, out);
        },
        set(obj, done) { Object.assign(store, structuredClone(obj)); cb(done); },
      },
      onChanged: { addListener() {} },
    },
    alarms: { create: (name, opt) => alarms.push({ name, opt }), onAlarm: { addListener() {} } },
  };
  const queue = [...responses];
  const fetch = async (url, init) => {
    calls.push({ url, init, body: init?.body ? JSON.parse(init.body) : null });
    if (url.endsWith("/auth/refresh")) return onRefresh ? onRefresh(store) : { ok: false, status: 401 };
    const next = queue.shift() ?? { status: 200 };
    if (next === "network") throw new TypeError("Failed to fetch");
    return { ok: next.status >= 200 && next.status < 300, status: next.status, json: async () => ({}) };
  };
  const ctx = vm.createContext({
    chrome, fetch, console: { warn() {}, log() {} }, AbortController, JSON, Promise, Set, Date, Number, String,
    setTimeout: (fn) => { fn(); return 0; }, clearTimeout() {}, encodeURIComponent,
  });
  vm.runInContext(read("api/config.js"), ctx);
  vm.runInContext(read("lib/submitClickReporter.js"), ctx);
  const api = ctx.__TLND_SUBMIT__;
  return {
    api, store, alarms,
    submits: () => calls.filter((c) => c.url.includes("/submit-click")),
    outbox: () => store.tlnd_submit_outbox || [],
  };
}

test("gửi đúng conversation của tab (tlnd_journey), kèm mã + giờ bấm", async () => {
  const h = harness();
  const at = Date.now() - 2000;
  await h.api.reportClick({ tabId: 5, host: "dichvucong.laichau.gov.vn", ref: "", clickId: "c-1", clickedAt: at });
  const [call] = h.submits();
  assert.match(call.url, /\/api\/v1\/assistant\/conversations\/conv-A\/submit-click$/);
  assert.deepEqual(call.body, { click_id: "c-1", clicked_at: at, host: "dichvucong.laichau.gov.vn", ref: "" });
  assert.equal(call.init.headers.Authorization, "Bearer a0");
  assert.deepEqual(h.outbox(), []);
});

test("tab tách chứng thực → conversation của tab GỐC", async () => {
  const h = harness();
  await h.api.reportClick({ tabId: 88, originTabId: 5, clickId: "c-2", clickedAt: Date.now() });
  assert.match(h.submits()[0].url, /conversations\/conv-A\//);
});

test("tab chưa có hồ sơ / thiếu mã cú bấm → không gửi (không lọc trùng được với sidebar)", async () => {
  const h = harness();
  await h.api.reportClick({ tabId: 99, clickId: "c-3", clickedAt: Date.now() });
  await h.api.reportClick({ tabId: 5, clickId: "", clickedAt: Date.now() });
  assert.equal(h.submits().length, 0);
});

test("401 → làm mới token (định dạng tlnd_auth) → gửi lại được", async () => {
  const h = harness({
    responses: [{ status: 401 }, { status: 200 }],
    onRefresh: () => ({ ok: true, status: 200, json: async () => ({ accessToken: "a1", refreshToken: "r1" }) }),
  });
  await h.api.reportClick({ tabId: 5, clickId: "c-4", clickedAt: Date.now() });
  assert.equal(h.submits()[1].init.headers.Authorization, "Bearer a1");
  const { access, refresh, user } = h.store.tlnd_auth;
  assert.deepEqual({ access, refresh, user }, { access: "a1", refresh: "r1", user: { id: "u1" } });
  assert.deepEqual(h.outbox(), []);
});

test("sidebar vừa làm mới trước (refresh của ta bị từ chối) → dùng cặp trong storage, không xoá token", async () => {
  const h = harness({
    responses: [{ status: 401 }, { status: 200 }],
    onRefresh: (store) => { store.tlnd_auth = { access: "a-sb", refresh: "r-sb" }; return { ok: false, status: 401 }; },
  });
  await h.api.reportClick({ tabId: 5, clickId: "c-5", clickedAt: Date.now() });
  assert.equal(h.submits()[1].init.headers.Authorization, "Bearer a-sb");
  assert.equal(h.store.tlnd_auth.access, "a-sb");
});

test("mất mạng → nằm lại hàng đợi + hẹn giờ; lần sau gửi đúng cú bấm cũ", async () => {
  // Server phụ đang tắt → mỗi lượt gửi chỉ thử MỘT server.
  const h = harness({ responses: ["network"] });
  await h.api.reportClick({ tabId: 5, clickId: "c-6", clickedAt: Date.now() });
  assert.equal(h.outbox().length, 1);
  assert.ok(h.alarms.some((a) => a.name === "tlnd-submit-outbox"));
  await h.api.flush();
  assert.deepEqual(h.outbox(), []);
  assert.deepEqual([...new Set(h.submits().map((c) => c.body.click_id))], ["c-6"]);
});

test("BE cũ chưa có endpoint (404) / phiên hết hạn → bỏ, không kẹt hàng đợi", async () => {
  const h = harness({ responses: [{ status: 404 }] });
  await h.api.reportClick({ tabId: 5, clickId: "c-7", clickedAt: Date.now() });
  assert.deepEqual(h.outbox(), []);
});

// ── Nối dây: content → background → BE, sidebar mang cùng mã ──

test("content sinh mã + giờ bấm ngay tại cú bấm", () => {
  assert.match(strip(read("content.js")),
    /__tlnd: "submitClicked", host: location\.hostname, ref: hit\.ref, clickId, clickedAt: lastSubmitClickAt/);
});

test("background nạp reporter và báo MỌI cú bấm (không chỉ tab tách)", () => {
  const bg = strip(read("background.js"));
  assert.match(bg, /importScripts\("api\/config\.js", "lib\/submitClickReporter\.js"\)/);
  const i = bg.indexOf('if (msg?.__tlnd !== "submitClicked" && msg?.__tlnd !== "attachRetrying") return;');
  const block = bg.slice(i, bg.indexOf("});", bg.indexOf("chrome.runtime.sendMessage(", i)));
  const report = block.indexOf("__TLND_SUBMIT__?.reportClick(");
  assert.ok(report > 0 && report < block.indexOf("if (!originTabId) return;"),
    "phải báo TRƯỚC khi lọc tab tách — tab gốc cũng cần background gửi");
  assert.match(block, /clickId: msg\.clickId/);
});

test("sidebar gửi kèm click_id để BE nhận ra cùng cú bấm", () => {
  assert.match(strip(read("sidebar.js")), /__event:submit_clicked:[\s\S]{0,200}click_id: String\(msg\.clickId \|\| ""\)/);
});

test("config.js chạy được trong service worker (không có window)", () => {
  const ctx = vm.createContext({ chrome: {}, console, AbortController, setTimeout, clearTimeout, fetch() {} });
  vm.runInContext(read("api/config.js"), ctx);
  assert.equal(typeof ctx.tlndOverBases, "function");
});

test("sidebar nhận cặp token mới khi background xoay token — không bị đá ra đăng nhập", () => {
  const auth = strip(read("api/auth.js"));
  assert.match(auth, /chrome\.storage\.onChanged\.addListener[\s\S]{0,200}changes\[KEY\]\?\.newValue/);
  assert.match(auth, /return \(await adoptRotatedTokens\(usedRefresh\)\) \? "ok" : "invalid";/);
});
