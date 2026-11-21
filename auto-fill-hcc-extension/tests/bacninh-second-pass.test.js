// Điền đợt 2 trên form Liferay cổng Bắc Ninh: bộ ghi lại ô chỉ ghi ô cán bộ chưa sửa, dùng lại bộ điền lượt đầu.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const read = (file) => fs.readFileSync(path.join(__dirname, "..", file), "utf8");

test("fill-bacninh xuất bộ ghi đợt 2, so giá trị đang hiện với from trước khi ghi", () => {
  const filler = read("content/fill-bacninh.js");
  const body = filler.slice(filler.indexOf("async function patchFormBacNinh"), filler.indexOf("Object.assign(H, {"));
  assert.match(body, /const shown = readBacNinhField\(f\);/);
  assert.match(body, /bnShownText\(shown\) !== \(isNew \? "" : bnShownText\(f\.from\)\)/);
  assert.match(body, /await fillFormBacNinh\(todo\)/);
  assert.match(filler, /Object\.assign\(H, \{\s*patchFormBacNinh,/);
});

test("handler patchFields chọn bộ ghi Bắc Ninh; popup khai năng lực secondPassBacNinh", () => {
  assert.match(read("content.js"), /formKind === "bacninh" \? H\.patchFormBacNinh/);
  assert.match(read("popup.js"), /"secondPassFormio", "secondPassBacNinh"\];/);
});
