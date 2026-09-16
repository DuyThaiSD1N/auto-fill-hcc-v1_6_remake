const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const source = fs.readFileSync(path.join(root, "background.js"), "utf8");
const storage = {};
const listeners = [];
const removedListeners = [];
const createdTabs = [];
const order = [];
let nextTabId = 100;

const chrome = {
  action: { onClicked: { addListener() {} } },
  storage: {
    onChanged: { addListener() {} },
    local: {
      async get(keys) {
        if (typeof keys === "string") return { [keys]: storage[keys] };
        const out = {};
        for (const key of Array.isArray(keys) ? keys : Object.keys(storage)) out[key] = storage[key];
        return out;
      },
      async set(values) { Object.assign(storage, values); order.push("storage-set"); },
      async remove(keys) {
        for (const key of Array.isArray(keys) ? keys : [keys]) delete storage[key];
      },
    },
  },
  tabs: {
    onRemoved: { addListener(fn) { removedListeners.push(fn); } },
    onCreated: { addListener() {} },
    async create(options) {
      const tab = { id: nextTabId++, ...options };
      createdTabs.push(tab);
      order.push("tab-create");
      return tab;
    },
    async update(tabId, options) { order.push("tab-navigate"); return { id: tabId, ...options }; },
    async get(tabId) { return { id: tabId }; },
    async reload() {},
    async remove() {},
    async sendMessage() {},
  },
  runtime: {
    onMessage: { addListener(fn) { listeners.push(fn); } },
    onConnect: { addListener() {} },
    lastError: null,
    sendMessage() {},
    // Tự cập nhật + công tắc khung (scan-bridge): background đăng ký thêm các sự kiện này lúc nạp.
    onInstalled: { addListener() {} },
    onStartup: { addListener() {} },
    getManifest() { return { version: "0.0.0-test" }; },
  },
  alarms: { onAlarm: { addListener() {} }, async create() {} },
  offscreen: { async hasDocument() { return false; }, async createDocument() {}, async closeDocument() {} },
};

const context = {
  chrome,
  console,
  setTimeout(callback) { callback(); return 0; },
  clearTimeout() {},
  Promise,
  Date,
  Number,
  Array,
  String,
  fetch: async () => { throw new Error("unexpected fetch"); },
};
// background.js nạp lib bằng importScripts như service worker thật → chạy file đó trong CÙNG context.
context.importScripts = (...files) => {
  for (const file of files) vm.runInContext(fs.readFileSync(path.join(root, file), "utf8"), context);
};
vm.runInNewContext(source, context);

function dispatch(message, tabId = null) {
  return new Promise((resolve, reject) => {
    let handled = false;
    let settled = false;
    const sender = tabId == null ? {} : { tab: { id: tabId } };
    for (const listener of listeners) {
      const returned = listener(message, sender, (response) => {
        if (settled) return;
        settled = true;
        resolve(response);
      });
      if (returned === true) handled = true;
    }
    if (!handled && !settled) reject(new Error(`Không có handler cho ${message.action}`));
  });
}

function bundle(ordinal) {
  return {
    ordinal,
    url: `https://example.test/dossier-${ordinal}`,
    files: [{ name: `file-${ordinal}.pdf`, dataUrl: "data:application/pdf;base64,AA==" }],
    attachments: [{ fileIndex: 0, componentIndex: 1 }],
    procedure: "chung-thuc-ban-sao",
  };
}

(async () => {
  storage.tro_ly_split_attach_queue_stage = { items: [bundle(2), bundle(3)] };
  const started = await dispatch({
    action: "startSplitAttachQueue",
    queueId: "queue-1",
    total: 3,
    initialResults: [{ ok: true, ordinal: 1 }],
    itemsStorageKey: "tro_ly_split_attach_queue_stage",
  });
  assert.equal(started.ok, true);
  assert.equal(storage.tro_ly_split_attach_queue_stage, undefined);
  assert.equal(createdTabs.length, 1, "khởi động chỉ mở một tab");
  assert.equal(createdTabs[0].active, true, "tab xử lý phải active");
  assert.ok(order.lastIndexOf("storage-set") < order.lastIndexOf("tab-navigate"),
    "pending và queue phải được lưu trước khi điều hướng");
  assert.equal(storage.tro_ly_split_attach_queue.activeTabId, createdTabs[0].id);

  await dispatch({ action: "clearPendingAttach" }, createdTabs[0].id);
  assert.equal(createdTabs.length, 2, "xong tab trước mới mở tab sau");
  await dispatch({ action: "failPendingAttach", code: "test", error: "lỗi thử" }, createdTabs[1].id);

  const status = await dispatch({ action: "getSplitAttachQueueStatus", queueId: "queue-1" });
  assert.equal(status.status, "done");
  assert.equal(status.total, 3);
  assert.equal(status.succeeded, 2);
  assert.equal(status.failed, 1);
  assert.equal(storage.tro_ly_split_attach_queue.remaining.length, 0,
    "queue terminal chỉ giữ summary nhẹ, không giữ dataUrl");
  console.log("TLND split queue runtime passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
