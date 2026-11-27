// Cổng DVC quốc gia mới hiện tên tệp lên dòng ngay khi bắt đầu tải; tải hỏng giữ dòng đỏ, và nạp chồng lúc tệp trước
// đang tải thì cổng bỏ qua tệp mới hoặc để dòng kẹt "đang tải" không fileId → tên tệp không đủ làm bằng chứng.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const strip = (src) => src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const main = strip(fs.readFileSync(path.join(root, "content/surveyjs-main.js"), "utf8"));
const fill = strip(fs.readFileSync(path.join(root, "content/fill-surveyjs.js"), "utf8"));

test("MAIN world đọc trạng thái tải từ props React và xoá dòng tệp theo trạng thái", () => {
  assert.match(main, /memoizedProps\?\.fileInfo/);
  assert.match(main, /info\.uploadStatus/);
  assert.match(main, /payload\.op === "uploadStatus"/);
  assert.match(main, /payload\.op === "removeUploads"/);
  assert.match(main, /statuses\.includes\(e\.status\)/);
  // DOM chỉ trỏ một trong hai bản fiber (current/alternate) → phải xét cả bản kia, không thì đọc ra trạng thái cũ.
  assert.match(main, /f\.alternate\?\.memoizedProps\?\.fileInfo/);
});

test("tải TỪNG tệp: chờ trạng thái thật trước tệp kế; kẹt thì xoá, nạp lại một lần; hỏng thì báo, không ghi nhớ", () => {
  const verify = fill.indexOf("let outcome = ok ? await uploadOutcome(file.name, firstTicks)");
  const retry = fill.indexOf('if (outcome === "timeout") {');
  const fail = fill.indexOf('if (outcome === "error" || outcome === "timeout") {');
  const remember = fill.indexOf("rememberAttached({ hash, name: file.name, row: rowKey })");
  assert.ok(verify > 0 && retry > verify && fail > retry && remember > fail, "kiểm → nạp lại → báo lỗi → mới ghi nhớ");
  assert.match(fill, /op: "removeUploads", name: file\.name, statuses: \["pending", "uploading"\]/);
  // Lý do theo toast cổng: chỉ toast nói dung lượng mới báo dung lượng; "Upload file thất bại" thì không.
  assert.match(fill, /toastsBefore\.has\(msg\)\) \|\| ""/);
  assert.match(fill, /tệp quá lớn \(cổng chỉ nhận tệp dưới 2 MB\)/);
  assert.match(fill, /đính kèm file thất bại/);
  assert.doesNotMatch(fill, /thường do tệp quá lớn/);
  assert.match(fill, /cổng không ghi nhận tệp sau khi tải/);
  assert.match(fill, /op: "removeUploads", statuses: \["error", "pending", "uploading"\] \}, 30000/);
  assert.match(fill, /if \(!last\) return "unknown";/);
  assert.doesNotMatch(fill, /uploading\.push\(/);
});

// Đăng ký thành lập hộ kinh doanh (DVCQG): giấy ủy quyền nộp hồ sơ vào dòng chỉ có sau khi chọn "Trường hợp ủy quyền…"
// ở ô "Chọn trường hợp thực hiện" → chọn trường hợp TRƯỚC khi tải tệp; không thấy dòng thì về dòng dự phòng.
test("chọn trường hợp thực hiện trước vòng tải tệp, sau khi dọn dòng hỏng", () => {
  const clean = fill.indexOf('op: "removeUploads", statuses: ["error", "pending", "uploading"] }, 30000');
  const choose = fill.indexOf("const caseError = await chooseExecutionCase(attachments);");
  const loop = fill.indexOf("for (let i = 0; i < attachments.length; i++)", choose);
  assert.ok(clean > 0 && choose > clean && loop > choose, "dọn → chọn trường hợp → tải tệp");
  assert.match(fill, /if \(caseError\) errors\.push\(caseError\);/);
});

test("findUploadRow: khớp dòng theo tên, không thấy thì về dòng dự phòng, không có dự phòng thì null", () => {
  const text = fill.replace(/\r/g, "");
  const start = text.indexOf("function findUploadRow(item) {");
  const end = text.indexOf("\n  }\n", start);
  const src = text.slice(start, end + 4);
  const fold = (s) => String(s ?? "").replace(/Đ/g, "D").replace(/đ/g, "d").normalize("NFD")
    .replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  const row = (text) => ({ textContent: text });
  const make = (rows) => new Function("fold", "uploadRows", `${src}; return findUploadRow;`)(fold, () => rows);
  const giayDeNghi = row("1 - Giấy đề nghị đăng ký hộ kinh doanh; 1 0");
  const uyQuyen = row("6 Văn bản ủy quyền cho cá nhân thực hiện thủ tục liên quan đến đăng ký hộ kinh doanh 1 0");
  const item = { slotName: "ủy quyền cho cá nhân", fallbackSlotName: "Giấy đề nghị đăng ký hộ kinh doanh" };
  assert.equal(make([giayDeNghi, uyQuyen])(item), uyQuyen);
  assert.equal(make([giayDeNghi])(item), giayDeNghi);
  assert.equal(make([giayDeNghi])({ slotName: "ủy quyền cho cá nhân" }), null);
});

// ---- cc-select "Chọn trường hợp thực hiện" chạy trên DOM giả tối giản (không có jsdom) ----
// Ô bản large: chữ "Chọn trường hợp thực hiện" CHỈ là placeholder của input, không có .cc-select-selected-label; option
// nằm trong .cc-select-option-list, chọn xong ô điều khiển hiện chữ của option.
class FakeText {
  constructor(text) { this.nodeType = 3; this.textContent = text; this.parentElement = null; }
}

class FakeEl {
  constructor(tag, { cls = "", attrs = {}, text = "" } = {}) {
    this.nodeType = 1;
    this.tagName = tag.toUpperCase();
    this.classList = cls.split(/\s+/).filter(Boolean);
    this.attrs = { ...attrs };
    this.childNodes = [];
    this.parentElement = null;
    this.handlers = {};
    this.value = attrs.value || "";
    if (text) this.append(new FakeText(text));
  }
  append(...nodes) {
    for (const node of nodes) { node.parentElement = this; this.childNodes.push(node); }
    return this;
  }
  remove() {
    const parent = this.parentElement;
    if (parent) parent.childNodes = parent.childNodes.filter((n) => n !== this);
    this.parentElement = null;
  }
  get children() { return this.childNodes.filter((n) => n.nodeType === 1); }
  get textContent() { return this.childNodes.map((n) => n.textContent).join(""); }
  getAttribute(name) { return name in this.attrs ? this.attrs[name] : null; }
  matchesOne(sel) {
    sel = sel.trim();
    let m;
    if ((m = sel.match(/^\[([\w-]+)(?:="([^"]*)")?\]$/))) {
      return m[2] === undefined ? m[1] in this.attrs : this.attrs[m[1]] === m[2];
    }
    const [tag, ...classes] = sel.split(".");
    if (tag && tag.toUpperCase() !== this.tagName) return false;
    return classes.every((c) => this.classList.includes(c));
  }
  matches(sel) { return sel.split(",").some((s) => this.matchesOne(s)); }
  descendants() {
    const out = [];
    for (const child of this.children) out.push(child, ...child.descendants());
    return out;
  }
  querySelectorAll(sel) { return this.descendants().filter((el) => el.matches(sel)); }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  closest(sel) {
    for (let el = this; el; el = el.parentElement) if (el.matches(sel)) return el;
    return null;
  }
  contains(other) {
    for (let el = other; el; el = el.parentElement) if (el === this) return true;
    return false;
  }
  on(type, fn) { (this.handlers[type] = this.handlers[type] || []).push(fn); return this; }
  dispatchEvent(event) {
    for (let el = this; el; el = el.parentElement) for (const fn of el.handlers[event.type] || []) fn(event);
    return true;
  }
}

function ccPage() {
  const body = new FakeEl("body");
  // Hình thức nhận kết quả (đã chọn sẵn).
  const result = new FakeEl("div").append(
    new FakeEl("span", { text: "Hình thức nhận kết quả" }),
    new FakeEl("div", { cls: "cc-select-wrapper" }).append(new FakeEl("div", { cls: "cc-select" }).append(
      new FakeEl("span", { cls: "cc-select-selected-label", text: "Trả kết quả tại bộ phận tiếp nhận và trả kết quả" }))));
  // THÀNH PHẦN HỒ SƠ + ô chọn trường hợp (placeholder trong input).
  const control = new FakeEl("div", { cls: "cc-select cc-select-large" }).append(
    new FakeEl("input", { attrs: { placeholder: "Chọn trường hợp thực hiện" } }));
  const container = new FakeEl("div", { cls: "cc-select-container" }).append(control);
  const wrapper = new FakeEl("div", { cls: "cc-select-wrapper" }).append(container);
  const section = new FakeEl("div").append(
    new FakeEl("div").append(new FakeEl("h3", { text: "THÀNH PHẦN HỒ SƠ" })),
    new FakeEl("div", { cls: "p-4" }).append(wrapper));
  body.append(result, section);
  let dropdown = null;
  const close = () => { dropdown?.remove(); dropdown = null; };
  control.on("click", () => {
    if (dropdown) return close();
    const option = new FakeEl("div", { cls: "cc-select-option",
      text: "Trường hợp ủy quyền thực hiện thủ tục thì hồ sơ phải kèm theo một trong những giấy tờ sau:" });
    option.on("click", (e) => {
      e.stopped = true;
      control.childNodes = [];
      control.append(new FakeEl("span", { text: option.textContent }));
      close();
    });
    dropdown = new FakeEl("div", { cls: "cc-select-dropdown" }).append(
      new FakeEl("div", { cls: "cc-select-search-wrapper" }).append(
        new FakeEl("input", { cls: "cc-select-search-input", attrs: { placeholder: "Nhập thông tin tìm kiếm..." } })),
      new FakeEl("div", { cls: "cc-select-option-list" }).append(option));
    container.append(dropdown);
  });
  return { body, control };
}

function loadCc(body) {
  const text = fill.replace(/\r/g, "");
  const start = text.indexOf("function ccClick(el) {");
  const end = text.indexOf("function uploadRows()", start);
  assert.ok(start > 0 && end > start, "không thấy khối cc-select");
  const fold = (s) => String(s ?? "").replace(/Đ/g, "D").replace(/đ/g, "d").normalize("NFD")
    .replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  const document = { querySelectorAll: (sel) => body.querySelectorAll(sel), activeElement: null };
  const isVisible = (el) => !!el && body.contains(el);
  const quiet = { info() {}, warn() {} };
  class Ev { constructor(type) { this.type = type; } }
  return new Function("fold", "sleep", "isVisible", "document", "window", "MouseEvent", "KeyboardEvent", "console", "CC_LOG",
    `${text.slice(start, end)}; return { chooseExecutionCase, executionCaseWrapper, resultMethodWrapper, ccSelectedText };`)(
    fold, async () => {}, isVisible, document, {}, Ev, Ev, quiet, "[cc-select]");
}

test("chọn trường hợp thực hiện: ô bản large chỉ có placeholder vẫn tìm ra và chọn được option ủy quyền", async () => {
  const { body, control } = ccPage();
  const cc = loadCc(body);
  const wrapper = cc.executionCaseWrapper();
  assert.ok(wrapper && wrapper.contains(control), "phải tìm ra ô Chọn trường hợp thực hiện");
  assert.notEqual(wrapper, cc.resultMethodWrapper());
  const error = await cc.chooseExecutionCase([
    { fileIndex: 0 },
    { fileIndex: 1, executionCase: "Trường hợp ủy quyền thực hiện thủ tục", executionCasePrefer: "ca nhan" },
  ]);
  assert.equal(error, "");
  assert.match(cc.ccSelectedText(wrapper), /^truong hop uy quyen thuc hien thu tuc/);
  // Đã chọn sẵn thì không bấm lại (không đổi trường hợp).
  assert.equal(await cc.chooseExecutionCase([{ executionCase: "Trường hợp ủy quyền thực hiện thủ tục" }]), "");
});

test("chọn trường hợp thực hiện: không có ô thì báo lỗi để cán bộ chọn tay, không có mục cần thì bỏ qua", async () => {
  const cc = loadCc(new FakeEl("body"));
  assert.match(await cc.chooseExecutionCase([{ executionCase: "Trường hợp ủy quyền thực hiện thủ tục" }]),
    /Không chọn được/);
  assert.equal(await cc.chooseExecutionCase([{ fileIndex: 0 }]), "");
});
