// Công dân NÓI tên thủ tục khác giữa chừng: BE gửi new_conversation kèm procedure_key → sidebar mở
// phiên mới (một conversation = một hồ sơ) rồi tự chọn đúng thủ tục đó, không bắt chọn lại.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const js = fs.readFileSync(path.join(__dirname, "..", "sidebar.js"), "utf8");

test("action new_conversation chuyển procedure_key vào returnToStart", () => {
  assert.match(js, /a\.type === "new_conversation"\) \{[\s\S]{0,300}await returnToStart\("new_procedure", \{ procedureKey: String\(a\.procedure_key \|\| ""\) \}\);/);
});

test("phiên mới: có procedureKey thì tự gửi pick_procedure, không thì mở danh sách như cũ", () => {
  assert.match(js, /await ask\("", "system"\);\s*if \(procedureKey\) await ask\(`__action:pick_procedure:\$\{JSON\.stringify\(\{ key: procedureKey \}\)\}`, "system"\);\s*else showProcedurePicker\(\);/);
});

test("đang bận (action chạy trong ask) thì hoãn cả lý do lẫn thủ tục, không mất procedureKey", () => {
  assert.match(js, /if \(busy\) \{ pendingReturnReason = reason; pendingReturnProcedure = procedureKey; return; \}/);
  assert.match(js, /const procedureKey = pendingReturnProcedure;[\s\S]{0,120}returnToStart\(reason, \{ procedureKey \}\);/);
});
