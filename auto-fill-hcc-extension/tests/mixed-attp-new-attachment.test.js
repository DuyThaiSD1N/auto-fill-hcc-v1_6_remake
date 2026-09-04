const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const contentSource = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");
const start = contentSource.indexOf("async function attachFilesByPlan");
const end = contentSource.indexOf("\n  async function attachFilesToRequiredCopyCertification", start);

assert.ok(start >= 0 && end > start, "Không tách được attachFilesByPlan");
const source = contentSource.slice(start, end);

assert.match(
  source,
  /const genericNewItems = allAttachments\.filter[\s\S]*?item\.target === "new" \|\| item\.needsAddComponent === true/,
  "Phải nhận diện item tạo thành phần động",
);
assert.match(
  source,
  /if \(attpItems\.length && !addDocumentItems\.length && !genericNewItems\.length\)/,
  "Chỉ được return nhanh khi kế hoạch không có target=new",
);

const mixedBranch = source.indexOf("if (attpItems.length && genericNewItems.length && onlyAttpAndGenericNew)");
const fixedAttach = source.indexOf("attachFilesByAttpRow(payloadFiles, attpItems)", mixedBranch);
const keepDynamic = source.indexOf("remainingAttachments = genericNewItems", mixedBranch);
const genericLoop = source.indexOf("const plannedAttachments", keepDynamic);

assert.ok(mixedBranch >= 0, "Thiếu nhánh kế hoạch hỗn hợp attp-row + new");
assert.ok(fixedAttach > mixedBranch, "Phải đính nhóm hàng cố định bằng engine attp-row trước");
assert.ok(keepDynamic > fixedAttach, "Sau hàng cố định phải giữ lại nhóm target=new");
assert.ok(genericLoop > keepDynamic, "Nhóm target=new phải tiếp tục đi qua engine generic");
assert.match(source, /const normalItems = remainingAttachments\.filter/);

console.log("mixed attp-row + target=new attachment contract passed");
