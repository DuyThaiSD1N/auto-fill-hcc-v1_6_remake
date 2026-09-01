const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));
const background = fs.readFileSync(path.join(root, "background.js"), "utf8");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");

const COOKIE_HOST_PERMISSIONS = [
  "https://dichvucong.gov.vn/*",
  "https://*.dichvucong.gov.vn/*",
  "https://sso.dancuquocgia.gov.vn/*",
  "https://dichvucongnganhtuphap.moj.gov.vn/*",
  "https://tokhaidientu.moj.gov.vn/*",
];

test("manifest chỉ cấp quyền cookie cho các miền đăng nhập công dân cần thiết", () => {
  assert.ok(manifest.permissions.includes("cookies"));
  assert.ok(manifest.permissions.includes("browsingData"));
  for (const permission of COOKIE_HOST_PERMISSIONS) {
    assert.ok(manifest.host_permissions.includes(permission), `thiếu ${permission}`);
  }
  assert.ok(!manifest.host_permissions.includes("https://*.gov.vn/*"));
  assert.ok(!manifest.host_permissions.includes("https://*.moj.gov.vn/*"));
});

function createBackgroundRuntime() {
  const listeners = [];
  const queries = [];
  const removals = [];
  const browsingDataRemovals = [];
  const contentMessages = [];
  const availableCookies = [{
      name: "dvc-session", domain: ".dichvucong.gov.vn", path: "/", secure: true, storeId: "0",
    }, {
      name: "sso-session", domain: ".dancuquocgia.gov.vn", path: "/auth", secure: true, storeId: "0",
    }, {
      name: "justice-session", domain: "dichvucongnganhtuphap.moj.gov.vn", path: "/", secure: true,
      storeId: "0", partitionKey: { topLevelSite: "https://dichvucong.gov.vn" },
    }, {
      name: "tokhai-session", domain: "tokhaidientu.moj.gov.vn", path: "/", secure: false, storeId: "0",
    }, {
      name: "staff-session", domain: "trolyao.tiengnoi.vn", path: "/", secure: true, storeId: "0",
    }];
  const chrome = {
    action: { onClicked: { addListener() {} } },
    cookies: {
      async getAllCookieStores() { return [{ id: "0", tabIds: [77] }]; },
      async getPartitionKey() { return { topLevelSite: "https://dichvucong.gov.vn" }; },
      async getAll(details) {
        queries.push(details);
        return details.partitionKey
          ? availableCookies.filter((cookie) => cookie.partitionKey)
          : availableCookies.filter((cookie) => !cookie.partitionKey);
      },
      async remove(details) {
        removals.push(details);
        return { name: details.name };
      },
    },
    browsingData: {
      async remove(options, dataTypes) { browsingDataRemovals.push({ options, dataTypes }); },
    },
    storage: { local: { async get() { return {}; }, async set() {}, async remove() {} } },
    tabs: {
      onRemoved: { addListener() {} },
      async query() { return [{ id: 77 }, { id: 88 }]; },
      async sendMessage(tabId, message) { contentMessages.push({ tabId, message }); },
      async create() {}, async update() {}, async get() {}, async reload() {}, async remove() {},
    },
    runtime: {
      onMessage: { addListener(fn) { listeners.push(fn); } },
      onConnect: { addListener() {} }, lastError: null, sendMessage() {},
    },
    offscreen: { async hasDocument() { return false; }, async createDocument() {}, async closeDocument() {} },
  };

  vm.runInNewContext(background, {
    chrome, console, setTimeout, clearTimeout, Promise, Date, Number, Array, String,
    fetch: async () => { throw new Error("unexpected fetch"); },
  });

  const dispatch = (message, tabId = 77) => new Promise((resolve, reject) => {
    let handled = false;
    let settled = false;
    for (const listener of listeners) {
      const returned = listener(message, { tab: { id: tabId } }, (response) => {
        if (settled) return;
        settled = true;
        resolve(response);
      });
      if (returned === true) handled = true;
    }
    if (!handled && !settled) reject(new Error(`Không có handler cho ${message.action}`));
  });
  return { dispatch, queries, removals, browsingDataRemovals, contentMessages };
}

test("background xóa cookie DVCQG, VNeID và Tư pháp trong đúng cookie store", async () => {
  const runtime = createBackgroundRuntime();
  const result = await runtime.dispatch({ action: "clearCitizenDvcCookies" });

  assert.deepEqual(JSON.parse(JSON.stringify(result)), {
    ok: true, scopes: 4, found: 4, removed: 4, failed: 0, failedQueries: 0,
    storageCleared: true, storageError: "", clearedTabs: 2, failedTabs: 0,
  });
  assert.equal(runtime.queries.length, 2, "quét cookie thường và partition hiện tại");
  assert.ok(runtime.queries.every((query) => query.storeId === "0"));
  assert.ok(runtime.removals.every((details) => details.storeId === "0"));
  assert.ok(runtime.removals.some((details) => details.url === "https://dichvucong.gov.vn/"));
  assert.ok(runtime.removals.some((details) => details.url === "https://sso.dancuquocgia.gov.vn/auth"),
    "cookie miền cha của VNeID phải được xóa qua đúng host SSO đã cấp quyền");
  assert.ok(runtime.removals.some((details) => details.url === "https://tokhaidientu.moj.gov.vn/"),
    "cookie không-Secure vẫn phải xóa qua URL HTTPS");
  assert.deepEqual(
    JSON.parse(JSON.stringify(runtime.removals.find((details) => details.name === "justice-session").partitionKey)),
    { topLevelSite: "https://dichvucong.gov.vn" },
  );
  assert.equal(runtime.removals.some((details) => details.name === "staff-session"), false,
    "không được xóa cookie đăng nhập hệ thống Trợ lý");
  assert.equal(JSON.stringify(result).includes("session"), false, "response không được lộ tên cookie");
  assert.deepEqual(JSON.parse(JSON.stringify(runtime.browsingDataRemovals)), [{
    options: { origins: [
      "https://dichvucong.gov.vn",
      "https://lienthong.dichvucong.gov.vn",
      "https://sso.dancuquocgia.gov.vn",
      "https://dichvucongnganhtuphap.moj.gov.vn",
      "https://tokhaidientu.moj.gov.vn",
    ] },
    dataTypes: { localStorage: true, indexedDB: true },
  }]);
  assert.deepEqual(runtime.contentMessages.map((entry) => entry.message.action), [
    "clearCitizenPortalSessionStorage", "clearCitizenPortalSessionStorage",
  ]);
});

test("sidebar chỉ xóa cookie khi tự kết thúc một hồ sơ đã nộp thành công", () => {
  const start = sidebar.indexOf('async function returnToStart(reason = "manual")');
  const end = sidebar.indexOf("// 🔄 Trò chuyện mới", start);
  const returnFlow = sidebar.slice(start, end);
  assert.match(returnFlow, /reason === "completed"/);
  assert.match(returnFlow, /if \(shouldClearCitizenCookies\)[\s\S]*action: "clearCitizenDvcCookies"/);
  assert.match(returnFlow, /action: "clearCitizenDvcCookies"[\s\S]*action: "navigate", url: DVC_HOME_URL/);
  assert.ok(
    returnFlow.indexOf('action: "clearCitizenDvcCookies"')
      < returnFlow.indexOf('action: "navigate", url: DVC_HOME_URL'),
    "phải xóa phiên công dân trước khi điều hướng về DVCQG",
  );
  assert.doesNotMatch(returnFlow, /reloadAfterCitizenLogout/);
  assert.doesNotMatch(returnFlow, /reason === "idle"[\s\S]*clearCitizenDvcCookies/);
});

test("content chỉ xóa sessionStorage của cổng khi nhận lệnh kết thúc và giữ trạng thái panel", () => {
  const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
  assert.match(content, /action === "clearCitizenPortalSessionStorage" && IS_TOP_FRAME/);
  assert.match(content, /panelState = sessionStorage\.getItem\(SS_OPEN_KEY\)/);
  assert.match(content, /sessionStorage\.clear\(\)/);
  assert.match(content, /sessionStorage\.setItem\(SS_OPEN_KEY, panelState\)/);
  assert.doesNotMatch(content, /reloadAfterCitizenLogout/);
});
