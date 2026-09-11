/**
 * "scope" của field: giới hạn VÙNG DÒ DOM cho đúng một khối.
 *
 * Cổng DVCQG dựng nhiều khối trên CÙNG một trang bằng các form Form.io riêng nên field-key lặp lại:
 * data[fullname] vừa là "Họ và tên người nộp hồ sơ" (cổng tự đổ tài khoản VNeID), vừa là "Họ và tên"
 * trong mục Thông tin chung của tờ đơn — hai ô đó là HAI NGƯỜI khác nhau khi nộp thay. Không giới hạn
 * vùng dò thì querySelector luôn trúng ô đầu tiên theo thứ tự tài liệu, tức khối người nộp.
 *
 * Bẫy thật gặp ở "Cấp lại Chứng chỉ hành nghề thú y": panel mang tên tờ đơn lại BỌC luôn cả khối người
 * nộp, nên scope đúng cú pháp mà vẫn trúng ô của khối người nộp. Field khai thêm scopeAway (mốc của
 * khối cấm) + scopeNear (ô neo chỉ có trong khối cần điền) để thu hẹp; không thu hẹp được thì BỎ ô.
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

const helpers = [
  slice("  function standardById(root, id) {", "  function findStandardInputForField("),
  slice("  function standardScopeRoot(field) {", "  function orderStandardFields(fields) {"),
].join("\n");

// ------------------------------------------------------- DOM tối giản (đủ cho các hàm trên)
// Selector hỗ trợ: "tag", ".class", "#id", "[name=...]", "tag[name]", "tag[name=...]", và danh sách
// ngăn cách bằng dấu phẩy.
function matches(node, selector) {
  return selector.split(",").some((part) => {
    const sel = part.trim();
    if (!sel) return false;
    const m = sel.match(/^([a-zA-Z]*)(?:\.([\w-]+))?(?:#([\w-]+))?(?:\[name(?:="([^"]*)")?\])?$/);
    if (!m) return false;
    const [, tag, cls, id, name] = m;
    if (tag && node.tagName.toLowerCase() !== tag.toLowerCase()) return false;
    if (cls && !node.classes.includes(cls)) return false;
    if (id && node.id !== id) return false;
    if (sel.includes("[name")) {
      if (!node.name) return false;
      if (name !== undefined && node.name !== name) return false;
    }
    return true;
  });
}

function makeNode(tag, props = {}, children = []) {
  const node = {
    tagName: tag.toUpperCase(),
    nodeType: 1,
    name: props.name || "",
    id: props.id || "",
    classes: props.classes || [],
    value: "",
    disabled: !!props.disabled,
    owner: props.owner || "",
    children,
    parentElement: null,
    getAttribute(attr) {
      if (attr === "name") return this.name || null;
      return null;
    },
    descendants() {
      return this.children.flatMap((child) => [child, ...child.descendants()]);
    },
    querySelectorAll(selector) {
      return this.descendants().filter((n) => matches(n, selector));
    },
    querySelector(selector) {
      return this.querySelectorAll(selector)[0] || null;
    },
  };
  children.forEach((child) => {
    child.parentElement = node;
  });
  return node;
}

const NGUOI_NOP_MARKERS = ["data[chonDoiTuong]", "data[isOwnerDossierCheck]", "data[ownerFullname]"];
const DON = ".formio-component-phuLuc1";

// Một trang thật: panel tờ đơn BỌC cả khối người nộp; khối người nộp đứng TRƯỚC khối tờ đơn.
function buildPage({ phanI = true, near = true } = {}) {
  const nguoiNop = makeNode("input", { name: "data[fullname]", owner: "nguoi-nop" });
  const phanIBlock = makeNode("div", {}, [
    makeNode("select", { name: "data[chonDoiTuong]" }),
    nguoiNop,
    makeNode("input", { name: "data[isOwnerDossierCheck]" }),
  ]);

  const toKhai = makeNode("input", { name: "data[fullname]", owner: "to-khai" });
  const donBlock = makeNode("div", {}, [
    toKhai,
    ...(near ? [makeNode("input", { name: "data[bangCapChuyenMon]", owner: "to-khai" })] : []),
  ]);

  const donPanel = makeNode(
    "div",
    { classes: ["formio-component", "formio-component-phuLuc1"] },
    phanI ? [phanIBlock, donBlock] : [donBlock],
  );
  const body = makeNode("body", {}, [donPanel]);

  const document = {
    body,
    documentElement: body,
    getElementById: (id) => body.querySelector(`#${id}`),
    querySelector: (selector) => (matches(donPanel, selector) ? donPanel : body.querySelector(selector)),
    querySelectorAll: (selector) => body.querySelectorAll(selector),
  };
  return { document, body, donPanel, donBlock, nguoiNop, toKhai };
}

function load(page) {
  const sandbox = {
    console: { warn() {} },
    document: page.document,
    CSS: { escape: (v) => String(v) },
    standardNameVariants: (names) => names,
    standardControlVisible: () => true,
    findStandardDatagridFallbackInput: () => null,
    standardOccurrence: () => null,
    pickStandardControl: (elements) => elements.find((el) => !el.disabled) || elements[0] || null,
  };
  vm.runInNewContext(
    `${helpers}
     globalThis.scopeRoot = standardScopeRoot;
     globalThis.findInput = findStandardInput;`,
    sandbox,
  );
  return sandbox;
}

// Không khai scope → dò cả trang, trúng ô ĐẦU TIÊN, tức khối người nộp.
{
  const page = buildPage();
  const api = load(page);
  const root = api.scopeRoot({ name: "data[fullname]" });
  assert.equal(root, page.document, "Không khai scope thì vùng dò là cả trang");
  assert.equal(api.findInput(["data[fullname]"], null, root).owner, "nguoi-nop");
}

// Khai scope mà panel KHÔNG bọc khối người nộp → dò đúng trong panel.
{
  const page = buildPage({ phanI: false });
  const api = load(page);
  const root = api.scopeRoot({ name: "data[fullname]", scope: DON });
  assert.equal(root, page.donPanel, "Khai scope thì vùng dò là chính khối đó");
  assert.equal(api.findInput(["data[fullname]"], null, root).owner, "to-khai");
}

// Panel tờ đơn BỌC cả khối người nộp: scope thôi là chưa đủ, phải thu hẹp bằng ô neo.
{
  const page = buildPage();
  const api = load(page);
  const field = {
    name: "data[fullname]",
    scope: DON,
    scopeNear: "data[bangCapChuyenMon]",
    scopeAway: NGUOI_NOP_MARKERS,
  };
  const root = api.scopeRoot(field);
  assert.equal(root, page.donBlock, "Vùng dò phải thu về khối tờ đơn, không bọc khối người nộp");
  assert.equal(
    api.findInput(["data[fullname]"], null, root).owner,
    "to-khai",
    "Ô của tờ đơn không được rơi vào khối người nộp",
  );
}

// Không khai scope nhưng có mốc khối cấm → vẫn thu hẹp được về khối tờ đơn.
{
  const page = buildPage();
  const api = load(page);
  const root = api.scopeRoot({
    name: "data[fullname]",
    scopeNear: "data[bangCapChuyenMon]",
    scopeAway: NGUOI_NOP_MARKERS,
  });
  assert.equal(root, page.donBlock);
}

// Trang KHÔNG render khối người nộp → mốc khối cấm vắng mặt, giữ nguyên vùng dò, vẫn điền bình thường.
{
  const page = buildPage({ phanI: false });
  const api = load(page);
  const root = api.scopeRoot({
    name: "data[fullname]",
    scope: DON,
    scopeNear: "data[bangCapChuyenMon]",
    scopeAway: NGUOI_NOP_MARKERS,
  });
  assert.equal(root, page.donPanel);
  assert.equal(api.findInput(["data[fullname]"], null, root).owner, "to-khai");
}

// Mất ô neo (form đổi layout) → KHÔNG đoán bừa: bỏ ô, thà trống còn hơn ghi đè nhân thân tài khoản.
{
  const page = buildPage({ near: false });
  const api = load(page);
  const root = api.scopeRoot({
    name: "data[fullname]",
    scope: DON,
    scopeNear: "data[bangCapChuyenMon]",
    scopeAway: NGUOI_NOP_MARKERS,
  });
  assert.equal(root, null, "Không tách được khối cấm thì phải bỏ ô");
}

// Trang không có khối đó → trả null để vòng điền bỏ qua ô.
{
  const page = buildPage();
  page.document.querySelector = () => null;
  const api = load(page);
  assert.equal(api.scopeRoot({ name: "data[fullname]", scope: DON }), null);
}

// Không khai scope (rỗng/khoảng trắng) và selector hỏng đều rơi về cả trang, không ném lỗi.
{
  const page = buildPage();
  const api = load(page);
  for (const scope of [undefined, null, "", "   "]) {
    assert.equal(api.scopeRoot({ name: "data[kinhGui]", scope }), page.document, `scope=${JSON.stringify(scope)}`);
  }
  page.document.querySelector = () => {
    throw new Error("selector hỏng");
  };
  assert.equal(api.scopeRoot({ name: "data[fullname]", scope: "!!invalid" }), page.document);
  assert.equal(api.scopeRoot(undefined), page.document, "Field rỗng không được ném lỗi");
}

console.log("field-scope-per-step: OK");
