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

// ── Cổng DVC Bộ Công an (thị thực 1.001194, 18/11): khối tải ảnh đầu trang KÊ KHAI không phải bảng đính kèm ──
function fileInput({ id = "", name = "", typeimg = false } = {}) {
  return { id, name, hasAttribute: (attr) => attr === "typeimg" && typeimg, closest: () => null };
}

function photoRow(inputs) {
  return {
    cells: [{ tagName: "TD" }],
    closest: () => null,
    querySelectorAll: (sel) => (sel === 'input[type="file"]' ? inputs : []),
    name: "Ảnh chân dung Tải ảnh Trang nhân thân hộ chiếu", button: true,
  };
}

test("trang kê khai Bộ Công an: hàng tải ảnh 4x6 + trang hộ chiếu không tính là dòng đính kèm", () => {
  const photo = photoRow([fileInput({ id: "custom-file-input-46", name: "filename46", typeimg: true }),
                          fileInput({ id: "custom-file-input-HoChieu", name: "filenamehc", typeimg: true })]);
  const { hasAttachmentTarget, findAttachmentRows } = load([photo]);
  assert.deepEqual([...findAttachmentRows()], []);
  assert.equal(hasAttachmentTarget(), false, "trang kê khai không được báo attachmentTarget");
  // Trang Thành phần hồ sơ thật (ô GiayToCuaHoSoOnline_*) vẫn là dòng đính kèm.
  const real = photoRow([fileInput({ name: "GiayToCuaHoSoOnline_15962_fileGiayTo" })]);
  real.name = "Tờ khai đề nghị cấp thị thực, gia hạn tạm trú (Mẫu NA5)";
  assert.deepEqual([...load([real]).findAttachmentRows()], [real]);
});

test("trang kê khai Bộ Công an: khối ảnh không nằm trong <tr> vẫn không báo trang đính kèm", () => {
  const inputs = [fileInput({ id: "custom-file-input-46", name: "filename46", typeimg: true })];
  const ctx = load([]);
  ctx.location = { hostname: "dichvucong.bocongan.gov.vn" };
  ctx.document.querySelectorAll = (sel) => (sel === 'input[type="file"]' ? inputs : []);
  ctx.document.querySelector = () => null;
  vm.runInContext([
    slice("function hasAttachmentTarget", "\nconst COPY_CERT_ATTACHMENT_SNIPPETS"),
    "this.hasAttachmentTarget = hasAttachmentTarget;",
  ].join("\n"), ctx);
  assert.equal(ctx.hasAttachmentTarget(), false);
});

test("lượt đính kèm chặn hộp chọn tệp của hệ điều hành rồi gỡ chặn", async () => {
  const listeners = new Map();
  const ctx = {
    document: {
      addEventListener: (type, fn, capture) => listeners.set(`${type}:${capture}`, fn),
      removeEventListener: (type, fn, capture) => {
        if (listeners.get(`${type}:${capture}`) === fn) listeners.delete(`${type}:${capture}`);
      },
    },
    setTimeout: (fn) => fn(),
  };
  vm.createContext(ctx);
  vm.runInContext(slice("let nativePickerBlockers", "\nasync function attachFilesByPlan")
    + "\nthis.withNativeFilePickerBlocked = withNativeFilePickerBlocked;", ctx);
  let prevented = 0;
  const click = (tagName, type) => listeners.get("click:true")?.({
    target: { tagName, type }, preventDefault: () => { prevented += 1; },
  });
  const result = await ctx.withNativeFilePickerBlocked(async () => {
    click("INPUT", "file");   // trang tự gọi input.click() → không mở hộp chọn tệp
    click("BUTTON", "");      // nút khác vẫn bấm bình thường
    return "xong";
  });
  assert.equal(result, "xong");
  assert.equal(prevented, 1);
  assert.equal(listeners.has("click:true"), false, "xong lượt đính phải gỡ chặn");
  const src2 = fs.readFileSync(path.join(__dirname, "..", "content/attach-core.js"), "utf8");
  assert.match(src2, /withNativeFilePickerBlocked\(\(\) => attachFilesByPlan\(files, attachments/);
  assert.match(src2, /attachFilesByPlan: \(\.\.\.args\) => withNativeFilePickerBlocked/);
});

test("eForm Bộ Công an: bảng đính kèm chỉ tính khi dòng của nó HIỆN, kể cả cùng trang form kê khai", () => {
  // Chạy thật 18/11 (thị thực 1.001194): bảng Thành phần hồ sơ nằm NGAY DƯỚI form kê khai trên cùng một trang. Thứ tự
  // điền trước / đính sau do BE quyết (cờ bcaKeKhaiForm), engine phải nhận được bảng thì mới đính được.
  const hiddenRow = { hidden: true };
  const shownRow = { hidden: false };
  const slot = (row) => ({ name: "GiayToCuaHoSoOnline_15962_fileGiayTo", closest: () => row });
  function page({ formShown, row }) {
    const formInput = { name: "CongDan_tenCongDan", hidden: !formShown };
    const ctx = load([]);
    ctx.location = { hostname: "dichvucong.bocongan.gov.vn" };
    ctx.isVisible = (el) => !!el && !el.hidden;
    ctx.document.querySelectorAll = (sel) => {
      if (sel.includes('name^="CongDan_"')) return [formInput];
      if (sel.includes("GiayToCuaHoSoOnline_")) return [slot(row)];
      return [];
    };
    vm.runInContext([
      slice("function hasAttachmentTarget", "\nconst COPY_CERT_ATTACHMENT_SNIPPETS"),
      "this.hasAttachmentTarget = hasAttachmentTarget;",
    ].join("\n"), ctx);
    return ctx.hasAttachmentTarget();
  }
  assert.equal(page({ formShown: true, row: shownRow }), true, "form + bảng cùng trang → có bảng đính kèm");
  assert.equal(page({ formShown: false, row: shownRow }), true, "trang chỉ có bảng → có bảng đính kèm");
  assert.equal(page({ formShown: true, row: hiddenRow }), false, "bảng dựng sẵn nhưng ẩn → chưa có");
  assert.equal(page({ formShown: false, row: hiddenRow }), false);
});
