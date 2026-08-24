// Mục (5) "Quan hệ với người được cấp bản sao" của mẫu trích lục dựng option bằng
// <p class="p_checkbox_custom radio-custom"> chứa input ẩn + text nhãn, id chỉ có hậu tố SỐ
// (uuid-7) và KHÔNG có <label for>. Cả hai nhánh khớp cũ đều trượt → radio không bao giờ tick được.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8");

const start = source.indexOf("function legacyRadioOptionWrap");
const end = source.indexOf("\nfunction legacyFieldState", start);
assert.ok(start >= 0 && end > start, "Không tách được helper khớp option radio");

const sandbox = {
  CSS: { escape: (value) => String(value) },
  foldLegacyChoice: (value) =>
    String(value || "")
      .replace(/Đ/g, "D")
      .replace(/đ/g, "d")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/\s*[-–—‐‑]+\s*/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase(),
};
vm.runInNewContext(
  `${source.slice(start, end)}
   globalThis.findTarget = findLegacyRadioTarget;
   globalThis.markTarget = legacyRadioMarkTarget;`,
  sandbox,
);

function node(tagName, opts = {}) {
  const self = {
    tagName: tagName.toUpperCase(),
    id: opts.id || "",
    type: opts.type || "",
    htmlFor: opts.htmlFor || "",
    checked: !!opts.checked,
    ownText: opts.text || "",
    children: [],
    parentElement: null,
  };
  self.append = (...kids) => {
    for (const kid of kids) {
      kid.parentElement = self;
      self.children.push(kid);
    }
    return self;
  };
  self.descendants = () => self.children.flatMap((kid) => [kid, ...kid.descendants()]);
  Object.defineProperty(self, "textContent", {
    get: () => self.ownText + self.children.map((kid) => kid.textContent).join(""),
  });
  self.querySelectorAll = (selector) => {
    if (selector === 'input[type="checkbox"]') {
      return self.descendants().filter((n) => n.tagName === "INPUT" && n.type === "checkbox");
    }
    const forMatch = /^label\[for="(.*)"\]$/.exec(selector);
    if (forMatch) {
      return self.descendants().filter((n) => n.tagName === "LABEL" && n.htmlFor === forMatch[1]);
    }
    return [];
  };
  self.querySelector = (selector) => self.querySelectorAll(selector)[0] || null;
  return self;
}

const UUID = "b0240d4a-b699-4fec-8cf8-57e80b3a09c8";
const OPTIONS = ["Bản thân", "Con Đẻ", "Bố Đẻ", "Bố nuôi", "Mẹ đẻ", "Khác"];

const inner = node("span");
const wraps = OPTIONS.map((label, index) => {
  const wrap = node("p", { text: label });
  wrap.append(node("input", { id: `${UUID}-${index}`, type: "checkbox" }));
  inner.append(wrap);
  return wrap;
});
const trichLuc = node("x-radio").append(node("span").append(inner));

for (const [index, label] of OPTIONS.entries()) {
  const target = sandbox.findTarget(trichLuc, label);
  assert.ok(target, `Không tìm thấy option "${label}" của mẫu trích lục`);
  assert.equal(target.id, `${UUID}-${index}`, `Tick nhầm option cho "${label}"`);
  assert.equal(
    sandbox.markTarget(trichLuc, target),
    wraps[index],
    "Input mẫu trích lục là display:none → phải tô màu lên ô bọc, không phải input",
  );
}

assert.equal(
  sandbox.findTarget(trichLuc, "Cụ nội"),
  null,
  "Giá trị không khớp option nào phải trả null, không tick bừa ô đầu tiên",
);
assert.equal(sandbox.findTarget(trichLuc, ""), null, "Giá trị rỗng không được khớp option nào");

// Mẫu khai sinh legacy: id có hậu tố mã option + <label for> → hai nhánh cũ vẫn phải chạy nguyên vẹn.
const legacy = node("x-radio");
const legacyInner = node("span");
for (const code of ["BanThan", "ChaDe", "MeDe"]) {
  legacyInner.append(
    node("input", { id: `ks-${code}`, type: "checkbox" }),
    node("label", { htmlFor: `ks-${code}`, text: code === "ChaDe" ? "Cha đẻ" : code }),
  );
}
legacy.append(legacyInner);

assert.equal(sandbox.findTarget(legacy, "ChaDe").id, "ks-ChaDe", "Hậu tố mã option phải vẫn khớp");
assert.equal(sandbox.findTarget(legacy, "Cha đẻ").id, "ks-ChaDe", "Nhãn <label for> phải vẫn khớp");
assert.equal(
  sandbox.markTarget(legacy, sandbox.findTarget(legacy, "ChaDe")).tagName,
  "LABEL",
  "Có <label for> thì vẫn tô màu lên label như cũ",
);

console.log("legacy trich luc relationship radio: option matching without label[for] passed");
