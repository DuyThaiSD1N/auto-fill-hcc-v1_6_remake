const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");
const start = source.indexOf("// Các thủ tục cần đối chiếu người yêu cầu");
const end = source.indexOf('action: "collectFormContext"', start);

assert.ok(start >= 0 && end > start, "Không tìm thấy khối thu thập formContext");

// Bỏ comment để comment không tự khớp assert.
const condition = source.slice(start, end).replace(/\/\/.*$/gm, "");
assert.match(
  condition,
  /cfg\.collectFormContext === true\s*\)\s*\{/,
  "Cờ collectFormContext từ registry BE phải bật thu formContext mà không cần danh sách cứng",
);
assert.match(
  condition,
  /cfg\.key === "dieu-chinh-huu-tri-xa-hoi"/,
  "Danh sách cứng phải giữ nguyên cho BE bản cũ chưa trả cờ",
);

console.log("form context registry flag passed");
