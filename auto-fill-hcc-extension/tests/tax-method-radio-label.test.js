/**
 * Nhóm radio "Phương pháp tính thuế" trên cổng ĐKKD (TaxInformation.aspx) không được tick.
 *
 * Backend gửi NHÃN ("Khấu trừ"); bộ điền radio so nhãn đó với chữ hiển thị cạnh từng ô. Test dựng
 * lại hai kiểu markup mà `parentElement.textContent` đọc sai, để chốt rằng radioLabelText đọc đúng
 * nhãn của TỪNG ô.
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");

const start = source.indexOf("  function radioTrailingText(radio) {");
const end = source.indexOf("  async function fillStandardRadio", start);
assert.ok(start >= 0 && end > start, "Không tách được helper đọc nhãn radio");

// ---------------------------------------------------------------- DOM tối giản
// Chỉ dựng đúng những gì helper dùng: nodeType, nodeValue, textContent, nextSibling, parentElement,
// tagName, matches, querySelector, closest, id.
function text(value) {
  return { nodeType: 3, nodeValue: value, textContent: value, nextSibling: null, parentElement: null };
}

function el(tagName, attrs, children) {
  const node = {
    nodeType: 1,
    tagName: tagName.toUpperCase(),
    id: (attrs && attrs.id) || "",
    type: (attrs && attrs.type) || "",
    value: (attrs && attrs.value) || "",
    nextSibling: null,
    parentElement: null,
    children: children || [],
  };
  node.matches = (selector) =>
    selector === 'input[type="radio"]' && node.tagName === "INPUT" && node.type === "radio";
  node.querySelector = (selector) => {
    for (const child of node.children) {
      if (child.nodeType !== 1) continue;
      if (child.matches(selector)) return child;
      const deeper = child.querySelector(selector);
      if (deeper) return deeper;
    }
    return null;
  };
  node.closest = (selector) => {
    let current = node;
    while (current) {
      if (current.tagName === selector.toUpperCase()) return current;
      current = current.parentElement;
    }
    return null;
  };
  Object.defineProperty(node, "textContent", {
    get: () => node.children.map((child) => child.textContent).join(""),
  });
  for (let i = 0; i < node.children.length; i++) {
    node.children[i].parentElement = node;
    node.children[i].nextSibling = node.children[i + 1] || null;
  }
  return node;
}

function radios(root) {
  const out = [];
  const walk = (node) => {
    if (node.nodeType !== 1) return;
    if (node.matches('input[type="radio"]')) out.push(node);
    node.children.forEach(walk);
  };
  walk(root);
  return out;
}

function makeSandbox(labelsByFor) {
  const sandbox = {
    CSS: { escape: (value) => value },
    document: {
      querySelector: (selector) => {
        const match = /^label\[for="(.*)"\]$/.exec(selector);
        if (!match) return null;
        const label = labelsByFor[match[1]];
        return label ? { textContent: label } : null;
      },
    },
    foldChoiceText: (value) =>
      String(value || "")
        .replace(/Đ/g, "D")
        .replace(/đ/g, "d")
        .normalize("NFD")
        .replace(/[̀-ͯ]/g, "")
        .replace(/\s*[-–—]+\s*/g, " ")
        .toLowerCase()
        .replace(/\s+/g, " ")
        .trim(),
  };
  vm.runInNewContext(
    `${source.slice(start, end)}
     globalThis.radioLabelText = radioLabelText;
     globalThis.radioValueMatches = radioValueMatches;`,
    sandbox,
  );
  return sandbox;
}

const OPTIONS = ["Khấu trừ", "Trực tiếp trên GTGT", "Trực tiếp trên doanh số", "Không phải nộp thuế GTGT"];
const NAME = "ctl00$C$UC_DW_TAXEditCtl$TAX_CAL_METHOD_IDRbBox";

/** Ô nào được tick khi bộ điền tìm giá trị `value` trong nhóm — null nghĩa là KHÔNG tick ô nào. */
function pick(sandbox, group, value) {
  const matched = group.find((radio) => sandbox.radioValueMatches(radio, value));
  return matched ? OPTIONS[group.indexOf(matched)] : null;
}

// ---- Kiểu 1: input và chữ ở HAI ô <td> khác nhau, không có <label for> ----------------------
{
  const table = el("table", {}, OPTIONS.map((label, index) =>
    el("tr", {}, [
      el("td", {}, [el("input", { type: "radio", id: `r_${index}`, value: String(index) })]),
      el("td", {}, [text(label)]),
    ]),
  ));
  const sandbox = makeSandbox({});
  const group = radios(table);

  assert.equal(group.length, 4, "Phải dựng đủ bốn ô radio");
  assert.deepEqual(
    group.map((radio) => sandbox.radioLabelText(radio)),
    OPTIONS,
    "Nhãn ở ô <td> bên cạnh phải đọc được cho TỪNG ô radio",
  );
  for (const wanted of OPTIONS) {
    assert.equal(pick(sandbox, group, wanted), wanted, `Phải tick đúng ô "${wanted}"`);
  }
}

// ---- Kiểu 2: CẢ BỐN ô nằm chung MỘT thẻ cha, chữ là text node ngay sau input ----------------
{
  const children = [];
  OPTIONS.forEach((label, index) => {
    children.push(el("input", { type: "radio", id: `f_${index}`, value: String(index) }));
    children.push(text(label));
    children.push(el("br", {}, []));
  });
  const box = el("div", {}, children);
  const sandbox = makeSandbox({});
  const group = radios(box);

  assert.deepEqual(
    group.map((radio) => sandbox.radioLabelText(radio)),
    OPTIONS,
    "Bốn ô chung một thẻ cha vẫn phải tách được nhãn riêng của từng ô",
  );
  // Đây là hồi quy của lỗi tick nhầm: trước đây mọi ô đều trả về chuỗi gộp cả bốn nhãn nên ô nào
  // cũng "khớp" và bộ điền luôn chọn ô ĐẦU danh sách.
  assert.equal(
    pick(sandbox, group, "Không phải nộp thuế GTGT"),
    "Không phải nộp thuế GTGT",
    "Không được tick nhầm ô đầu danh sách",
  );
  assert.equal(pick(sandbox, group, "Khấu trừ"), "Khấu trừ");
}

// ---- Kiểu 3: có <label for> chuẩn — đường cũ vẫn phải chạy nguyên vẹn -----------------------
{
  const box = el("div", {}, OPTIONS.map((_, index) =>
    el("input", { type: "radio", id: `g_${index}`, value: String(index) }),
  ));
  const labelsByFor = {};
  OPTIONS.forEach((label, index) => { labelsByFor[`g_${index}`] = label; });
  const sandbox = makeSandbox(labelsByFor);
  const group = radios(box);

  assert.deepEqual(group.map((radio) => sandbox.radioLabelText(radio)), OPTIONS);
  assert.equal(pick(sandbox, group, "Trực tiếp trên doanh số"), "Trực tiếp trên doanh số");
}

// ---- Giá trị lạ vẫn KHÔNG được tick bừa ----------------------------------------------------
{
  const table = el("table", {}, OPTIONS.map((label, index) =>
    el("tr", {}, [
      el("td", {}, [el("input", { type: "radio", id: `h_${index}`, value: String(index) })]),
      el("td", {}, [text(label)]),
    ]),
  ));
  const sandbox = makeSandbox({});
  const group = radios(table);

  assert.equal(
    pick(sandbox, group, "Hạch toán độc lập"),
    null,
    "Giá trị không thuộc nhóm thì tuyệt đối không tick ô nào",
  );
}

console.log(`Tên nhóm radio dùng trong test: ${NAME}`);
console.log("tax-method-radio-label: OK");
