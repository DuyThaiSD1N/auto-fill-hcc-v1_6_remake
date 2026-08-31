// Dropdown "Dân tộc" của cổng tư pháp: khớp lỏng bằng includes() thô chọn nhầm "Kháng" khi cần
// "Hán" (chuỗi "hán" nằm lọt trong "k|hán|g") — lỗi gặp ở thủ tục kết hôn có yếu tố nước ngoài,
// chồng người Trung Quốc bị điền dân tộc "Kháng". Phải: gõ "Hán" rồi chọn đúng option "Hán (Hoa)".
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8");

function slice(from, to) {
  const start = source.indexOf(from);
  const end = source.indexOf(to, start);
  assert.ok(start >= 0 && end > start, `Không cắt được đoạn "${from}"`);
  return source.slice(start, end);
}

const sandbox = {
  console: { warn() {}, log() {} },
  sleep: async () => {},
  waitFor: async (fn) => !!fn(),
  markFilled: () => {},
  markUnfilled: () => {},
  setNativeValue: (el, value) => { el.value = value; },
  norm: (s) => (s || "").trim().toLowerCase().replace(/\s+/g, " "),
};
vm.runInNewContext(
  slice("const isPlaceholderOpt", "function foldLegacyChoice")
  + slice("function foldLegacyChoice", "// Khớp \"lỏng\" phải theo RANH GIỚI TỪ")
  + slice("function legacyChoiceHasWord", "async function fillSelect")
  + "globalThis.pickInWidget = pickInWidget;"
  + "globalThis.legacyChoiceHasWord = legacyChoiceHasWord;",
  sandbox,
);

/** Dropdown giả: header + danh sách option + ô "Tìm kiếm..." lọc theo chuỗi CÓ DẤU như cổng thật. */
function dropdown(options) {
  const picked = [];
  const search = { value: "" };
  const optionNodes = options.map((text) => ({
    get textContent() { return text; },
    click() { picked.push(text); },
  }));
  const visible = () => {
    const q = search.value.trim().toLowerCase();
    if (!q) return optionNodes;
    const hits = optionNodes.filter((o) => o.textContent.toLowerCase().includes(q));
    return hits.length ? hits : [{ textContent: "Không tìm thấy dữ liệu", click() {} }];
  };
  const box = { querySelectorAll: () => visible() };
  const root = {
    picked,
    search,
    querySelector: (sel) => {
      if (sel === ".input-field-select") return { click() {} };
      if (sel === ".input-field-select-options") return box;
      if (sel.includes("Tìm kiếm")) return search;
      return null;
    },
  };
  return root;
}

const DAN_TOC = ["-- Chọn --", "Kinh", "Kháng", "Hán (Hoa)", "Hoa", "Mông", "Mông (Hmông)"];

(async () => {
  // 1) "Hán" → option "Hán (Hoa)", tuyệt đối không phải "Kháng".
  let root = dropdown(DAN_TOC);
  assert.equal(await sandbox.pickInWidget(root, "Hán"), true, "không chọn được dân tộc Hán");
  assert.deepEqual(root.picked, ["Hán (Hoa)"]);

  // 2) Khớp chính xác vẫn thắng option "chứa" nó: "Mông" không được nhảy sang "Mông (Hmông)".
  root = dropdown(DAN_TOC);
  assert.equal(await sandbox.pickInWidget(root, "Mông"), true);
  assert.deepEqual(root.picked, ["Mông"]);

  // 3) Khớp chỉ khác dấu vẫn nhận: "Kinh" thường, "HAN (HOA)" viết hoa không dấu.
  root = dropdown(DAN_TOC);
  assert.equal(await sandbox.pickInWidget(root, "HAN (HOA)"), true);
  assert.deepEqual(root.picked, ["Hán (Hoa)"]);

  // 4) Danh sách KHÔNG có "Hán": thà bỏ trống (tô đỏ để người dùng sửa) còn hơn điền bừa "Kháng".
  root = dropdown(["-- Chọn --", "Kinh", "Kháng", "Hoa"]);
  assert.equal(await sandbox.pickInWidget(root, "Hán"), false);
  assert.deepEqual(root.picked, []);

  // 5) Ranh giới từ: chỉ chấp nhận cụm đứng trọn vẹn.
  assert.equal(sandbox.legacyChoiceHasWord("kháng", "hán"), false);
  assert.equal(sandbox.legacyChoiceHasWord("hán (hoa)", "hán"), true);
  assert.equal(sandbox.legacyChoiceHasWord("bru - vân kiều", "vân kiều"), true);

  console.log("legacy-ethnicity-word-boundary: OK");
})();
