// Điền lại sau khi điều chỉnh giấy tờ: BE gửi removeListed (bản ghi trợ lý thêm ở lượt trước mà bộ giấy mới không còn)
// → engine standard bấm nút xoá dòng của cổng TRƯỚC khi tính panel đã có trong danh sách và trước khi thêm bản ghi mới.
// Thiếu bước này xe của bộ giấy cũ còn nguyên trong danh sách phù hiệu (cổng Bộ Xây dựng). BE: flow._with_refill_cleanup.
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const strip = (src) => src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const core = strip(fs.readFileSync(path.resolve(__dirname, "..", "content", "fill-core.js"), "utf8"));

test("có hàm xoá dòng theo removeListed, bấm nút xoá của chính dòng đó", () => {
  const fn = core.slice(core.indexOf("async function removeStandardListedRows("));
  assert.ok(fn.length > 50, "thiếu removeStandardListedRows");
  const body = fn.slice(0, fn.indexOf("\n}\n"));
  assert.match(body, /f\.comp === "dom-click" && Array\.isArray\(f\.removeListed\)/);
  assert.match(body, /\[data-dsp-action="delete"\]/);
  assert.match(body, /btn\.click\(\)/);
});

test("xoá dòng cũ chạy TRƯỚC khi tính panel đã có trong danh sách", () => {
  const removeAt = core.indexOf("await removeStandardListedRows(fields);");
  const listedAt = core.indexOf("const listedPanels = new Set(fields");
  assert.ok(removeAt > 0 && listedAt > removeAt);
});
