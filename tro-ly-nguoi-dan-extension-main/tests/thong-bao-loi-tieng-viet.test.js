const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const config = fs.readFileSync(path.join(root, "api", "config.js"), "utf8");

// Chạy thật viError / viMicError (hai hàm chỉ dùng chính chúng + console).
const src = ["viError", "viMicError"]
  .map((name) => sidebar.match(new RegExp(`function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n  \\}`))[0])
  .join("\n");
// eslint-disable-next-line no-new-func
const { viError, viMicError } = new Function("console", `${src}; return { viError, viMicError };`)({ warn() {} });
const tiengViet = (s) => /[^\x00-\x7F]/.test(s);

test("lỗi mạng / máy chủ tiếng Anh → câu tiếng Việt kèm việc cần làm", () => {
  const cases = [
    new DOMException("signal is aborted without reason", "AbortError"),
    new DOMException("Hết thời gian chờ máy chủ", "TimeoutError"),
    new TypeError("Failed to fetch"),
    new Error("HTTP 413"),
    new Error("HTTP 502"),
    new Error("HTTP 401"),
    new Error("Something odd"),
  ];
  for (const e of cases) {
    const out = viError(e);
    assert.ok(tiengViet(out), `${e.name}: ${e.message} → ${out}`);
    assert.doesNotMatch(out, /signal|fetch|HTTP|aborted/i);
  }
  assert.match(viError(new DOMException("signal is aborted without reason", "AbortError")), /quá lâu/);
  assert.match(viError(new Error("HTTP 413")), /quá lớn/);
});

test("câu đã là tiếng Việt (máy chủ trả) giữ nguyên", () => {
  assert.equal(viError(new Error("Tệp a.pdf vượt 50MB.")), "Tệp a.pdf vượt 50MB.");
});

test("lỗi micro của trình duyệt → câu tiếng Việt đúng tình huống", () => {
  assert.match(viMicError("NotFoundError", "Requested device not found"), /Không tìm thấy micro/);
  assert.match(viMicError("NotReadableError", "Could not start audio source"), /ứng dụng khác/);
  assert.match(viMicError("OverconstrainedError", "x"), /micro khác/);
  assert.equal(viMicError("WsError", "Mất kết nối dịch vụ nhận giọng nói."), "Mất kết nối dịch vụ nhận giọng nói.");
  assert.ok(tiengViet(viMicError("SomethingNew", "weird english")));
});

test("các chỗ báo lỗi không còn in nguyên câu tiếng Anh; tải tệp chờ 5 phút", () => {
  assert.doesNotMatch(sidebar, /Tải tệp lỗi: \$\{err\?\.message/);
  assert.doesNotMatch(sidebar, /Lỗi giọng nói: \$\{msg\.error/);
  assert.doesNotMatch(sidebar, /Không gọi được trợ lý: \$\{e\?\.message/);
  assert.match(sidebar, /const UPLOAD_TIMEOUT_MS = 5 \* 60 \* 1000;/);
  assert.match(sidebar, /upload-sessions\/\$\{uploadSid\}\/files`,\s*\{ method: "POST", body: fd, timeoutMs: UPLOAD_TIMEOUT_MS \}/);
  assert.match(config, /const \{ timeoutMs = TLND_API_TIMEOUT_MS, \.\.\.rest \} = init;/);
  assert.match(config, /reason\.name = "TimeoutError";\s*ctrl\.abort\(reason\);\s*\}, timeoutMs\);/);
});
