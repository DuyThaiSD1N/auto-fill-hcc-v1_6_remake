// Cổng hiện toast "Upload thất bại (File Service)…" / "Tải lên tài liệu thất bại, vui lòng thử lại"
// → hoãn tệp NGAY, ĐÓNG toast rồi mới sang tệp kế (toast treo làm tệp kế bị hiểu nhầm là hỏng),
// báo cán bộ một lần, và thử lại chỉ chờ phần còn thiếu kể từ lần hỏng gần nhất.
// Đồng bộ bản Handfree (tro-ly-nguoi-dan-extension/content/attach-core.js).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const content = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");

test("chỉ khớp đúng câu tải-tệp-thất-bại của cổng", () => {
  const src = content.match(/const UPLOAD_FAILURE_RE = (\/.+\/i);/);
  assert.ok(src, "thiếu UPLOAD_FAILURE_RE");
  const re = eval(src[1]); // eslint-disable-line no-eval
  assert.ok(re.test("Upload thất bại (File Service): Upload failed: 500 Internal Server Error"));
  assert.ok(re.test("Tải lên tài liệu thất bại, vui lòng thử lại"));
  assert.ok(re.test("Thông báo Không tải được file hoặc lưu thất bại."));
  assert.ok(!re.test("Lưu thất bại"));
  assert.ok(!re.test("Lời nhắn: vui lòng kiểm tra lại"));
  assert.ok(!re.test("Lệ phí 1.500.000 đồng"));
  assert.ok(!re.test("Có lỗi xảy ra"));
});

test("toast cũ còn treo không bị tính cho tệp mới (so theo nội dung với mốc)", () => {
  assert.match(content, /if \(!seen\.has\(foldChoiceText\(hit\.text\)\)\) return hit\.text;/);
});

test("mã hoãn sớm KHÔNG thuộc nhóm reload của chế độ tách", () => {
  const set = content.slice(content.indexOf("const SPLIT_RELOADABLE_WALLET_CODES"));
  assert.ok(!set.slice(0, set.indexOf("]);")).includes("wallet-upload-rejected"));
  assert.match(content, /code: "wallet-upload-rejected"/);
});

test("đóng toast + báo trước khi sang tệp kế, ở cả hai nhánh hỏng do cổng", () => {
  assert.equal((content.match(/await dismissUploadFailureToasts\(\);[^\n]*\n\s*announceRetry\(round\);/g) || []).length, 2);
  assert.match(content, /if \(retryAnnounced \|\| round >= MAX_ROUNDS\) return;/);
});

test("MỌI nhánh hoãn đều ghi mốc hỏng; thử lại chờ phần còn thiếu", () => {
  const loop = content.slice(content.indexOf("const MAX_ROUNDS = 3"));
  const body = loop.slice(0, loop.indexOf("queue = deferred;"));
  assert.equal((body.match(/lastFailAt = Date\.now\(\);/g) || []).length, 4);
  assert.equal((body.match(/deferred\.push\(/g) || []).length, 4);
  assert.match(content, /if \(backoffMs\) await sleep\(backoffMs\);/);
});

test("vòng chờ tên tệp chỉ bị cắt bởi uploadFailed và vẫn probe lần cuối", () => {
  const fn = content.slice(content.indexOf("async function waitForPersistedAttachment"));
  const body = fn.slice(0, fn.indexOf("\n  }\n"));
  assert.match(body, /if \(uploadFailed\?\.\(\)\) break;[\s\S]*return probe\(\);/);
});
