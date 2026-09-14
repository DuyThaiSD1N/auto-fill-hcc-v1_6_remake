const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const source = fs.readFileSync(path.join(root, "background.js"), "utf8");
const storage = {};
const createdTabs = [];
const updatedTabs = [];
let nextTabId = 100;
// Chrome gọi MỌI listener onMessage, kênh trả lời giữ mở nếu một listener trả true. Background có
// nhiều listener (scan-bridge thêm vài cái) → không được chỉ giữ listener đăng ký sau cùng.
const runtimeListeners = [];
const runtimeListener = (...args) => runtimeListeners.map((listener) => listener(...args)).includes(true);

const chrome = {
  action: { onClicked: { addListener() {} } },
  scripting: { async executeScript() {} },
  storage: {
    local: {
      async get(key) {
        if (typeof key === "string") return { [key]: storage[key] };
        return { ...storage };
      },
      async set(values) { Object.assign(storage, values); },
      async remove(keys) {
        for (const key of Array.isArray(keys) ? keys : [keys]) delete storage[key];
      },
    },
  },
  tabs: {
    onRemoved: { addListener() {} },
    async create(options) {
      const tab = { id: nextTabId++, ...options };
      createdTabs.push(tab);
      return tab;
    },
    async update(tabId, options) {
      updatedTabs.push({ tabId, ...options });
      return { id: tabId, ...options };
    },
    async get(tabId) { return { id: tabId }; },
    async reload() {},
    async remove() {},
    async sendMessage() {},
  },
  runtime: {
    onMessage: {
      addListener(listener) { runtimeListeners.push(listener); },
    },
    onConnect: { addListener() {} },
    // Tự cập nhật (scan-bridge): background đặt lịch kiểm bản mới và đọc version lúc nạp.
    onInstalled: { addListener() {} },
    onStartup: { addListener() {} },
    getManifest() { return { version: "0.0.0-test" }; },
  },
  alarms: { onAlarm: { addListener() {} }, async create() {} },
};

vm.runInNewContext(source, {
  chrome,
  console,
  // Không chờ 800 ms giữa hai tab trong unit test; production vẫn dùng setTimeout thật.
  setTimeout(callback) { callback(); return 0; },
  Promise,
  Date,
  Number,
  Array,
  String,
});

function dispatch(message, tabId = null) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const returned = runtimeListener(message, tabId == null ? {} : { tab: { id: tabId } }, (response) => {
      settled = true;
      resolve(response);
    });
    if (returned !== true && !settled) reject(new Error(`Message ${message.action} không giữ response async`));
  });
}

function bundle(ordinal) {
  return {
    ordinal,
    url: `https://example.test/dossier-${ordinal}`,
    files: [{ name: `file-${ordinal}.pdf`, dataUrl: "data:application/pdf;base64,AA==" }],
    attachments: [{ fileIndex: 0, componentIndex: 1 }],
    procedure: ordinal % 2 ? "chung-thuc-ban-sao" : "chung-thuc-chu-ky",
  };
}

(async () => {
  storage.autofill_split_attach_queue_stage = {
    items: [bundle(2), bundle(3)],
    stagedAt: Date.now(),
  };
  const started = await dispatch({
    action: "startSplitAttachQueue",
    itemsStorageKey: "autofill_split_attach_queue_stage",
    runId: "run-test-1",
    originTabId: 77,
    procedure: "chung-thuc-ban-sao",
    totalBundles: 3,
    initialCompleted: 1,
    initialSucceeded: 1,
  });
  assert.equal(started.ok, true);
  assert.equal(storage.autofill_split_attach_queue_stage, undefined, "Staging phải được dọn sau khi background nhận");
  assert.equal(createdTabs.length, 1, "Khởi động queue chỉ được mở một tab");
  assert.equal(createdTabs[0].active, true, "Tab đang đính kèm phải được activate");
  assert.equal(updatedTabs[0].active, true);
  assert.equal(storage.autofill_split_attach_queue.activeTabId, createdTabs[0].id);
  assert.equal(storage.autofill_split_attach_queue.remaining.length, 1);
  assert.equal(storage.autofill_split_attach_progress.status, "running");
  assert.equal(storage.autofill_split_attach_progress.completed, 1);
  assert.equal(storage.autofill_split_attach_progress.succeeded, 1);
  assert.equal(storage.autofill_split_attach_progress.activeOrdinal, 2);
  assert.equal(storage.autofill_split_attach_progress.originTabId, 77);

  await dispatch({
    action: "pausePendingAttach",
    code: "wallet-file-not-persisted",
    error: "test",
  }, createdTabs[0].id);
  assert.equal(createdTabs.length, 1, "Dòng chưa có file thật thì không được mở tab tiếp theo");
  assert.equal(storage.autofill_split_attach_queue.activeTabId, createdTabs[0].id);
  assert.equal(storage.autofill_split_attach_queue.paused.code, "wallet-file-not-persisted");
  assert.ok(storage.autofill_pending_attach[createdTabs[0].id], "Phải giữ pending để reload tab có thể thử lại");
  assert.equal(storage.autofill_split_attach_progress.status, "paused");
  assert.equal(storage.autofill_split_attach_progress.activeOrdinal, 2);

  await dispatch({ action: "clearPendingAttach" }, createdTabs[0].id);
  assert.equal(createdTabs.length, 2, "Chỉ sau khi tab đầu thành công mới được mở tab thứ hai");
  assert.equal(storage.autofill_split_attach_queue.activeTabId, createdTabs[1].id);
  assert.equal(storage.autofill_split_attach_queue.remaining.length, 0);
  assert.equal(storage.autofill_split_attach_progress.completed, 2);
  assert.equal(storage.autofill_split_attach_progress.succeeded, 2);
  assert.equal(storage.autofill_split_attach_progress.activeOrdinal, 3);

  await dispatch({ action: "failPendingAttach", code: "wallet-modal-not-opened", error: "test" }, createdTabs[1].id);
  assert.equal(createdTabs.length, 2, "Queue hết không được mở thêm tab");
  assert.equal(storage.autofill_split_attach_queue, undefined, "Queue phải được dọn khi xử lý xong");
  assert.equal(storage.autofill_split_attach_progress.status, "completed");
  assert.equal(storage.autofill_split_attach_progress.completed, 3);
  assert.equal(storage.autofill_split_attach_progress.succeeded, 2);
  assert.equal(storage.autofill_split_attach_progress.failed, 1);
  assert.doesNotMatch(JSON.stringify(storage.autofill_split_attach_progress), /dataUrl/,
    "Bản tổng kết không được giữ nội dung file");

  console.log("split queue runtime: one active tab at a time for copy/signature bundles passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
