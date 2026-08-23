const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");
const start = popup.indexOf("function splitProgressPresentation(progress)");
const end = popup.indexOf("\nfunction renderSplitProgress", start);
assert.ok(start >= 0 && end > start, "Không tìm thấy formatter tiến độ split");

const context = {};
vm.createContext(context);
vm.runInContext(`${popup.slice(start, end)}\nthis.present = splitProgressPresentation;`, context);

assert.deepEqual(
  JSON.parse(JSON.stringify(context.present({
    status: "running", total: 5, completed: 1, succeeded: 1, failed: 0, activeOrdinal: 2,
  }))),
  { type: "info", message: "Đã đính kèm 1/5 hồ sơ.\nĐang xử lý hồ sơ 2/5…" }
);

assert.deepEqual(
  JSON.parse(JSON.stringify(context.present({
    status: "paused", total: 5, completed: 2, succeeded: 2, failed: 0,
    activeOrdinal: 3, paused: { ordinal: 3 },
  }))),
  {
    type: "warn",
    message: "Đã đính kèm 2/5 hồ sơ.\nHồ sơ 3 chưa nhận được file; hàng đợi đang dừng tại tab đó.",
  }
);

assert.deepEqual(
  JSON.parse(JSON.stringify(context.present({
    status: "completed", total: 5, completed: 5, succeeded: 5, failed: 0,
  }))),
  { type: "ok", message: "Đã đính kèm thành công 5/5 hồ sơ." }
);

assert.deepEqual(
  JSON.parse(JSON.stringify(context.present({
    status: "completed", total: 5, completed: 5, succeeded: 4, failed: 1,
  }))),
  {
    type: "warn",
    message: "Đã xử lý 5/5 hồ sơ: 4 thành công, 1 chưa thành công.\nVui lòng kiểm tra các tab được báo lỗi.",
  }
);

console.log("split progress display: running, paused, completed and partial copy passed");
