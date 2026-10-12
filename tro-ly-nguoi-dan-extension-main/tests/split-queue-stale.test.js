// Hàng đợi tách hồ sơ nằm trong chrome.storage.local (sống qua tắt Chrome). Tab đang xử lý không báo
// xong → "running" kẹt mãi, mọi lượt tách sau bị từ chối "Đang có một lượt tách hồ sơ khác chưa hoàn
// tất" kể cả hồ sơ 1 tài liệu. Chạy THẬT background.js trong vm.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const source = fs.readFileSync(path.join(root, "background.js"), "utf8");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");

function loadBackground({ liveTabs = [] } = {}) {
  const storage = {};
  const listeners = [];
  const noop = { addListener() {} };
  const chrome = {
    action: { onClicked: noop },
    storage: {
      onChanged: noop,
      local: {
        async get(keys) {
          if (typeof keys === "string") return { [keys]: storage[keys] };
          const out = {};
          for (const k of Array.isArray(keys) ? keys : Object.keys(storage)) out[k] = storage[k];
          return out;
        },
        async set(v) { Object.assign(storage, v); },
        async remove(keys) { for (const k of Array.isArray(keys) ? keys : [keys]) delete storage[k]; },
      },
    },
    tabs: {
      onRemoved: noop, onCreated: noop, onUpdated: noop, onActivated: noop,
      async get(id) { if (!liveTabs.includes(id)) throw new Error(`No tab with id: ${id}`); return { id }; },
      async create(o) { return { id: 999, ...o }; }, async update() {}, async reload() {}, async remove() {},
      async sendMessage() {}, async query() { return []; },
    },
    runtime: {
      onMessage: { addListener(fn) { listeners.push(fn); } }, onConnect: noop, onInstalled: noop, onStartup: noop,
      lastError: null, sendMessage() {}, getManifest() { return { version: "0.0.0-test" }; },
    },
    alarms: { onAlarm: noop, async create() {} },
    offscreen: { async hasDocument() { return false; }, async createDocument() {}, async closeDocument() {} },
  };
  const context = {
    chrome, console: { log() {}, warn() {}, error() {}, info() {} },
    setTimeout(cb) { cb(); return 0; }, clearTimeout() {}, Promise, Date, Number, Array, String,
    fetch: async () => { throw new Error("unexpected fetch"); },
  };
  context.importScripts = (...files) => {
    for (const f of files) vm.runInContext(fs.readFileSync(path.join(root, f), "utf8"), context);
  };
  vm.runInNewContext(source, context);
  const dispatch = (message) => new Promise((resolve) => {
    for (const l of listeners) l(message, {}, resolve);
  });
  return { storage, dispatch };
}

const running = (over = {}) => ({
  queueId: "q-cu", status: "running", total: 2, remaining: [], results: [],
  activeTabId: 41, activeItem: { ordinal: 1 }, startedAt: Date.now(), updatedAt: Date.now(), ...over,
});

test("tab đang xử lý của lượt cũ không còn (vd tắt Chrome) → dọn, lượt mới chạy được", async () => {
  const { storage, dispatch } = loadBackground({ liveTabs: [] });
  storage.tro_ly_split_attach_queue = running();
  const res = await dispatch({ action: "prepareSplitAttachQueue" });
  assert.equal(res.ok, true);
  assert.equal(storage.tro_ly_split_attach_queue, undefined);
});

test("quá 30 phút không tiến triển → dọn dù tab còn mở", async () => {
  const { storage, dispatch } = loadBackground({ liveTabs: [41] });
  storage.tro_ly_split_attach_queue = running({ updatedAt: Date.now() - 31 * 60 * 1000 });
  assert.equal((await dispatch({ action: "prepareSplitAttachQueue" })).ok, true);
});

test("lượt đang chạy thật (tab còn, vừa tiến triển) → vẫn từ chối như cũ", async () => {
  const { storage, dispatch } = loadBackground({ liveTabs: [41] });
  storage.tro_ly_split_attach_queue = running();
  const res = await dispatch({ action: "prepareSplitAttachQueue" });
  assert.match(res.error, /lượt tách hồ sơ khác chưa hoàn tất/);
  assert.equal(storage.tro_ly_split_attach_queue.status, "running");
});

test("sidebar hết hạn chờ → bỏ đúng hàng đợi đó (khác queueId thì không đụng)", async () => {
  const { storage, dispatch } = loadBackground({ liveTabs: [41] });
  storage.tro_ly_split_attach_queue = running();
  storage.tro_ly_pending_attach = { 41: { files: [1] } };
  await dispatch({ action: "abandonSplitAttachQueue", queueId: "q-khac" });
  assert.equal(storage.tro_ly_split_attach_queue.status, "running");
  await dispatch({ action: "abandonSplitAttachQueue", queueId: "q-cu" });
  assert.equal(storage.tro_ly_split_attach_queue.status, "done");
  assert.equal(storage.tro_ly_pending_attach[41], undefined);
  assert.equal((await dispatch({ action: "prepareSplitAttachQueue" })).ok, true);
});

test("sidebar gọi abandonSplitAttachQueue ở nhánh hết hạn chờ", () => {
  assert.match(sidebar,
    /if \(Date\.now\(\) > deadline \|\| missingCount >= 10\) \{\s*setStatus\(""\);\s*await sendToBackground\(\{ action: "abandonSplitAttachQueue", queueId \}\);/);
});
