// "Tự đăng xuất giữa lúc làm hồ sơ": chỉ đăng xuất khi BE nói rõ phiên không còn (401/403 ở
// /auth/refresh). Mất mạng, BE đang khởi động lại (502/503), bảo trì… là lỗi TẠM — giữ phiên.
// Chạy THẬT api/auth.js trong vm với fetch + chrome.storage giả.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const read = (f) => fs.readFileSync(path.join(root, f), "utf8");

const b64 = (o) => Buffer.from(JSON.stringify(o)).toString("base64").replace(/=+$/, "");
const jwt = (iat, exp) => `h.${b64({ iat, exp })}.s`;

function harness(refreshResponse, { stored } = {}) {
  const now = Math.floor(Date.now() / 1000);
  const store = { tlnd_auth: stored || { access: jwt(now - 7200, now - 3600), refresh: "r0", user: { id: "u1" } } };
  const events = [];
  const calls = [];
  const win = {
    dispatchEvent: (e) => events.push(e.type),
    tlndOverBases: (fn) => fn("https://be.test"),
    tlndFetch: async (url, init) => {
      calls.push({ url, auth: init?.headers?.Authorization });
      if (url.endsWith("/auth/refresh")) return refreshResponse(store);
      return { status: init?.headers?.Authorization === `Bearer ${store.tlnd_auth?.access}` && store.__fresh ? 200 : 401 };
    },
  };
  const chrome = {
    runtime: { lastError: null },
    storage: {
      local: {
        get: (k, cb) => cb({ tlnd_auth: store.tlnd_auth }),
        set: (o, cb) => { Object.assign(store, o); cb && cb(); },
        remove: (k, cb) => { delete store.tlnd_auth; cb && cb(); },
      },
      onChanged: { addListener() {} },
    },
  };
  const ctx = vm.createContext({ window: win, chrome, atob: (s) => Buffer.from(s, "base64").toString("binary"),
    console: { warn() {}, info() {}, log() {} }, setTimeout: (fn) => { fn(); return 0; }, Date, JSON, Promise,
    CustomEvent: class { constructor(t) { this.type = t; } } });
  vm.runInContext(read("api/auth.js"), ctx);
  return { auth: win.tlndAuth, store, events, calls };
}

const ok = (access) => async (store) => {
  store.__fresh = true;
  return { ok: true, status: 200, json: async () => ({ accessToken: access, refreshToken: "r1" }) };
};

test("BE đang khởi động lại (refresh 502) lúc đọc giọng nói → GIỮ phiên", async () => {
  const h = harness(async () => ({ ok: false, status: 502 }));
  await h.auth.getAccessToken();
  assert.ok(h.store.tlnd_auth, "không được xoá token vì BE chập chờn");
  assert.deepEqual(h.events, []);
});

test("mất mạng lúc làm mới trong authFetch → GIỮ phiên, trả lỗi cho nơi gọi", async () => {
  const h = harness(async () => { throw new TypeError("Failed to fetch"); });
  const res = await h.auth.authFetch("https://be.test/api/v1/x");
  assert.equal(res.status, 401);
  assert.ok(h.store.tlnd_auth);
  assert.deepEqual(h.events, []);
});

test("BE từ chối refresh token (401) → đăng xuất + bật màn đăng nhập", async () => {
  const h = harness(async () => ({ ok: false, status: 401 }));
  await h.auth.getAccessToken();
  assert.equal(h.store.tlnd_auth, undefined);
  assert.deepEqual(h.events, ["tlnd-auth-required"]);
});

test("TTS + nghe + chat cùng cần token mới → CHỈ một lượt làm mới", async () => {
  const now = Math.floor(Date.now() / 1000);
  const h = harness(ok(jwt(now, now + 3600)));
  await Promise.all([h.auth.getAccessToken(), h.auth.getAccessToken(), h.auth.authFetch("https://be.test/api/v1/x")]);
  assert.equal(h.calls.filter((c) => c.url.endsWith("/auth/refresh")).length, 1);
  assert.equal(h.store.tlnd_auth.refresh, "r1");
});

test("máy chạy sai giờ (nhanh 3 giờ) không làm mới token vừa nhận", async () => {
  const now = Math.floor(Date.now() / 1000);              // giờ server
  const h = harness(ok(jwt(now, now + 3600)));
  const realNow = Date.now;
  Date.now = () => realNow() + 3 * 3600 * 1000;           // đồng hồ máy quầy nhanh 3 giờ
  try {
    await h.auth.getAccessToken();                         // token cũ hết hạn → làm mới (1 lần)
    assert.ok(h.store.tlnd_auth.obtained_at && h.store.tlnd_auth.ttl_s === 3600);
    const before = h.calls.length;
    // So exp (giờ server) với giờ máy thì token mới cũng "đã hết hạn" → làm mới mỗi lượt giọng nói.
    await h.auth.getAccessToken();
    await h.auth.getAccessToken();
    assert.equal(h.calls.length, before, "không làm mới lại token vừa nhận");
  } finally {
    Date.now = realNow;
  }
});

test("tắt server phụ (khác database)", () => {
  assert.match(read("api/config.js"), /const TLND_FALLBACK_BASE_URL = "";/);
});
