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

assert.match(
  popup,
  /async function clearSplitProgressForCurrentTab\(\)[\s\S]*?progress\.originTabId[\s\S]*?chrome\.storage\.local\.remove\(SPLIT_ATTACH_PROGRESS_KEY\)/,
  "Chỉ được xóa tiến độ split thuộc đúng tab hiện tại",
);
assert.match(
  popup,
  /newSessionBtn\.addEventListener\("click", async \(\) => \{[\s\S]*?await clearSession\(\);[\s\S]*?await clearSplitProgressForCurrentTab\(\);/,
  "Tạo phiên mới phải xóa banner tiến độ cũ",
);
assert.match(
  popup,
  /if \(shouldResetProcedureWork\(next\.key\)\) \{[\s\S]*?resetProcedureWorkState\(\);[\s\S]*?await clearSplitProgressForCurrentTab\(\);/,
  "Đổi thủ tục phải xóa banner tiến độ cũ",
);

console.log("split progress display: running, paused, completed and partial copy passed");
