/**
 * Bảng "Thành phần hồ sơ" của eForm Cổng DVC quốc gia có thêm cột "Loại bản" (radio 1 Bản chính /
 * 1 Bản sao) và cột "Mẫu giấy tờ" (link tải Mau so 01.doc). Bản cũ đọc cứng cột thứ 3 làm ô tệp và
 * chỉ xoá thẻ <input>, nên phần CHỮ của radio ở lại: mọi dòng đều đọc ra "1 Bản chính 1 Bản sao" và
 * bị coi là ĐÃ CÓ FILE. Hệ quả thật (hồ sơ hỏa táng 1.012749): dòng nào cũng rẽ sang nhánh thêm
 * thành phần hồ sơ rồi chết ở "Không tìm thấy nút Thêm thành phần hồ sơ", không đính được gì.
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");

function slice(startMarker, endMarker) {
  const start = source.indexOf(startMarker);
  assert.ok(start >= 0, `Không tìm thấy ${startMarker}`);
  const end = source.indexOf(endMarker, start);
  assert.ok(end > start, `Không tìm thấy ${endMarker}`);
  return source.slice(start, end);
}

const helpers =
  slice("  // Ô chứa tệp của một dòng hồ sơ.", "  function findAttachmentFileInput(row) {") +
  slice("  // Link tải MẪU giấy tờ", "  function rowHasAttachedFile(row) {");

// ------------------------------------------------------- DOM tối giản
function matches(node, selector) {
  return selector.split(",").some((part) => {
    const sel = part.trim();
    if (!sel) return false;
    const withType = sel.match(/^input\[type='([a-z]+)'\]$/);
    if (withType) return node.tagName === "INPUT" && node.type === withType[1];
    if (sel === "a[href]") return node.tagName === "A" && !!node.attrs.href;
    return node.tagName === sel.toUpperCase();
  });
}

function el(tag, props = {}, children = []) {
  const node = {
    tagName: tag.toUpperCase(),
    type: props.type || "",
    attrs: props.attrs || {},
    text: props.text || "",
    children,
    parentElement: null,
    getAttribute(name) {
      return Object.prototype.hasOwnProperty.call(this.attrs, name) ? this.attrs[name] : null;
    },
    descendants() {
      return this.children.flatMap((child) => [child, ...child.descendants()]);
    },
    querySelectorAll(selector) {
      return this.descendants().filter((node) => matches(node, selector));
    },
    querySelector(selector) {
      return this.querySelectorAll(selector)[0] || null;
    },
    closest(selector) {
      for (let node = this; node; node = node.parentElement) {
        if (matches(node, selector)) return node;
      }
      return null;
    },
    remove() {
      const parent = this.parentElement;
      if (!parent) return;
      parent.children = parent.children.filter((child) => child !== this);
      this.parentElement = null;
    },
    cloneNode() {
      return el(
        this.tagName,
        { type: this.type, attrs: { ...this.attrs }, text: this.text },
        this.children.map((child) => child.cloneNode()),
      );
    },
    get textContent() {
      return [this.text, ...this.children.map((child) => child.textContent)].join(" ");
    },
  };
  for (const child of children) child.parentElement = node;
  return node;
}

function row(cells) {
  const node = el("TR", {}, cells);
  node.cells = cells;
  return node;
}

const context = {
  foldChoiceText(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, " ")
      .trim();
  },
  nodeText(node) {
    return String(node?.textContent || "").replace(/\s+/g, " ").trim();
  },
};
context.foldedNodeText = (node) => context.foldChoiceText(context.nodeText(node));
vm.createContext(context);
vm.runInContext(
  helpers + "\nthis.rowAttachedFileName = rowAttachedFileName;\nthis.attachmentFileCell = attachmentFileCell;",
  context,
);

function copyTypeCell() {
  return el("TD", {}, [
    el("LABEL", { text: "1 Bản chính" }, [el("INPUT", { type: "radio" })]),
    el("LABEL", { text: "1 Bản sao" }, [el("INPUT", { type: "radio" })]),
  ]);
}

const stt = () => el("TD", { text: "1" });
const name = () => el("TD", { text: "Tờ khai đề nghị hỗ trợ chi phí hỏa táng theo Mẫu số 01" });
const chooseButton = () => el("BUTTON", { text: "Chọn tệp tin" });

// 1. Dòng TRỐNG của eForm hỏa táng: STT | Tên giấy tờ | Loại bản | mẫu .doc + nút chọn tệp.
const emptyRow = row([
  stt(),
  name(),
  copyTypeCell(),
  el("TD", {}, [
    el("A", { text: "Mau so 01.doc", attrs: { href: "/storage/form/Mau so 01.doc" } }),
    chooseButton(),
  ]),
]);
assert.equal(
  context.rowAttachedFileName(emptyRow),
  "",
  "Dòng chưa đính gì mà đọc ra tên file thì mọi dòng đều bị coi là đã có file",
);

// 2. Cùng dòng đó sau khi đính: tên file thật phải đọc được (hậu điều kiện xác minh đính kèm).
const filledRow = row([
  stt(),
  name(),
  copyTypeCell(),
  el("TD", {}, [
    el("A", { text: "Mau so 01.doc", attrs: { href: "/storage/form/Mau so 01.doc" } }),
    el("SPAN", { text: "TỜ KHAI ĐỀ NGHỊ_0001.pdf" }),
    chooseButton(),
  ]),
]);
assert.equal(
  context.rowAttachedFileName(filledRow),
  "TỜ KHAI ĐỀ NGHỊ_0001.pdf",
  "Tên file đã đính phải đọc được, không bị link tải mẫu che mất",
);

// 3. Bố cục cũ (tệp ở cột 3, không có cột Loại bản) phải giữ nguyên hành vi.
const legacyRow = row([
  stt(),
  name(),
  el("TD", {}, [el("SPAN", { text: "CCCD.pdf" }), el("BUTTON", { text: "Chọn tệp đính kèm" })]),
]);
assert.equal(context.rowAttachedFileName(legacyRow), "CCCD.pdf", "Bảng cũ phải đọc tên file như trước");

// 4. Ô tệp là ô có nút chọn tệp, không phải cứ cột thứ 3.
assert.equal(
  context.attachmentFileCell(emptyRow),
  emptyRow.cells[3],
  "Cột Loại bản không được nhận nhầm là ô chứa tệp",
);

console.log("attachment-row-copy-type-column: OK");
