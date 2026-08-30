// Mục (5) "Quan hệ với người được xác minh" của mẫu XNTTHN: chọn "Khác" thì cổng mở thêm một ô
// nhập free-text ngay cạnh. Tên ô này đổi theo phiên bản eForm nên ngoài alias, filler phải tìm
// được nó theo CẤU TRÚC (nằm trong/kề option đang tick) — nếu không, ô "Khác" luôn để trống.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8");

assert.match(
  source,
  /const el = findLegacyRawInput\(f\);/,
  'Nhánh fill "raw" phải dùng findLegacyRawInput để có fallback theo cấu trúc',
);
assert.match(
  source,
  /if \(field\.comp === "raw"\) \{\s*const input = findLegacyRawInput\(field\);/,
  "Pass sửa field bị mất cũng phải dùng cùng cách tìm input",
);

const start = source.indexOf("function legacyRadioOptionWrap");
const end = source.indexOf("\nfunction findLegacyRadioTarget", start);
assert.ok(start >= 0 && end > start, "Không tách được helper tìm ô nhập cạnh option Khác");

function node(tagName, opts = {}) {
  const self = {
    tagName: tagName.toUpperCase(),
    attrs: { ...(opts.attrs || {}), ...(opts.type ? { type: opts.type } : {}) },
    type: opts.type || "",
    checked: !!opts.checked,
    children: [],
    parentElement: null,
  };
  self.getAttribute = (name) => (name in self.attrs ? self.attrs[name] : null);
  self.append = (...kids) => {
    for (const kid of kids) {
      kid.parentElement = self;
      self.children.push(kid);
    }
    return self;
  };
  self.descendants = () => self.children.flatMap((kid) => [kid, ...kid.descendants()]);
  self.querySelectorAll = (selector) => {
    const all = self.descendants();
    if (selector === 'input[type="checkbox"]') {
      return all.filter((n) => n.tagName === "INPUT" && n.type === "checkbox");
    }
    if (selector === "input") return all.filter((n) => n.tagName === "INPUT");
    if (selector === "input.input-field-radio") {
      return all.filter((n) => n.tagName === "INPUT" && String(n.attrs.class || "").split(/\s+/).includes("input-field-radio"));
    }
    return [];
  };
  Object.defineProperty(self, "nextElementSibling", {
    get: () => {
      const kids = self.parentElement?.children || [];
      return kids[kids.indexOf(self) + 1] || null;
    },
  });
  return self;
}

function runFinder(container) {
  const sandbox = {
    CSS: { escape: (value) => String(value) },
    document: { querySelector: () => null },
    // Không tên nào khớp → buộc phải đi nhánh fallback theo cấu trúc.
    findNamedElement: (tag) => ({ el: tag === "x-radio" ? container : null, usedName: "" }),
    fieldCandidates: (f) => [f.name],
  };
  vm.runInNewContext(
    `${source.slice(start, end)}
     globalThis.findRaw = findLegacyRawInput;`,
    sandbox,
  );
  return sandbox.findRaw({ name: "quanhekhac", comp: "raw", value: "Con đẻ" });
}

// Bố cục 1: ô nhập nằm trong chính ô bọc của option "Khác" đang tick.
const inWrapText = node("input", { type: "text", attrs: { name: "khac-1" } });
const container1 = node("x-radio", { attrs: { name: "quanhevoinguoiduocxacminh" } }).append(
  node("p").append(node("input", { type: "checkbox" })),
  node("p").append(node("input", { type: "checkbox", checked: true }), inWrapText),
);
assert.equal(runFinder(container1), inWrapText, "Phải tìm được ô nhập nằm trong option Khác");

// Bố cục thật của eForm tokhaidientu.moj.gov.vn: ô nhập nằm CÙNG span với các ô tích, DÙNG CHUNG
// name với ô tích (nên không thể tìm theo name — sẽ trúng checkbox đầu tiên) và chỉ khác ở class
// input-field-radio, không có thuộc tính type.
const portalText = node("input", {
  attrs: { name: "quanhevoinguoiduocxacminh", class: "checkbox_showOnly input-field-radio" },
});
const portalContainer = node("x-radio", { attrs: { name: "quanhevoinguoiduocxacminh" } }).append(
  node("span").append(
    node("span").append(
      node("input", { type: "checkbox", attrs: { name: "quanhevoinguoiduocxacminh" } }),
      node("label", { attrs: { for: "uuid-1" } }),
      node("input", { type: "checkbox", checked: true, attrs: { name: "quanhevoinguoiduocxacminh" } }),
      node("label", { attrs: { for: "uuid-2" } }),
      portalText,
    ),
  ),
);
assert.equal(runFinder(portalContainer), portalText, "Phải tìm được ô nhập input-field-radio của cổng");

// Bố cục 2: ô nhập nằm trong khối ô tích nhưng ngoài các option.
const looseText = node("input", { type: "text", attrs: { name: "khac-2" } });
const container2 = node("x-radio", { attrs: { name: "quanhevoinguoiduocxacminh" } }).append(
  node("p").append(node("input", { type: "checkbox" })),
  node("p").append(node("input", { type: "checkbox", checked: true })),
  looseText,
);
assert.equal(runFinder(container2), looseText, "Phải tìm được ô nhập đặt ngoài các option");

// Không được nhầm chính checkbox là ô nhập khi cổng chưa render ô "Khác".
const container3 = node("x-radio", { attrs: { name: "quanhevoinguoiduocxacminh" } }).append(
  node("p").append(node("input", { type: "checkbox", checked: true })),
);
assert.equal(runFinder(container3), null, "Chưa có ô nhập thì phải trả null, không trả checkbox");

console.log("legacy other-relationship text: fallback locates the Khác input passed");
