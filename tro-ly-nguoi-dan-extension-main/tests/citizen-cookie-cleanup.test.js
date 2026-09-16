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
  // CITIZEN_COOKIE_HOSTS trong code, không dựa vào manifest.
  assert.ok(manifest.host_permissions.includes("https://*.gov.vn/*"));
  const hosts = background.slice(
    background.indexOf("const CITIZEN_COOKIE_HOSTS"),
    background.indexOf("]);", background.indexOf("const CITIZEN_COOKIE_HOSTS")),
  );
  assert.doesNotMatch(hosts, /\*/, "danh sách xóa cookie phải là host cụ thể, không ký tự đại diện");
  // Cookie đăng nhập của chính hệ thống Trợ lý tuyệt đối không nằm trong diện xóa.
  assert.doesNotMatch(hosts, /tiengnoi\.vn|vnekyc\.vn/);
});

function createBackgroundRuntime({ getPartitionKey, breakPartitionQuery = false } = {}) {
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

  // scopes = số host trong CITIZEN_COOKIE_HOSTS (cổng bộ ngành: NN&MT + GD&ĐT + Xây dựng
  // + cổng tỉnh Bắc Ninh).
  assert.deepEqual(JSON.parse(JSON.stringify(result)), {
    ok: true, scopes: 8, found: 4, removed: 4, failed: 0, failedQueries: 0,
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
      "https://dichvucongnnmt.mae.gov.vn",
      "https://dvc.moet.gov.vn",
      "https://dvc.moc.gov.vn",
      "https://dichvucong.bacninh.gov.vn",
    ] },
    dataTypes: { localStorage: true, indexedDB: true },
  }]);
  assert.deepEqual(runtime.contentMessages.map((entry) => entry.message.action), [
    "clearCitizenPortalSessionStorage", "clearCitizenPortalSessionStorage",
  ]);
});

test("một lượt quét cookie hỏng KHÔNG được kéo sập cả việc dọn phiên", async () => {
  // Ca thật trên máy cán bộ: getAll ném đồng bộ vì hình dạng partitionKey sai → cả hàm đổ vỡ,
  // 0 cookie bị xóa, công dân trước vẫn đăng nhập nguyên trên cổng. Quét thường phải sống sót.
  const runtime = createBackgroundRuntime({
    getPartitionKey: async () => ({ partitionKey: { topLevelSite: "https://dichvucong.gov.vn" } }),
    breakPartitionQuery: true,
  });
  const result = await runtime.dispatch({ action: "clearCitizenDvcCookies" });
  assert.equal(result.ok, false, "phải báo chưa sạch để sidebar cảnh báo cán bộ");
  assert.equal(result.failedQueries, 1);
  // 3 cookie công dân không phân vùng trong fixture; cookie phân vùng mất theo lượt quét hỏng.
  assert.equal(result.removed, 3, "vẫn phải xóa được cookie không phân vùng");
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
  const start = sidebar.indexOf('async function returnToStart(reason = "manual")');
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
  assert.match(content, /sessionStorage\.setItem\(SS_OPEN_KEY, panelState\)/);
  assert.doesNotMatch(content, /reloadAfterCitizenLogout/);
});
