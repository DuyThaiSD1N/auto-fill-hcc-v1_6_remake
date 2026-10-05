// Mốc "bấm Gửi hồ sơ" phải tới được BE kể cả khi token vừa hết hạn / mất mạng lúc bấm.
// Đo trên prod: ~1,6% hồ sơ đã hỏi đánh giá (chắc chắn đã bấm nộp) mà sổ vẫn "chưa nộp" — background
// gửi một phát bằng access token hết hạn, BE trả 401, fetch không ném lỗi nên tưởng đã ghi.
// Chạy THẬT đoạn code của background.js trong vm với chrome + fetch giả.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const src = fs.readFileSync(path.join(__dirname, "..", "background.js"), "utf8");
const block = src.slice(
  src.indexOf('const SUBMIT_WATCH_KEY = "autofill_submit_watch";'),
  src.indexOf("chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {"),
);

function harness({ responses = [], tokens = { accessToken: "a0", refreshToken: "r0" }, onRefresh } = {}) {
  const store = {
    autofill_submit_watch: { base: "https://chinh", bases: ["https://chinh", "https://phu"] },
    auth_tokens: tokens,
    autofill_session_7: { dossierId: "d1" },
  };
  const calls = [];
  const alarms = [];
  const listeners = { alarm: [], startup: [], changed: [] };
  const chrome = {
    storage: {
      local: {
        async get(keys) {
          const out = {};
          for (const k of [].concat(keys)) if (k in store) out[k] = structuredClone(store[k]);
          return out;
        },
        async set(obj) { Object.assign(store, structuredClone(obj)); },
        async remove(keys) { for (const k of [].concat(keys)) delete store[k]; },
      },
      onChanged: { addListener: (fn) => listeners.changed.push(fn) },
    },
    alarms: { create: (name, opt) => alarms.push({ name, opt }), onAlarm: { addListener: (fn) => listeners.alarm.push(fn) } },
    runtime: { onStartup: { addListener: (fn) => listeners.startup.push(fn) }, sendMessage: async () => {} },
  };
  const queue = [...responses];
  const fetch = async (url, init) => {
    calls.push({ url, init, body: init.body ? JSON.parse(init.body) : null });
    if (url.endsWith("/auth/refresh")) return onRefresh ? onRefresh(store) : { ok: false, status: 401 };
    const next = queue.shift() ?? { status: 200 };
    if (next === "network") throw new TypeError("Failed to fetch");
    return { ok: next.status >= 200 && next.status < 300, status: next.status, json: async () => ({}) };
  };
  const ctx = vm.createContext({
    chrome, fetch, console: { warn() {}, log() {} }, crypto: { randomUUID: () => "uuid-" + Math.random() },
    setTimeout: (fn) => { fn(); return 0; }, clearTimeout() {}, AbortController, Date, JSON, Promise, Set, Number, String, Array, Object,
  });
  vm.runInContext(block + "\n;this.api = { reportDossierSubmitClick, reportDossierSubmitSeen, flushSubmitOutbox };", ctx);
  return { api: ctx.api, store, calls, alarms, submits: () => calls.filter((c) => c.url.includes("submit-click")) };
}

const outbox = (h) => h.store.autofill_submit_outbox || [];
const settle = async (h) => { await h.api.flushSubmitOutbox(); await new Promise((r) => setImmediate(r)); };

test("401 → làm mới token → gửi lại được, kèm mã cú bấm và giờ bấm thật", async () => {
  const h = harness({
    responses: [{ status: 401 }, { status: 200 }],
    onRefresh: () => ({ ok: true, status: 200, json: async () => ({ accessToken: "a1", refreshToken: "r1" }) }),
  });
  const bamLuc = Date.now() - 5 * 60 * 1000; // gửi lại muộn vẫn phải mang giờ bấm thật
  await h.api.reportDossierSubmitClick(7, "dvc.moc.gov.vn", "", "click-1", bamLuc);
  await settle(h);
  const [first, second] = h.submits();
  assert.equal(second.init.headers.Authorization, "Bearer a1");
  assert.deepEqual(
    { id: first.body.clickId, at: first.body.clickedAt, src: first.body.source },
    { id: "click-1", at: bamLuc, src: "click" },
  );
  assert.equal(h.store.auth_tokens.refreshToken, "r1", "token mới phải lưu lại cho popup dùng");
  assert.deepEqual(outbox(h), []);
});

test("popup vừa làm mới trước (refresh của ta bị từ chối) → dùng cặp token trong storage", async () => {
  const h = harness({
    responses: [{ status: 401 }, { status: 200 }],
    onRefresh: (store) => { store.auth_tokens = { accessToken: "a-popup", refreshToken: "r-popup" }; return { ok: false, status: 401 }; },
  });
  await h.api.reportDossierSubmitClick(7, "h", "", "c1", Date.now());
  await settle(h);
  assert.equal(h.submits()[1].init.headers.Authorization, "Bearer a-popup");
  assert.deepEqual(outbox(h), []);
  assert.equal(h.store.auth_tokens.accessToken, "a-popup", "background không được xoá token");
});

test("mất mạng → mốc nằm lại hàng đợi + hẹn giờ gửi lại, lần sau gửi được", async () => {
  const h = harness({ responses: ["network", "network"] });
  await h.api.reportDossierSubmitClick(7, "h", "", "c1", Date.now());
  await settle(h);
  assert.equal(outbox(h).length, 1);
  assert.ok(h.alarms.some((a) => a.name === "autofill-submit-outbox"));
  await settle(h); // lần hẹn giờ: mạng đã ổn
  assert.deepEqual(outbox(h), []);
  assert.equal(new Set(h.submits().map((c) => c.body.clickId)).size, 1, "gửi lại đúng cú bấm cũ");
});

test("fetch không ném với 401 — trước đây vẫn tưởng đã ghi; giờ còn trong hàng đợi", async () => {
  const h = harness({ responses: [{ status: 401 }] }); // refresh hỏng, storage không có token mới
  await h.api.reportDossierSubmitClick(7, "h", "", "c1", Date.now());
  await settle(h);
  assert.equal(outbox(h).length, 1);
});

test("BE chính lỗi hạ tầng → sang BE phụ", async () => {
  const h = harness({ responses: [{ status: 503 }, { status: 200 }] });
  await h.api.reportDossierSubmitClick(7, "h", "", "c1", Date.now());
  await settle(h);
  assert.deepEqual(h.submits().map((c) => new URL(c.url).host), ["chinh", "phu"]);
  assert.deepEqual(outbox(h), []);
});

test("BE từ chối hẳn (4xx) → bỏ, không kẹt hàng đợi", async () => {
  const h = harness({ responses: [{ status: 422 }] });
  await h.api.reportDossierSubmitClick(7, "h", "", "c1", Date.now());
  await settle(h);
  assert.deepEqual(outbox(h), []);
});

test("không có khóa hồ sơ ở tab → không chấm (chỉ tính hồ sơ trợ lý tham gia)", async () => {
  const h = harness();
  await h.api.reportDossierSubmitClick(99, "h", "", "c1", Date.now());
  await settle(h);
  assert.equal(h.submits().length, 0);
});

// ── Lớp 2: chữ "nộp hồ sơ thành công" ──

test("chữ thành công ngay sau cú bấm → là của chính lần đó, không gửi thêm", async () => {
  const h = harness();
  const t = Date.now();
  await h.api.reportDossierSubmitClick(7, "h", "", "c1", t);
  await h.api.reportDossierSubmitSeen(7, "h", "", t + 4000);
  await settle(h);
  assert.deepEqual(h.submits().map((c) => c.body.source), ["click"]);
});

test("cú bấm rớt mà màn kết quả hiện chữ thành công → ghi bằng nguồn text, một lần", async () => {
  const h = harness();
  await h.api.reportDossierSubmitSeen(7, "h", "", Date.now());
  await h.api.reportDossierSubmitSeen(7, "h", "", Date.now() + 60 * 60 * 1000);
  await settle(h);
  assert.deepEqual(h.submits().map((c) => c.body.source), ["text"]);
  assert.equal(h.store.autofill_session_7.dossierSubmitted, true);
});

test("chữ thành công có sẵn TỪ TRƯỚC khi bắt đầu hồ sơ này → của hồ sơ cũ, bỏ", async () => {
  const h = harness();
  h.store.autofill_session_7 = { dossierId: "d2", dossierCreatedAt: 2_000 };
  await h.api.reportDossierSubmitSeen(7, "h", "", 1_000);
  await settle(h);
  assert.equal(h.submits().length, 0);
});

test("cú bấm chưa gửi được thì mốc dò chữ phải chờ sau nó (giữ thứ tự để BE lọc trùng)", async () => {
  const h = harness({ responses: Array(8).fill("network") });
  const t = Date.now();
  await h.api.reportDossierSubmitClick(7, "h", "", "c1", t);
  h.store.autofill_submit_marks = {}; // giả sử mốc theo tab bị mất → dò chữ vẫn vào hàng
  await h.api.reportDossierSubmitSeen(7, "h", "", t + 5000);
  await settle(h);
  assert.deepEqual(outbox(h).map((i) => i.source), ["click", "text"]);
  assert.equal(h.submits().filter((c) => c.body.source === "text").length, 0, "text không được vượt lên trước");
});

test("mốc nằm hàng đợi quá 3 ngày thì bỏ (giờ đó ghi vào sổ cũng vô nghĩa)", async () => {
  const h = harness();
  h.store.autofill_submit_outbox = [{ dossierId: "d1", clickId: "cu", clickedAt: Date.now() - 4 * 24 * 3600 * 1000 }];
  await settle(h);
  assert.equal(h.submits().length, 0);
  assert.deepEqual(outbox(h), []);
});

test("content: mã + giờ bấm sinh ngay tại cú bấm; dò chữ thành công báo background", () => {
  const content = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");
  assert.match(content, /action: "dossierSubmitClicked", host: location\.hostname, ref, clickId, clickedAt: lastSubmitClickAt/);
  assert.match(content, /const SUCCESS_PHRASES = \["nop ho so thanh cong", "gui ho so thanh cong"\]/);
  assert.match(content, /action: "dossierSubmitSeen"/);
  // successText riêng của cổng vẫn khóa theo urlPattern — cụm chữ khớp mà sai trang thì không tính.
  assert.match(content, /!Array\.isArray\(groups\) \|\| !groups\.length \|\| !matchUrl\(rule\)\.ok/);
});

test("popup: refresh bị từ chối vì background vừa xoay token → dùng token mới, không đá ra đăng nhập", () => {
  // Hành vi chạy thật ở tests/auth-keep-session.test.js; ở đây chỉ khoá chỗ đọc lại storage.
  const client = fs.readFileSync(path.join(__dirname, "..", "api", "client.js"), "utf8");
  const fn = client.slice(client.indexOf("function refreshTokens("), client.indexOf("async function apiCall("));
  assert.match(fn, /cur\.refreshToken !== tokens\.refreshToken\) return \{ status: "ok", tokens: cur \}/);
});

// ── Chứng thực tách nhiều tab: CHUNG một khóa hồ sơ, mỗi tab một lần nộp ──

function haiTabTach() {
  const h = harness();
  h.store.autofill_session_8 = { dossierId: "d1" }; // background gieo khóa gốc cho tab tách
  return h;
}

test("đa tab: mỗi tab bấm + hiện chữ thành công (kể cả quay lại sau 1 giờ) → đúng 2 lần nộp", async () => {
  const h = haiTabTach();
  const t = Date.now();
  await h.api.reportDossierSubmitClick(7, "h", "", "c-tab7", t);
  await h.api.reportDossierSubmitClick(8, "h", "", "c-tab8", t + 60_000);
  // Hàng đợi tự chuyển tab → tab cũ bị ẩn, chữ của nó chỉ dò được khi cán bộ quay lại rất lâu sau.
  await h.api.reportDossierSubmitSeen(7, "h", "", t + 3600_000);
  await h.api.reportDossierSubmitSeen(8, "h", "", t + 3600_000);
  await settle(h);
  assert.deepEqual(h.submits().map((c) => c.body.clickId), ["c-tab7", "c-tab8"]);
});

test("đa tab: tab 2 rớt cú bấm, chỉ còn chữ thành công → vẫn đếm (cú bấm tab 1 không che)", async () => {
  const h = haiTabTach();
  const t = Date.now();
  await h.api.reportDossierSubmitClick(7, "h", "", "c-tab7", t);
  await h.api.reportDossierSubmitSeen(8, "h", "", t + 90_000);
  await settle(h);
  assert.deepEqual(h.submits().map((c) => c.body.source), ["click", "text"]);
});
