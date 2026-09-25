const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

// Cổng MAE: mỗi dòng thành phần hồ sơ có khối "Scan tệp tin" (có input file riêng) ĐỨNG TRƯỚC khối
// "Chọn tệp tin" (button.btn_upload + input multiple). Engine attp-row phải gán vào ô của "Chọn tệp tin".
const content = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8").replace(/\r\n/g, "\n");
const start = content.indexOf("  function attpRowUploadInput(row)");
const end = content.indexOf("\n  }\n", start) + 4;
assert.ok(start >= 0 && end > start, "Không tách được attpRowUploadInput");

const fold = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/gi, "d").toLowerCase().trim();
// eslint-disable-next-line no-new-func
const attpRowUploadInput = new Function("foldChoiceText", "nodeText", `${content.slice(start, end)}; return attpRowUploadInput;`)(
  fold,
  (node) => node.textContent,
);

function el(tag, { cls = [], text = "", children = [] } = {}) {
  const node = { tag, classList: { contains: (c) => cls.includes(c) }, children, parentElement: null };
  for (const child of children) child.parentElement = node;
  const all = () => children.flatMap((c) => [c, ...c._all()]);
  node._all = all;
  Object.defineProperty(node, "textContent", { get: () => text + children.map((c) => c.textContent).join(" ") });
  node.querySelectorAll = (sel) => all().filter((n) =>
    sel.includes("input") ? n.tag === "input" : sel.split(",").map((s) => s.trim()).includes(n.tag));
  return node;
}

const scanInput = el("input");
const chooseInput = el("input");
const row = el("tr", {
  children: [el("td", {
    children: [
      el("div", { cls: ["uploadBtn"], children: [el("button", { text: "Scan tệp tin" }), el("div", { children: [scanInput] })] }),
      el("div", {
        cls: ["uploadBtn"],
        children: [el("button", { cls: ["btn_upload"], text: "Chọn tệp tin" }), el("div", { children: [chooseInput] })],
      }),
    ],
  })],
});
assert.equal(attpRowUploadInput(row), chooseInput, "Phải lấy input của nút Chọn tệp tin, không phải Scan");

const only = el("input");
assert.equal(attpRowUploadInput(el("tr", { children: [el("div", { children: [el("button", { text: "Chọn tệp tin" }), only] })] })), only);

assert.match(content, /const input = attpRowUploadInput\(row\);/, "Engine attp-row phải dùng attpRowUploadInput");
console.log("attp-row chooses the Chọn tệp tin input");
