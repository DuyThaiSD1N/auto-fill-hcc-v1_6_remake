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
      .replace(/[̀-ͯ]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase();
  },
};
vm.createContext(context);
vm.runInContext(
  attachCore.slice(helpersStart, helpersEnd) +
    "\nthis.attachmentKeyEquals = attachmentKeyEquals;",
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

// LỖI THẬT (chứng thực bản sao, 9 tài liệu): lượt đính đầu của dòng 1 hỏng vì cổng trả 502.
// Lượt round-robin thứ hai bị coi là TRÙNG với "Bảng điểm Đại học Duy Tân 2" — bản tự đánh số
// của một tài liệu KHÁC — nên bỏ retry và tô xanh, trong khi dòng bắt buộc số 1 vẫn trống.
// Thủ phạm là so khớp kiểu CHỨA NHAU: "…duy tan 2".includes("…duy tan").
assert.equal(
  context.attachmentKeyEquals("Bảng điểm Đại học Duy Tân 2.pdf", "Bảng điểm Đại học Duy Tân"),
  false,
  "Hậu tố đánh số là tài liệu KHÁC, không được nuốt bản gốc",
);
assert.equal(
  context.attachmentKeyEquals("Bảng điểm Đại học Duy Tân.pdf", "Bảng điểm Đại học Duy Tân"),
  true,
  "Đúng tài liệu đó thì vẫn phải nhận ra là đã đính",
);

// Hàm so kiểu chứa nhau phải BIẾN MẤT hẳn, không chỉ thôi được gọi — còn trong file là còn
// nguy cơ ai đó dùng lại.
assert.equal(
  attachCore.includes("attachmentKeyMatches"),
  false,
  "attachmentKeyMatches (so kiểu chứa nhau) phải được gỡ khỏi attach-core.js",
);

const existingRowStart = attachCore.indexOf("function findExistingAttachedRowForPlanItem");
const existingRowEnd = attachCore.indexOf("\nfunction findEmptyAttachmentRowByComponent", existingRowStart);
const existingRowSource = attachCore.slice(existingRowStart, existingRowEnd);
assert.match(
  existingRowSource,
  /if \(wantsNewComponent\)[\s\S]*?attachmentKeyEquals\(componentName, expectedNewComponent\)[\s\S]*?attachmentKeyEquals\(attachedName, label\)/,
  "Thành phần động phải dùng so khớp chính xác cho cả tên dòng và tên file",
);
// Dòng CỐ ĐỊNH cũng phải so chính xác — đây chính là nhánh đã gây ra lỗi trên.
assert.match(
  existingRowSource,
  /return labels\.some\(\(label\) => attachmentKeyEquals\(attachedName, label\)\);/,
  "Dòng cố định phải so khớp chính xác, không được dùng lại kiểu chứa nhau",
);

// Hai extension dùng chung một tiêu chí: no-handfree đã sửa trước, handfree không được tụt lại.
const noHandfree = fs.readFileSync(
  path.join(root, "..", "auto-fill-hcc-extension", "content.js"), "utf8",
);
assert.equal(
  noHandfree.includes("attachmentKeyMatches"),
  false,
  "no-handfree cũng không được có hàm so kiểu chứa nhau",
);

console.log("Handfree attachment duplicate names: exact matching on both fixed and dynamic rows passed");
