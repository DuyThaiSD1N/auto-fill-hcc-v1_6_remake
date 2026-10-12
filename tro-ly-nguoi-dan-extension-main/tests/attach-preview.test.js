// Cổng DVC quốc gia mới: nút xem tệp ĐÃ đính (lấy lại từ server cổng theo fileId) cạnh nút "Xóa file".
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const FILE = "content/attach-preview-main.js";
const code = () => read(FILE).replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

test("biên dịch được và nạp ở MAIN world chỉ trên dichvucong.gov.vn", () => {
  assert.doesNotThrow(() => new vm.Script(read(FILE), { filename: FILE }));
  const entry = JSON.parse(read("manifest.json")).content_scripts.find((e) => e.js.includes(FILE));
  assert.ok(entry, "manifest thiếu " + FILE);
  assert.strictEqual(entry.world, "MAIN");
  assert.deepStrictEqual(entry.matches, ["https://dichvucong.gov.vn/*"]);
  assert.match(code(), /location\.hostname/);
});

test("lấy tệp từ API của cổng theo fileId với token của trang", () => {
  const src = code();
  assert.match(src, /\/api\/v1\/submitting\/preview-attachment-by-citizen/);
  assert.match(src, /citizenCitizenAccessToken/);
  assert.match(src, /Authorization: `Bearer \$\{token\}`/);
  assert.match(src, /memoizedProps\?\.fileInfo/);
  assert.match(src, /info\.fileId \|\| info\.id/);
  assert.match(src, /f\.alternate\?\.memoizedProps\?\.fileInfo/);
});

test("gắn nút cạnh nút Xóa file, không dùng innerHTML, chống gắn trùng", () => {
  const src = code();
  assert.match(src, /button\[title="Xóa file"\]/);
  assert.match(src, /del\.before\(btn\)/);
  assert.match(src, /hasAttribute\(MARK\)/);
  assert.doesNotMatch(src, /innerHTML/);
});

test("cờ chặn và thuộc tính đánh dấu dùng chung tên với extension còn lại (máy cài cả hai chỉ một bản chạy)", () => {
  const src = code();
  assert.match(src, /if \(window\.__HCC_ATTACH_PREVIEW__\) return;\s*window\.__HCC_ATTACH_PREVIEW__ = true;/);
  assert.match(src, /const MARK = "data-hcc-preview";/);
});
