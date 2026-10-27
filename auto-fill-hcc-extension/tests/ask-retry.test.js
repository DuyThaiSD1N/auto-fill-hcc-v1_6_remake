// BE khởi động lại giữa lúc xử lý: lệnh hệ thống / cú bấm nút được thử lại tới khi BE lên lại (tối đa 90s); nối lại
// kênh tiến trình thì nhờ BE bù sự kiện đã lỡ (__event:pipeline_resync).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const raw = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const sidebar = raw.replace(/^\s*\/\/.*$/gm, "");

function loadRetry(api) {
  const start = raw.indexOf("  const ASK_RETRY_MAX_MS");
  const end = raw.indexOf("  async function ask(message");
  const statuses = [];
  const ctx = {
    api, statuses, Date, Math,
    setStatus: (text) => statuses.push(text),
    setTimeout: (fn) => fn(), // bỏ chờ thật cho test chạy nhanh
  };
  vm.runInNewContext(`${raw.slice(start, end)}; this.apiAskRetrying = apiAskRetrying;`, ctx);
  return ctx;
}

const httpError = (status) => Object.assign(new Error(`HTTP ${status}`), { status });

test("lệnh hệ thống gặp 502 / mất mạng thì thử lại tới khi được, chỉ một lần thành công", async () => {
  const calls = [];
  const errors = [httpError(502), new TypeError("Failed to fetch")];
  const ctx = loadRetry({ ask: async (m) => { calls.push(m); if (errors.length) throw errors.shift(); return { ok: 1 }; } });
  const data = await ctx.apiAskRetrying("__action:fill_report:{}", {}, "system");
  assert.deepEqual(data, { ok: 1 });
  assert.equal(calls.length, 3);
  assert.match(ctx.statuses[0], /Máy chủ đang khởi động lại/);
  assert.equal(ctx.statuses.at(-1), "");
});

test("câu nói tự do và lỗi nghiệp vụ (4xx) không thử lại", async () => {
  let n = 0;
  const ctx = loadRetry({ ask: async () => { n += 1; throw httpError(502); } });
  await assert.rejects(ctx.apiAskRetrying("cho tôi nộp hồ sơ", {}, "voice"));
  assert.equal(n, 1);
  n = 0;
  const ctx2 = loadRetry({ ask: async () => { n += 1; throw httpError(422); } });
  await assert.rejects(ctx2.apiAskRetrying("__action:x", {}, "system"));
  assert.equal(n, 1);
});

test("hết 90 giây vẫn lỗi thì hiện nút Thử lại gửi đúng lệnh cũ", () => {
  assert.match(sidebar, /const ASK_RETRY_MAX_MS = 90000;/);
  assert.match(sidebar, /const data = await apiAskRetrying\(message, \{ source, displayText, clientContext, preferredLang \}, source\);/);
  assert.match(sidebar, /renderChips\(\[\{ label: "🔁 Thử lại", send: message, solid: true \}\]\);/);
});

test("nối lại kênh tiến trình giữa lúc xử lý thì nhờ BE bù sự kiện", () => {
  assert.match(sidebar, /if \(\["filling", "owner_filling", "attaching"\]\.includes\(lastState\)\) ask\("__event:pipeline_resync", "system"\);/);
});
