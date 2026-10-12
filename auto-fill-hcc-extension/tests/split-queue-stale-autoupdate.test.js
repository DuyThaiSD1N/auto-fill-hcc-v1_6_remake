// Hàng đợi tách hồ sơ bỏ dở (tab đang xử lý không còn / chạy quá 2 giờ) không được chặn tự cập
// nhật mãi mãi. Chạy THẬT hangDoiTachBoDo của popup.js trong vm.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const popup = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");
const snippet = popup.slice(popup.indexOf("const HANG_DOI_TACH_TOI_DA_MS"), popup.indexOf("async function extUpdateDangBanRon()"));

function load(liveTabs) {
  const sent = [];
  const ctx = vm.createContext({
    Date, Number, console: { info() {} },
    chrome: {
      tabs: { get: async (id) => { if (!liveTabs.includes(id)) throw new Error("No tab"); return { id }; } },
      runtime: { sendMessage: async (m) => { sent.push(m.action); } },
    },
  });
  vm.runInContext(`${snippet}\nthis.boDo = hangDoiTachBoDo;`, ctx);
  return { boDo: ctx.boDo, sent };
}

test("tab đang xử lý không còn (Chrome tắt giữa chừng) → bỏ dở, dọn hàng đợi", async () => {
  const { boDo, sent } = load([]);
  assert.equal(await boDo({ startedAt: Date.now(), activeTabId: 9 }), true);
  assert.deepEqual(sent, ["clearAllPendingAttach"]);
});

test("chạy quá 2 giờ → bỏ dở dù tab còn", async () => {
  const { boDo } = load([9]);
  assert.equal(await boDo({ startedAt: Date.now() - 3 * 3600 * 1000, activeTabId: 9 }), true);
});

test("đang chạy thật (tab còn, mới bắt đầu) hoặc đang chuyển giữa hai tab → vẫn bận", async () => {
  const { boDo, sent } = load([9]);
  assert.equal(await boDo({ startedAt: Date.now(), activeTabId: 9 }), false);
  assert.equal(await boDo({ startedAt: Date.now(), activeTabId: null }), false);
  assert.deepEqual(sent, []);
});

test("extUpdateDangBanRon chỉ coi là bận khi hàng đợi CHƯA bỏ dở", () => {
  assert.match(popup, /if \(q && !\(await hangDoiTachBoDo\(q\)\)\) return true;/);
});
