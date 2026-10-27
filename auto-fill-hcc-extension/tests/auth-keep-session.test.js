// "Tự đăng xuất giữa lúc làm hồ sơ": chỉ được về màn đăng nhập khi BE nói rõ phiên không còn
// (401/403 ở /auth/refresh). Mất mạng, BE đang khởi động lại (502/503), bảo trì… là lỗi TẠM — giữ token.
// Chạy THẬT api/client.js trong vm với fetch giả.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const read = (f) => fs.readFileSync(path.join(root, f), "utf8");
const clientSource = read("api/client.js");

function harness(routes) {
  let tokens = { accessToken: "a0", refreshToken: "r0" };
  const calls = [];
  const AuthStore = {
    getTokens: async () => (tokens ? { ...tokens } : null),
    saveTokens: async (t) => { tokens = { accessToken: t.accessToken, refreshToken: t.refreshToken }; },
    clearTokens: async () => { tokens = null; },
  };
  const fetch = async (url, init) => {
    const p = new URL(url).pathname;
    calls.push({ path: p, auth: init.headers?.Authorization });
    const out = await routes(p, init, { setTokens: (t) => { tokens = t; } });
    if (out === "network") throw new TypeError("Failed to fetch");
    return { ok: out.status >= 200 && out.status < 300, status: out.status, text: async () => JSON.stringify(out.body || {}) };
  };
  const ctx = vm.createContext({
    BACKEND_URL: "https://be.test", BACKEND_URL_FALLBACK: "", BACKEND_TIMEOUT_MS: 5000,
    BACKEND_FAILOVER_COOLDOWN_MS: 30000, AbortController, Date, JSON, Promise, console: { warn() {}, log() {} },
    setTimeout: (fn) => { fn(); return 0; }, clearTimeout() {}, AuthStore, fetch,
    chrome: { runtime: { lastError: null, sendMessage: (_m, cb) => cb(null) } },
  });
  vm.runInContext(clientSource + "\n;this.api = { apiCall, apiJson };", ctx);
  return { api: ctx.api, calls, tokens: () => tokens };
}

const expired = (p, init) => p === "/api/v1/x" && init.headers.Authorization === "Bearer a0" ? { status: 401 } : null;

test("BE đang khởi động lại (refresh 502) → báo lỗi tạm, GIỮ token", async () => {
  const h = harness((p, init) => expired(p, init) || (p === "/auth/refresh" ? { status: 502 } : { status: 200 }));
  await assert.rejects(h.api.apiCall("/api/v1/x"), (e) => e.transient === true && !e.unauthorized);
  assert.deepEqual(h.tokens(), { accessToken: "a0", refreshToken: "r0" });
});

test("mất mạng lúc làm mới → lỗi tạm, GIỮ token", async () => {
  const h = harness((p, init) => expired(p, init) || (p === "/auth/refresh" ? "network" : { status: 200 }));
  await assert.rejects(h.api.apiCall("/api/v1/x"), (e) => !e.unauthorized);
  assert.ok(h.tokens(), "không được xoá token vì mất mạng");
});

test("bảo trì (503 SYSTEM_MAINTENANCE) → giữ token, báo đúng câu của BE", async () => {
  const h = harness((p, init) => expired(p, init) || (p === "/auth/refresh"
    ? { status: 503, body: { message: "Hệ thống đang được tối ưu và nâng cấp. Vui lòng quay lại sau" } } : { status: 200 }));
  await assert.rejects(h.api.apiCall("/api/v1/x"), /tối ưu và nâng cấp/);
  assert.ok(h.tokens());
});

test("BE từ chối refresh token (401) và không ai làm mới thay → đăng xuất", async () => {
  const h = harness((p, init) => expired(p, init) || (p === "/auth/refresh" ? { status: 401 } : { status: 200 }));
  await assert.rejects(h.api.apiCall("/api/v1/x"), (e) => e.unauthorized === true);
  assert.equal(h.tokens(), null);
});

test("refresh bị từ chối nhưng tab khác vừa làm mới → dùng cặp mới, không đăng xuất", async () => {
  const h = harness((p, init, { setTokens }) => {
    if (expired(p, init)) return expired(p, init);
    if (p === "/auth/refresh") { setTokens({ accessToken: "a-tab2", refreshToken: "r-tab2" }); return { status: 401 }; }
    return { status: 200 };
  });
  const res = await h.api.apiCall("/api/v1/x");
  assert.equal(res.status, 200);
  assert.equal(h.calls.at(-1).auth, "Bearer a-tab2");
});

test("nhiều lời gọi cùng gặp 401 → CHỈ một lượt làm mới (không tự tranh chấp)", async () => {
  const h = harness((p, init) => expired(p, init)
    || (p === "/auth/refresh" ? { status: 200, body: { accessToken: "a1", refreshToken: "r1" } } : { status: 200 }));
  await Promise.all([h.api.apiCall("/api/v1/x"), h.api.apiCall("/api/v1/x"), h.api.apiCall("/api/v1/x")]);
  assert.equal(h.calls.filter((c) => c.path === "/auth/refresh").length, 1);
  assert.deepEqual(h.tokens(), { accessToken: "a1", refreshToken: "r1" });
});

test("panel dựng lại: chỉ xoá token khi phiên hết thật, lỗi khác thì giữ phiên + thử lại", () => {
  const popup = read("popup.js");
  const boot = popup.slice(popup.indexOf("async function bootstrap()"), popup.indexOf('const LAST_USER_KEY = "autofill_last_user"'));
  const clears = boot.split("await AuthStore.clearTokens();").length - 1;
  const guarded = (boot.match(/if \(e\?\.unauthorized\) \{\s*await AuthStore\.clearTokens\(\);/g) || []).length;
  assert.equal(clears, guarded, "mọi chỗ xoá token trong bootstrap phải nằm sau kiểm e?.unauthorized");
  assert.match(boot, /bootstrapRetryTimer = setTimeout\(\(\) => \{ void bootstrap\(\); \}, BOOTSTRAP_RETRY_MS\)/);
});

test("tắt server phụ (khác database → refresh token không tồn tại, dữ liệu ghi lệch)", () => {
  assert.match(read("api/config.js"), /const BACKEND_URL_FALLBACK = "";/);
});
