const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const strip = (src) => src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const popup = strip(fs.readFileSync(path.join(root, "popup.js"), "utf8"));
const endpoints = strip(fs.readFileSync(path.join(root, "api/endpoints.js"), "utf8"));

test("ảnh HEIC được đổi sang JPG ở cả hai lối thêm tệp (chọn tệp, kéo thả)", () => {
  assert.match(popup, /fileInput\.addEventListener\("change", async \(\) => \{[\s\S]{0,200}await convertHeicFiles\(picked\)/);
  assert.match(popup, /async function addDroppedFiles\([\s\S]{0,400}await convertHeicFiles\(dropped\)/);
});

test("đổi HEIC gọi API BE, lỗi thì giữ tệp gốc", () => {
  assert.match(endpoints, /apiCall\("\/api\/v1\/files\/convert-image", \{ method: "POST", body: form \}\)/);
  assert.match(popup, /catch \(e\) \{[\s\S]{0,120}out\.push\(f\);/);
});
