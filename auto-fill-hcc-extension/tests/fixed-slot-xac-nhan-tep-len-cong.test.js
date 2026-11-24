// Ô input cố định (vd mai táng BYT): gán được tệp vào input chưa phải đã lên cổng — chỉ nhận thành công khi tên
// tệp hiện trên dòng. Hành vi so khớp chạy thật ở tro-ly-nguoi-dan-extension/tests/fixed-slot-xac-nhan-tep-len-cong.test.js.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const src = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");
const code = src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

test("nhánh input của fixed-slot chỉ đếm thành công sau khi thấy tên tệp trên dòng", () => {
  const start = code.indexOf("async function attachFilesByFixedSlot(");
  const branch = code.slice(start, code.indexOf("const trigger = findMenuSlotTrigger(", start));
  const wait = branch.indexOf("await waitFor(() => fixedSlotFilesLanded(liveRow(), pending), FIXED_SLOT_LAND_TIMEOUT_MS");
  assert.ok(wait > 0, "thiếu bước chờ tên tệp hiện trên dòng");
  assert.ok(branch.indexOf("if (ok) attachedNames.push(...pending.map((f) => f.name));") > wait);
  assert.match(branch, /if \(ok\) markLandedFileChips\(liveRow\(\), pending\);\s*else markAttachmentResult\(liveRow\(\), false\);/);
  assert.match(branch, /else if \(assigned\) fail\(item, `Cổng chưa ghi nhận tệp ở ô/);
});

test("nhánh menu (liên thông) cũng chỉ đếm thành công sau khi thấy tên tệp trên dòng", () => {
  const start = code.indexOf("const trigger = findMenuSlotTrigger(", code.indexOf("async function attachFilesByFixedSlot("));
  const branch = code.slice(start, code.indexOf("Không tìm thấy ô đính kèm", start));
  const wait = branch.indexOf("await waitFor(() => fixedSlotFilesLanded(markTarget, pending)");
  assert.ok(wait > 0, "thiếu bước chờ tên tệp hiện trên dòng");
  assert.ok(branch.indexOf("if (ok) attachedNames.push(...pending.map((f) => f.name));") > wait);
  assert.match(branch, /if \(ok\) markLandedFileChips\(markTarget, pending\);\s*else markAttachmentResult\(markTarget, false\);/);
});

test("bằng chứng gồm tên trên chip của dòng và ô readonly; mốc chờ không quá 8 giây", () => {
  assert.match(code, /const FIXED_SLOT_LAND_TIMEOUT_MS = 8000;/);
  assert.match(code, /function fixedSlotFilesLanded\(row, files\) \{\s*const missing = filesNotOnRow\(row, files\);/);
  assert.match(code, /querySelectorAll\?\.\("input\[readonly\]"\)/);
});
