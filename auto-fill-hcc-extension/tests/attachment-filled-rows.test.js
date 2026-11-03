// Cổng tư pháp thay nút "Chọn tệp đính kèm" bằng chip tên tệp khi dòng đã có tệp. Dòng đó vẫn phải
// được liệt kê (theo đúng STT) để đính kèm lại nhận ra tệp đã có, không đếm lệch dòng.
// Chạy THẬT các hàm tìm dòng của content.js trong vm; helper đọc DOM được thay bằng bản giả.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const src = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");

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

function tr({ table, name, fileName = "", button = false, cell = "TD" }) {
  return { cells: [{ tagName: cell }], closest: (sel) => (sel === "table" ? table : null), name, fileName, button };
}

function findRows(rows) {
  const ctx = {
    document: { querySelectorAll: (sel) => (sel === "tr" ? rows : []) },
    textContainsAll: (el, snippets) => snippets.every((s) => fold(el?.textContent).includes(s)),
    isAddAttachmentRow: () => false,
    hasAttachmentChooseControl: (row) => !!row.button,
    rowHasAttachedFile: (row) => !!row.fileName,
    attachmentComponentName: (row) => row.name || "",
  };
  vm.createContext(ctx);
  vm.runInContext(
    slice("function isFilledComponentTableRow", "\n  function componentTextMatches")
      + "\nthis.findAttachmentRows = findAttachmentRows;",
    ctx,
  );
  return [...ctx.findAttachmentRows()];
}

test("dòng đã có tệp (không còn nút) vẫn được liệt kê theo đúng STT", () => {
  const header = tr({ table: COMPONENT_TABLE, name: "Tên thành phần hồ sơ", fileName: "Đính kèm tệp tin", cell: "TH" });
  const row1 = tr({ table: COMPONENT_TABLE, name: "Dòng 1", fileName: "a.pdf" });
  const row2 = tr({ table: COMPONENT_TABLE, name: "Dòng 2", button: true });
  assert.deepEqual(findRows([header, row1, row2]), [row1, row2]);
});

test("bảng khác có chữ ở cột 3 không bị coi là dòng đính kèm", () => {
  assert.deepEqual(findRows([tr({ table: OTHER_TABLE, name: "Nguyễn Văn A", fileName: "01/01/1990" })]), []);
});
