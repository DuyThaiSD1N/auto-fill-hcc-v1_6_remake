const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");

test("fallback kê khai đòi đủ mẫu điện tử, nút Xem trước và form thật", () => {
  assert.match(content, /function collectDeclarationPageSignals\(\)/);
  assert.match(content, /text\.startsWith\("noi dung mau"\)/);
  assert.match(content, /text\.includes\("dien tu tuong tac"\)/);
  assert.match(content, /=== "xem truoc"/);
  assert.match(content, /declarationTarget:\s*hasInteractiveTemplateHeading && hasPreviewControl/);
  assert.match(content, /if \(!formKind\) return \{ declarationTarget: false/);
});

test("sidebar đọc tín hiệu kê khai từ frame thật và chuyển xuyên page status", () => {
  assert.match(sidebar, /action: "getDeclarationContext"/);
  assert.match(sidebar, /declarationTarget:\s*!!c\.declarationTarget/);
  assert.match(sidebar, /ctx\.declarationTarget \? 1 : 0/);
});
