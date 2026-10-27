// Bảng 29 dòng GPXD (dvc.moc Bộ Xây dựng) tick sẵn mọi dòng; planner GPXD đính kiểu ô cố định (fixed-slot) và gửi
// untickUnplannedRows → bỏ tích hết trước khi đính, dòng đính được thì tích lại (bản copy của tro-ly-nguoi-dan-extension
// content/attach-core.js).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const content = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8").replace(/^\s*\/\/.*$/gm, "");
const fixedSlot = content.slice(content.indexOf("async function attachFilesByFixedSlot"),
  content.indexOf("function forceRow1PlanItem"));

test("ô cố định: bỏ tích hết trước khi đính khi BE gửi untickUnplannedRows", () => {
  assert.match(fixedSlot, /const untick = attachments\.some\(\(item\) => item\.untickUnplannedRows\);\s*if \(untick\) await uncheckAllAttpRows\(\);/);
});

test("ô cố định: dòng đính được thì tích lại (cả ô upload trực tiếp lẫn ô menu)", () => {
  assert.match(fixedSlot, /if \(ok && untick && slotRow\) await tickAttpRowCheckbox\(slotRow\);/);
  assert.match(fixedSlot, /if \(ok && untick && trigger\.closest\("tr"\)\) await tickAttpRowCheckbox\(trigger\.closest\("tr"\)\);/);
});
