// Lệnh điền gửi đúng lúc cổng vừa chuyển bước: eForm chưa dựng xong thì không frame nào trả lời (null) → sidebar
// từng báo 0 ô và đi tiếp, form gần như trống. Phải chờ rồi gửi lại.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const sidebar = fs.readFileSync(path.join(__dirname, "..", "sidebar.js"), "utf8");

function loadRetry(responses) {
  const start = sidebar.indexOf("const FILL_RETRY_DELAYS_MS");
  const end = sidebar.indexOf("// ── Mốc \"công dân bấm Gửi hồ sơ\" ──");
  const calls = [];
  const ctx = {
    console: { warn() {} },
    setTimeout: (fn) => fn(),
    sendToContent: async (payload) => { calls.push(payload); return responses.shift() ?? null; },
  };
  vm.createContext(ctx);
  vm.runInContext(`${sidebar.slice(start, end)}\nthis.sendFillWithRetry = sendFillWithRetry;`, ctx);
  return { run: ctx.sendFillWithRetry, calls };
}

test("lệnh fill_fields đi qua sendFillWithRetry", () => {
  assert.match(sidebar, /const res = await sendFillWithRetry\(\{\n\s*action: "fillFields"/);
});

test("chưa frame nào trả lời thì gửi lại tới khi có kết quả", async () => {
  const { run, calls } = loadRetry([null, null, { filled: 12, notFound: [], errors: [] }]);
  const res = await run({ action: "fillFields" });
  assert.equal(res.filled, 12);
  assert.equal(calls.length, 3);
});

test("hết lượt chờ vẫn không trả lời thì trả null như cũ", async () => {
  const { run, calls } = loadRetry([]);
  assert.equal(await run({ action: "fillFields" }), null);
  assert.equal(calls.length, 5);
});

test("có form mà 0 ô thì chỉ thử lại một lần; điền được hoặc lỗi thì không thử lại", async () => {
  const empty = { filled: 0, notFound: ["A"], errors: [] };
  let t = loadRetry([empty, { ...empty }]);
  assert.equal((await t.run({})).filled, 0);
  assert.equal(t.calls.length, 2);
  t = loadRetry([{ filled: 3, notFound: [], errors: [] }]);
  await t.run({});
  assert.equal(t.calls.length, 1);
  t = loadRetry([{ error: "Engine điền chưa nạp" }]);
  await t.run({});
  assert.equal(t.calls.length, 1);
});
