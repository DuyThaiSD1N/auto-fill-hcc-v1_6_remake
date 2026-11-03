// Đính tách nhiều tab dùng CHUNG khóa hồ sơ: chỉ hỏi đánh giá khi mọi TAB của lượt đã bấm nộp.
// Lỗi gốc: cú bấm ở tab đầu tiên đã đặt cờ hỏi đánh giá trong khi các tab khác còn chưa nộp.
// Chạy THẬT đoạn code của background.js trong vm với chrome + fetch giả.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const src = fs.readFileSync(path.join(root, "background.js"), "utf8");
const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");
const block = src.slice(
  src.indexOf('const SUBMIT_WATCH_KEY = "autofill_submit_watch";'),
  src.indexOf("chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {"),
);

function harness() {
  const store = {
    autofill_submit_watch: { base: "https://chinh", bases: ["https://chinh"] },
    auth_tokens: { accessToken: "a0", refreshToken: "r0" },
    autofill_session_7: { dossierId: "d1" },
    autofill_session_8: { dossierId: "d1" },
    autofill_session_9: { dossierId: "d1" },
  };
  const messages = [];
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
      onChanged: { addListener() {} },
    },
    alarms: { create() {}, onAlarm: { addListener() {} } },
    runtime: { onStartup: { addListener() {} }, sendMessage: async (m) => { messages.push(m); } },
  };
  const fetch = async () => ({ ok: true, status: 200, json: async () => ({}) });
  const ctx = vm.createContext({
    chrome, fetch, console: { warn() {}, log() {} }, crypto: { randomUUID: () => "uuid-" + Math.random() },
    setTimeout: (fn) => { fn(); return 0; }, clearTimeout() {}, AbortController, Date, JSON, Promise, Set, Number, String, Array, Object,
  });
  vm.runInContext(block + "\n;this.api = { reportDossierSubmitClick, startSplitSubmitBook, addSplitSubmitMember, noteSplitTabClosed };", ctx);
  const click = (tab) => ctx.api.reportDossierSubmitClick(tab, "h", "", "c-" + Math.random(), Date.now());
  return { api: ctx.api, store, messages, click, pending: () => store.autofill_rating_pending?.dossierId || null };
}

async function splitRun() {
  const h = harness();
  await h.api.startSplitSubmitBook([{ dossierId: "d1" }, { dossierId: "d1" }], 7, 3);
  await h.api.addSplitSubmitMember("d1", 8);
  await h.api.addSplitSubmitMember("d1", 9);
  return h;
}

test("tab đầu bấm nộp → chưa hỏi đánh giá, báo panel tiến độ 1/3", async () => {
  const h = await splitRun();
  await h.click(7);
  assert.equal(h.pending(), null);
  assert.equal(JSON.stringify(h.messages.at(-1).splitSubmit), JSON.stringify({ done: 1, total: 3 }));
});

test("một tab bấm nhiều lần chỉ tính một; tab cuối bấm thì mới hỏi", async () => {
  const h = await splitRun();
  await h.click(7);
  await h.click(8);
  await h.click(8);
  await h.click(8);
  assert.equal(h.pending(), null);
  assert.equal(JSON.stringify(h.messages.at(-1).splitSubmit), JSON.stringify({ done: 2, total: 3 }));
  await h.click(9);
  assert.equal(h.pending(), "d1");
  assert.equal(h.messages.at(-1).splitSubmit, undefined);
});

test("tab tách đóng mà chưa nộp → trừ khỏi tổng, đủ thì hỏi ở tab gốc", async () => {
  const h = await splitRun();
  await h.click(7);
  await h.click(8);
  await h.api.noteSplitTabClosed(99); // tab không thuộc lượt tách → không tính
  assert.equal(h.pending(), null);
  await h.api.noteSplitTabClosed(9);
  assert.equal(h.pending(), "d1");
  assert.equal(h.messages.at(-1).tabId, 7);
});

test("đóng tab đã nộp không trừ tổng", async () => {
  const h = await splitRun();
  await h.click(7);
  await h.click(8);
  await h.api.noteSplitTabClosed(8);
  assert.equal(h.pending(), null);
});

test("hồ sơ không tách (không có sổ) → hỏi ngay ở cú bấm như cũ", async () => {
  const h = harness();
  await h.click(7);
  assert.equal(h.pending(), "d1");
});

test("panel: dòng tiến độ + nút thoát gửi splitSubmitRelease", () => {
  assert.match(popup, /if \(msg\.splitSubmit\) void showSplitSubmitNotice\(msg\.splitSubmit\);/);
  assert.match(popup, /splitSubmitDoneBtn\?\.addEventListener\("click"[\s\S]{0,120}?action: "splitSubmitRelease"[\s\S]{0,60}?resumePendingRating\(\)/);
  assert.match(src, /msg\?\.action === "splitSubmitRelease"[\s\S]*?markRatingPending\(dossierId/);
  assert.match(src, /onRemoved\.addListener\(async \(tabId\) => \{\s*try \{\s*void noteSplitTabClosed\(tabId\);/);
});
