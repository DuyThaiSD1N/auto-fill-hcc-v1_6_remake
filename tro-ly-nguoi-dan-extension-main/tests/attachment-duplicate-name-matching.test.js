const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const attachCore = fs.readFileSync(path.join(root, "content", "attach-core.js"), "utf8");
const helpersStart = attachCore.indexOf("function attachmentTextKey");
const helpersEnd = attachCore.indexOf("\nfunction attachmentPlanLabels", helpersStart);

assert.ok(helpersStart >= 0 && helpersEnd > helpersStart, "Không tìm thấy helper so tên file đính kèm");

const context = {
  foldChoiceText(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase();
  },
};
vm.createContext(context);
vm.runInContext(
  attachCore.slice(helpersStart, helpersEnd) +
    "\nthis.attachmentKeyEquals = attachmentKeyEquals;" +
    "\nthis.attachmentKeyMatches = attachmentKeyMatches;",
  context,
);

assert.equal(
  context.attachmentKeyEquals("CCCD VŨ HUY HOÀN.pdf", "CCCD VŨ HUY HOÀN"),
  true,
  "Cùng tên, chỉ khác đuôi file, phải được nhận là trùng",
);
assert.equal(
  context.attachmentKeyEquals("CCCD VŨ HUY HOÀN.pdf", "CCCD VŨ HUY HÒA"),
  false,
  "HOÀN và HÒA là hai chủ thể khác nhau, không được bỏ qua",
);

const existingRowStart = attachCore.indexOf("function findExistingAttachedRowForPlanItem");
const existingRowEnd = attachCore.indexOf("\nfunction findEmptyAttachmentRowByComponent", existingRowStart);
const existingRowSource = attachCore.slice(existingRowStart, existingRowEnd);
assert.match(
  existingRowSource,
  /if \(wantsNewComponent\)[\s\S]*?attachmentKeyEquals\(componentName, expectedNewComponent\)[\s\S]*?attachmentKeyEquals\(attachedName, label\)/,
  "Thành phần động phải dùng so khớp chính xác cho cả tên dòng và tên file",
);

console.log("Handfree attachment duplicate names: exact dynamic matching passed");
