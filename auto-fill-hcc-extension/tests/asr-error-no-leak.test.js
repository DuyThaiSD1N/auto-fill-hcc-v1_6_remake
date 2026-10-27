// Sidebar không được hiện nguyên văn lỗi máy chủ ASR (có thể chứa địa chỉ dịch vụ nội bộ).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const asr = fs.readFileSync(path.join(__dirname, "..", "services", "asr.js"), "utf8");

test("lỗi ASR từ máy chủ → câu cố định, không dùng msg.message", () => {
  const i = asr.indexOf('msg.type === "error"');
  const block = asr.slice(i, i + 400);
  assert.ok(i > 0);
  assert.ok(!/msg\.message/.test(block), "không được đưa msg.message ra màn hình");
  assert.match(block, /name: "AsrError", message: "Dịch vụ nhận giọng nói đang gặp sự cố/);
});
