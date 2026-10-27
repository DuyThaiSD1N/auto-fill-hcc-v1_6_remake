const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");

test("chọn cơ quan không suy ra đăng nhập từ trang trước điều hướng", () => {
  const start = sidebar.indexOf('a.type === "select_agency"');
  const end = sidebar.indexOf('a.type === "fill_agency_plan"', start);
  const block = sidebar.slice(start, end);

  assert.match(block, /ask\("__event:agency_selected", "system"\)/);
  assert.doesNotMatch(block, /pre\?\.loggedIn/);
  assert.doesNotMatch(block, /getPageContext/);
});
