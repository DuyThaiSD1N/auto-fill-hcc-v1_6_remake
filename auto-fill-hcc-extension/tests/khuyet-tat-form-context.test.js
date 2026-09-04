const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");
const start = source.indexOf("// Các thủ tục cần đối chiếu người yêu cầu");
const end = source.indexOf("\n    setStatus(page", start);

assert.ok(start >= 0 && end > start, "Không tìm thấy khối thu thập formContext");

const contextBlock = source.slice(start, end);
assert.match(
  contextBlock,
  /cfg\.key === "xac-dinh-muc-do-khuyet-tat"/,
  "Thủ tục khuyết tật phải thu tên và CCCD người nộp từ UI trước khi gọi backend",
);
assert.match(
  contextBlock,
  /action:\s*"collectFormContext"/,
  "Khối thủ tục phải gọi content script để thu formContext",
);

console.log("khuyet tat requester form context collection passed");
