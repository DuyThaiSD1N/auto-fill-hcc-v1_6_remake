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
  "https://dichvucongnnmt.mae.gov.vn/*",
  "https://dvc.moet.gov.vn/*",
  "https://dvc.moc.gov.vn/*",
];

test("manifest cấp đủ quyền cookie cho các miền đăng nhập công dân", () => {
  assert.ok(manifest.permissions.includes("cookies"));
  assert.ok(manifest.permissions.includes("browsingData"));
  for (const permission of COOKIE_HOST_PERMISSIONS) {
    assert.ok(manifest.host_permissions.includes(permission), `thiếu ${permission}`);
  }
});

test("quyền RỘNG ở manifest không được nới phạm vi XÓA cookie", () => {
  // Chủ đích: giữ https://*.gov.vn/* để cổng gov mới không phải sửa manifest — mỗi lần đổi
  // permissions là Chrome tắt extension của toàn bộ máy đã cài cho tới khi cán bộ bấm duyệt lại.
  // Đánh đổi: quyền đọc/xóa cookie trải rộng mọi miền chính phủ, nên hàng rào thật phải nằm ở
  // code: chỉ miền đơn vị của cổng công dân đã đi qua + DVCQG, không bao giờ gov.vn trần.
  assert.ok(manifest.host_permissions.includes("https://*.gov.vn/*"));
  const { context } = createBackgroundRuntime();
  assert.equal(context.citizenUnitDomain("dichvucongbyt.moh.gov.vn"), "moh.gov.vn");
  assert.equal(context.citizenUnitDomain("sso-dvc.moh.gov.vn"), "moh.gov.vn");
  assert.equal(context.citizenUnitDomain("lienthong.dichvucong.gov.vn"), "dichvucong.gov.vn");
  assert.equal(context.citizenUnitDomain("dichvucong.gov.vn"), "dichvucong.gov.vn");
  assert.equal(context.citizenUnitDomain("gov.vn"), "");
  assert.equal(context.citizenUnitDomain(".gov.vn"), "");
  assert.equal(context.citizenUnitDomain("trolyhoso-hcc.tiengnoi.vn"), "");
  assert.equal(context.citizenGovHost("https://trolyhoso-hcc.tiengnoi.vn/x"), "");
  assert.equal(context.citizenGovHost("http://dichvucong.gov.vn/"), "", "chỉ nhận https");
  const fixed = background.slice(
    background.indexOf("const DVCQG_LOGOUT_DOMAINS"),
    background.indexOf("const CITIZEN_VISITED_KEY"),
  );
  assert.doesNotMatch(fixed, /tiengnoi\.vn|vnekyc\.vn/);
});

function createBackgroundRuntime({ getPartitionKey, breakPartitionQuery = false } = {}) {
  const listeners = [];
  const queries = [];
  const removals = [];
  const browsingDataRemovals = [];
  const contentMessages = [];
  const tabUpdates = [];
  const store = {};
  const availableCookies = [{
      name: "dvc-session", domain: ".dichvucong.gov.vn", path: "/", secure: true, storeId: "0",
    }, {
      name: "sso-session", domain: ".dancuquocgia.gov.vn", path: "/auth", secure: true, storeId: "0",
    }, {
      name: "justice-session", domain: "dichvucongnganhtuphap.moj.gov.vn", path: "/", secure: true, storeId: "0",
    }, {
      name: "KEYCLOAK_IDENTITY", domain: "sso-dvc.moh.gov.vn", path: "/auth/realms/x", secure: true, storeId: "0",
    }, {
      name: "SESSIONID", domain: "dichvucongbyt.moh.gov.vn", path: "/", secure: false, storeId: "0",
    }, {
      name: "DVC-LIENTHONG", domain: "lienthong.dichvucong.gov.vn", path: "/", secure: true,
      storeId: "0", partitionKey: { topLevelSite: "https://dichvucong.gov.vn" },
    }, {
      name: "gov-wide", domain: ".gov.vn", path: "/", secure: true, storeId: "0",
    }, {
      name: "staff-session", domain: "trolyao.tiengnoi.vn", path: "/", secure: true, storeId: "0",
    }];
  const chrome = {
    action: { onClicked: { addListener() {} } },
    cookies: {
      async getAllCookieStores() { return [{ id: "0", tabIds: [77] }]; },
      // Hình dạng THẬT của Chrome: BAO NGOÀI { partitionKey: {...} }. Bản giả cũ trả thẳng
      // CookiePartitionKey nên che mất lỗi làm cả lượt dọn phiên công dân đổ vỡ trên máy thật.
      getPartitionKey: getPartitionKey || (async () => ({
        partitionKey: { topLevelSite: "https://dichvucong.gov.vn", hasCrossSiteAncestor: false },
      })),
      // Chrome kiểm tra tham số và ném ĐỒNG BỘ (không trả promise bị từ chối) khi hình dạng sai.
      getAll(details) {
        for (const key of Object.keys(details)) {
          if (!["storeId", "partitionKey", "url", "name", "domain", "path", "secure", "session"].includes(key)) {
            throw new TypeError(`Error at parameter 'details': Unexpected property: '${key}'.`);
          }
        }
        if (details.partitionKey && "partitionKey" in details.partitionKey) {
          throw new TypeError("Error at property 'partitionKey': Unexpected property: 'partitionKey'.");
        }
        if (breakPartitionQuery && details.partitionKey) {
          throw new TypeError("Error at property 'partitionKey': hình dạng không hợp lệ.");
        }
        queries.push(details);
        return Promise.resolve(details.partitionKey
          ? availableCookies.filter((cookie) => cookie.partitionKey)
          : availableCookies.filter((cookie) => !cookie.partitionKey));
      },
      async remove(details) {
        removals.push(details);
        return { name: details.name };
      },
    },
    browsingData: {
      async remove(options, dataTypes) { browsingDataRemovals.push({ options, dataTypes }); },
    },
    storage: {
      onChanged: { addListener() {} },
      local: {
        async get(keys) {
          const out = {};
          for (const key of [].concat(keys || [])) if (key in store) out[key] = JSON.parse(JSON.stringify(store[key]));
          return out;
        },
        async set(obj) { Object.assign(store, JSON.parse(JSON.stringify(obj))); },
        async remove() {},
      },
    },
    tabs: {
      onRemoved: { addListener() {} },
      onCreated: { addListener() {} },
      async query() {
        return [
          { id: 77, url: "https://dichvucongbyt.moh.gov.vn/vi/padsvc/apply-online/abc" },
          { id: 88, url: "https://lienthong.dichvucong.gov.vn/#/ke-khai/1.001193" },
          { id: 99, url: "https://dichvucongnganhtuphap.moj.gov.vn/nop-ho-so/1" },
        ];
      },
      async sendMessage(tabId, message) { contentMessages.push({ tabId, message }); },
      async update(tabId, props) { tabUpdates.push({ tabId, props }); },
      async create() {}, async get() {}, async reload() {}, async remove() {},
    },
    runtime: {
      onMessage: { addListener(fn) { listeners.push(fn); } },
      onConnect: { addListener() {} }, lastError: null, sendMessage() {},
      onInstalled: { addListener() {} },
      onStartup: { addListener() {} },
    },
    alarms: { onAlarm: { addListener() {} }, async create() {} },
    offscreen: { async hasDocument() { return false; }, async createDocument() {}, async closeDocument() {} },
  };

  const context = {
    chrome, console, setTimeout, clearTimeout, Promise, Date, Number, Array, String, URL, Object, JSON,
    fetch: async () => { throw new Error("unexpected fetch"); },
  };
  // background.js nạp lib bằng importScripts như service worker thật → chạy file đó trong CÙNG context.
  context.importScripts = (...files) => {
    for (const file of files) vm.runInContext(fs.readFileSync(path.join(root, file), "utf8"), context);
  };
  vm.runInNewContext(background, context);

  // Cổng công dân đi qua: tab 77 có hồ sơ (journey), tab 88 mở ra từ tab 77, tab 99 là cán bộ tự
  // mở (không hồ sơ) → không được ghi.
  store.tlnd_journey = { 77: { conversation_id: "c-1" } };
  const visit = async (url, tab) => {
    for (const listener of listeners) listener({ __tlnd: "citizenPortalVisit" }, { url, tab }, () => {});
    await new Promise((resolve) => setTimeout(resolve, 5));
  };
  const visitAll = async () => {
    await visit("https://dichvucongbyt.moh.gov.vn/vi/padsvc/apply-online/abc", { id: 77 });
    await visit("https://sso-dvc.moh.gov.vn/auth/realms/x/login", { id: 77 });
    await visit("https://lienthong.dichvucong.gov.vn/#/ke-khai/1.001193", { id: 88, openerTabId: 77 });
    await visit("https://dichvucongnganhtuphap.moj.gov.vn/nop-ho-so/1", { id: 99 });
  };

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
  return { context, store, dispatch, visitAll, queries, removals, browsingDataRemovals, contentMessages, tabUpdates };
}

test("background chỉ xóa phiên ở cổng công dân đã đi qua (kể cả miền SSO cùng đơn vị) + DVCQG", async () => {
  const runtime = createBackgroundRuntime();
  await runtime.visitAll();
  assert.deepEqual(Object.keys(runtime.store.tlnd_citizen_visited_hosts).sort(), [
    "dichvucongbyt.moh.gov.vn", "lienthong.dichvucong.gov.vn", "sso-dvc.moh.gov.vn",
  ], "tab cán bộ tự mở (không có hồ sơ) không được ghi");

  const result = await runtime.dispatch({ action: "clearCitizenDvcCookies" });
  // scopes = số miền đơn vị: dichvucong.gov.vn, dancuquocgia.gov.vn, moh.gov.vn.
  assert.deepEqual(JSON.parse(JSON.stringify(result)), {
    ok: true, scopes: 3, found: 5, removed: 5, failed: 0, failedQueries: 0,
    storageCleared: true, storageError: "", clearedTabs: 2, failedTabs: 0,
  });
  assert.equal(runtime.queries.length, 2, "quét cookie thường và partition hiện tại");
  assert.ok(runtime.queries.every((query) => query.storeId === "0"));
  assert.ok(runtime.removals.every((details) => details.storeId === "0"));
  const removed = runtime.removals.map((details) => details.name).sort();
  for (const name of ["dvc-session", "sso-session", "KEYCLOAK_IDENTITY", "SESSIONID", "DVC-LIENTHONG"]) {
    assert.ok(removed.includes(name), `phải xóa ${name}`);
  }
  for (const name of ["justice-session", "staff-session", "gov-wide"]) {
    assert.equal(removed.includes(name), false, `không được xóa ${name}`);
  }
  assert.ok(runtime.removals.some((details) => details.url === "https://sso.dancuquocgia.gov.vn/auth"),
    "cookie miền cha của VNeID phải được xóa qua đúng host SSO");
  assert.ok(runtime.removals.some((details) => details.url === "https://sso-dvc.moh.gov.vn/auth/realms/x"),
    "phiên SSO của cổng iGate (miền riêng cùng đơn vị) phải bị xóa");
  assert.ok(runtime.removals.some((details) => details.url === "https://dichvucongbyt.moh.gov.vn/"),
    "cookie không-Secure vẫn phải xóa qua URL HTTPS");
  assert.deepEqual(
    JSON.parse(JSON.stringify(runtime.removals.find((details) => details.name === "DVC-LIENTHONG").partitionKey)),
    { topLevelSite: "https://dichvucong.gov.vn" },
  );
  assert.equal(JSON.stringify(result).includes("session"), false, "response không được lộ tên cookie");

  const origins = runtime.browsingDataRemovals[0].options.origins;
  for (const origin of [
    "https://dichvucong.gov.vn", "https://lienthong.dichvucong.gov.vn", "https://sso.dancuquocgia.gov.vn",
    "https://dichvucongbyt.moh.gov.vn", "https://sso-dvc.moh.gov.vn",
  ]) assert.ok(origins.includes(origin), `thiếu ${origin}`);
  assert.equal(origins.some((origin) => origin.includes("moj.gov.vn")), false, "không đụng cổng chưa đi qua");
  assert.deepEqual(JSON.parse(JSON.stringify(runtime.browsingDataRemovals[0].dataTypes)),
    { localStorage: true, indexedDB: true });

  // Xóa TRONG trang (cả localStorage) ở tab thuộc phạm vi; tab cán bộ (moj) không đụng.
  assert.deepEqual(JSON.parse(JSON.stringify(runtime.contentMessages)), [
    { tabId: 77, message: { action: "clearCitizenPortalSessionStorage", localStorage: true } },
    { tabId: 88, message: { action: "clearCitizenPortalSessionStorage", localStorage: true } },
  ]);
  // Tab Liên thông khác đang mở → về trang chủ DVCQG; tab đang làm do sidebar tự điều hướng.
  assert.deepEqual(JSON.parse(JSON.stringify(runtime.tabUpdates)), [
    { tabId: 88, props: { url: "https://dichvucong.gov.vn/" } },
  ]);
  assert.deepEqual(runtime.store.tlnd_citizen_visited_hosts, {}, "dọn xong phải quên các cổng đã đi qua");
});

test("chưa đi qua cổng nào vẫn đăng xuất DVCQG + VNeID", async () => {
  const runtime = createBackgroundRuntime();
  const result = await runtime.dispatch({ action: "clearCitizenDvcCookies" });
  assert.equal(result.scopes, 2);
  const removed = runtime.removals.map((details) => details.name);
  assert.ok(removed.includes("dvc-session") && removed.includes("sso-session") && removed.includes("DVC-LIENTHONG"));
  assert.equal(removed.includes("KEYCLOAK_IDENTITY"), false);
});

test("một lượt quét cookie hỏng KHÔNG được kéo sập cả việc dọn phiên", async () => {
  // Ca thật trên máy cán bộ: getAll ném đồng bộ vì hình dạng partitionKey sai → cả hàm đổ vỡ,
  // 0 cookie bị xóa, công dân trước vẫn đăng nhập nguyên trên cổng. Quét thường phải sống sót.
  const runtime = createBackgroundRuntime({
    getPartitionKey: async () => ({ partitionKey: { topLevelSite: "https://dichvucong.gov.vn" } }),
    breakPartitionQuery: true,
  });
  await runtime.visitAll();
  const result = await runtime.dispatch({ action: "clearCitizenDvcCookies" });
  assert.equal(result.ok, false, "phải báo chưa sạch để sidebar cảnh báo cán bộ");
  assert.equal(result.failedQueries, 1);
  // 4 cookie công dân không phân vùng trong phạm vi; cookie phân vùng mất theo lượt quét hỏng.
  assert.equal(result.removed, 4, "vẫn phải xóa được cookie không phân vùng");
  assert.equal(result.storageCleared, true, "localStorage/indexedDB vẫn phải được dọn");
});

test("sidebar chỉ xóa cookie khi tự kết thúc một hồ sơ đã nộp thành công", () => {
  const start = sidebar.indexOf("async function clearCitizenSessionAndGoHome()");
  const end = sidebar.indexOf("// 🔄 Trò chuyện mới", start);
  const returnFlow = sidebar.slice(start, end);
  assert.ok(start > 0, "phải có hàm dọn phiên công dân tách riêng");
  assert.match(returnFlow, /reason === "completed"/);
  assert.ok(
    returnFlow.indexOf('action: "clearCitizenDvcCookies"')
      < returnFlow.indexOf('action: "navigate", url: DVC_HOME_URL'),
    "phải xóa phiên công dân trước khi điều hướng về DVCQG",
  );
  assert.doesNotMatch(returnFlow, /reloadAfterCitizenLogout/);
  assert.doesNotMatch(returnFlow, /reason === "idle"[\s\S]*clearCitizenDvcCookies/);
});

test("một bước dọn hỏng KHÔNG được làm lỡ việc xóa phiên công dân", () => {
  // Ca thật: cả thân returnToStart nằm trong try…finally KHÔNG có catch, khối xóa cookie nằm
  // CUỐI — deleteConversation/showStartScreen ném lỗi là nhảy thẳng ra finally, bỏ qua việc
  // xóa phiên, không một dòng cảnh báo. Công dân sau ngồi vào máy còn nguyên đăng nhập.
  const start = sidebar.indexOf('async function returnToStart(reason = "manual"');
  const end = sidebar.indexOf("// 🔄 Trò chuyện mới", start);
  const body = sidebar.slice(start, end);
  assert.match(body, /\} catch \(error\) \{[\s\S]{0,400}?Lỗi khi kết thúc phiên/);
  assert.match(
    body,
    /\} finally \{[\s\S]{0,600}?if \(reason === "completed"\)[\s\S]{0,200}?await clearCitizenSessionAndGoHome\(\)/,
    "việc xóa phiên công dân phải nằm trong finally",
  );
  assert.ok(
    body.indexOf("await clearCitizenSessionAndGoHome()") < body.indexOf("endingSession = false"),
    "phải dọn xong mới mở khóa cho lượt kết thúc phiên tiếp theo",
  );
});

test("content chỉ xóa sessionStorage của cổng khi nhận lệnh kết thúc và giữ trạng thái panel", () => {
  const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
  assert.match(content, /action === "clearCitizenPortalSessionStorage" && IS_TOP_FRAME/);
  assert.match(content, /panelState = sessionStorage\.getItem\(SS_OPEN_KEY\)/);
  assert.match(content, /sessionStorage\.clear\(\)/);
  assert.match(content, /if \(msg\.localStorage\) localStorage\.clear\(\)/);
  assert.match(content, /__tlnd: "citizenPortalVisit"/);
  assert.match(content, /sessionStorage\.setItem\(SS_OPEN_KEY, panelState\)/);
  assert.doesNotMatch(content, /reloadAfterCitizenLogout/);
});
