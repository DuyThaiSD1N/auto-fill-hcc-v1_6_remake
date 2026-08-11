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
let runtimeListener = null;

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
      addListener(listener) { runtimeListener = listener; },
    },
  },
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
  const started = await dispatch({
    action: "startSplitAttachQueue",
    items: [bundle(2), bundle(3)],
  });
  assert.equal(started.ok, true);
  assert.equal(createdTabs.length, 1, "Khởi động queue chỉ được mở một tab");
  assert.equal(createdTabs[0].active, true, "Tab đang đính kèm phải được activate");
  assert.equal(updatedTabs[0].active, true);
  assert.equal(storage.autofill_split_attach_queue.activeTabId, createdTabs[0].id);
  assert.equal(storage.autofill_split_attach_queue.remaining.length, 1);

  await dispatch({ action: "clearPendingAttach" }, createdTabs[0].id);
  assert.equal(createdTabs.length, 2, "Chỉ sau khi tab đầu thành công mới được mở tab thứ hai");
  assert.equal(storage.autofill_split_attach_queue.activeTabId, createdTabs[1].id);
  assert.equal(storage.autofill_split_attach_queue.remaining.length, 0);

  await dispatch({ action: "failPendingAttach", code: "wallet-modal-not-opened", error: "test" }, createdTabs[1].id);
  assert.equal(createdTabs.length, 2, "Queue hết không được mở thêm tab");
  assert.equal(storage.autofill_split_attach_queue, undefined, "Queue phải được dọn khi xử lý xong");

  console.log("split queue runtime: one active tab at a time for copy/signature bundles passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
