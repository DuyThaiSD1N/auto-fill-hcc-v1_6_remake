const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
const start = content.indexOf("function forceRow1PlanItem");
const end = content.indexOf("\n  // ===== Engine đính kèm bảng-checkbox", start);
assert.ok(start >= 0 && end > start, "Không tìm thấy helper định tuyến split");

const row1 = { slot: 1 };
const row2 = { slot: 2 };
const context = {
  isIdentityAttachmentItem: (item) => item.detectedType === "Căn cước công dân",
  findAttachmentRows: () => [row1, row2],
  findCopyCertificationAttachmentRow: () => row1,
  attachmentComponentName: (row) => row === row2 ? "Giấy tùy thân" : "Bản chính giấy tờ",
};
vm.createContext(context);
vm.runInContext(
  content.slice(start, end) + "\nthis.forceRow1PlanItem = forceRow1PlanItem;",
  context
);

const identity = { detectedType: "Căn cước công dân", documentName: "CCCD Nguyễn Văn A" };
const document = { detectedType: "Học bạ", documentName: "Học bạ Nguyễn Văn A" };

const copyIdentity = context.forceRow1PlanItem(identity, "chung-thuc-ban-sao");
assert.equal(copyIdentity.componentIndex, 1, "CCCD chứng thực bản sao phải vào STT1 của hồ sơ riêng");
assert.equal(copyIdentity.componentName, "Bản chính giấy tờ");

const signatureIdentity = context.forceRow1PlanItem(identity, "chung-thuc-chu-ky");
assert.equal(signatureIdentity.componentIndex, 2, "CCCD chứng thực chữ ký phải vào STT2");
assert.equal(signatureIdentity.componentName, "Giấy tùy thân");

const copyDocument = context.forceRow1PlanItem(document, "chung-thuc-ban-sao");
assert.equal(copyDocument.componentIndex, 1);

const forcedTranslation = context.forceRow1PlanItem(
  { ...identity, forceFirstRow: true },
  "chung-thuc-chu-ky"
);
assert.equal(forcedTranslation.componentIndex, 1, "Tài liệu forceFirstRow không bị heuristic CCCD đẩy xuống STT2");

console.log("copy certification split routing: procedure-aware STT1/STT2 passed");
