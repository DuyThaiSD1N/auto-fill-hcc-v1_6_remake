// Cổng tư pháp thay nút "Chọn tệp đính kèm" bằng chip tên tệp khi dòng đã có tệp (đọc từ bundle
// "thongtin/man ket thuc/tư pháp"). Mọi dòng cố định đã đủ tệp mà bấm đính kèm lại thì engine phải
// vẫn thấy bảng thành phần hồ sơ (không im lặng → "Trang không nhận lệnh đính kèm") và vẫn liệt kê
// dòng đã có tệp để bỏ qua / gỡ tệp lượt trước.
//
// Chạy THẬT các hàm tìm dòng của attach-core.js trong vm; helper đọc DOM được thay bằng bản giả.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const src = fs.readFileSync(path.join(__dirname, "..", "content/attach-core.js"), "utf8");

function slice(from, to) {
  const start = src.indexOf(from);
  const end = src.indexOf(to, start + 1);
  assert.ok(start >= 0 && end > start, `không cắt được đoạn ${from} → ${to}`);
  return src.slice(start, end);
}

const fold = (s) => String(s || "")
  .replace(/Đ/g, "D").replace(/đ/g, "d")
  .normalize("NFD").replace(/[̀-ͯ]/g, "")
  .replace(/\s+/g, " ").trim().toLowerCase();

const COMPONENT_TABLE = { textContent: "STT Tên thành phần hồ sơ Đính kèm tệp tin Loại chứng thực Thao Tác" };
const OTHER_TABLE = { textContent: "STT Họ tên Ngày sinh Ghi chú" };

function tr({ table, name, fileName = "", button = false, cell = "TD", add = false }) {
  return {
    cells: [{ tagName: cell }],
    closest: (sel) => (sel === "table" ? table : null),
    name, fileName, button, add,
  };
}

function load(rows) {
  const ctx = {
    document: {
      querySelector: () => null,
      querySelectorAll: (sel) => (sel === "tr" ? rows : []),
    },
    textContainsAll: (el, snippets) => snippets.every((s) => fold(el?.textContent).includes(s)),
    foldChoiceText: fold,
    foldedNodeText: (el) => fold(el?.textContent),
    isVisible: () => true,
    isAddAttachmentRow: (row) => !!row.add,
    isAuthorizationAttachmentRow: () => false,
    hasAttachmentChooseControl: (row) => !!row.button,
    rowHasAttachedFile: (row) => !!row.fileName,
    attachmentComponentName: (row) => row.name || "",
    findCopyCertificationAttachmentRow: () => null,
  };
  vm.createContext(ctx);
  vm.runInContext([
    slice("function hasAttachmentTarget", "\nconst COPY_CERT_ATTACHMENT_SNIPPETS"),
    slice("function isFilledComponentTableRow", "\nfunction componentTextMatches"),
    "this.hasAttachmentTarget = hasAttachmentTarget;",
    "this.findAttachmentRows = findAttachmentRows;",
  ].join("\n"), ctx);
  return ctx;
}

test("mọi dòng đã có tệp: vẫn là trang đính kèm và liệt kê đủ dòng theo STT", () => {
  const header = tr({ table: COMPONENT_TABLE, name: "Tên thành phần hồ sơ", fileName: "Đính kèm tệp tin", cell: "TH" });
  const row1 = tr({ table: COMPONENT_TABLE, name: "Bản chính giấy chứng nhận", fileName: "So do.pdf" });
  const row2 = tr({ table: COMPONENT_TABLE, name: "Dự thảo giao dịch", fileName: "Hop dong.pdf" });
  const addRow = tr({ table: COMPONENT_TABLE, name: "Thêm thành phần hồ sơ", add: true });
  const { hasAttachmentTarget, findAttachmentRows } = load([header, row1, row2, addRow]);

  assert.equal(hasAttachmentTarget(), true);
  assert.deepEqual([...findAttachmentRows()], [row1, row2]);
});

test("dòng trống có nút xen dòng đã có tệp: thứ tự dòng giữ đúng STT", () => {
  const row1 = tr({ table: COMPONENT_TABLE, name: "Dòng 1", fileName: "a.pdf" });
  const row2 = tr({ table: COMPONENT_TABLE, name: "Dòng 2", button: true });
  const { findAttachmentRows } = load([row1, row2]);

  assert.deepEqual([...findAttachmentRows()], [row1, row2]);
});

test("bảng khác có chữ ở cột 3 không bị coi là dòng đính kèm", () => {
  const stray = tr({ table: OTHER_TABLE, name: "Nguyễn Văn A", fileName: "01/01/1990" });
  const { hasAttachmentTarget, findAttachmentRows } = load([stray]);

  assert.equal(hasAttachmentTarget(), false);
  assert.equal(findAttachmentRows().length, 0);
});
