// Cổng DVC quốc gia mới hiện tên tệp lên dòng ngay khi bắt đầu tải; tải hỏng giữ dòng đỏ, và nạp chồng lúc tệp trước
// đang tải thì cổng bỏ qua tệp mới hoặc để dòng kẹt "đang tải" không fileId → tên tệp không đủ làm bằng chứng.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const strip = (src) => src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const main = strip(fs.readFileSync(path.join(root, "content/surveyjs-main.js"), "utf8"));
const fill = strip(fs.readFileSync(path.join(root, "content/fill-surveyjs.js"), "utf8"));

test("MAIN world đọc trạng thái tải từ props React và xoá dòng tệp theo trạng thái", () => {
  assert.match(main, /memoizedProps\?\.fileInfo/);
  assert.match(main, /info\.uploadStatus/);
  assert.match(main, /payload\.op === "uploadStatus"/);
  assert.match(main, /payload\.op === "removeUploads"/);
  assert.match(main, /statuses\.includes\(e\.status\)/);
  // DOM chỉ trỏ một trong hai bản fiber (current/alternate) → phải xét cả bản kia, không thì đọc ra trạng thái cũ.
  assert.match(main, /f\.alternate\?\.memoizedProps\?\.fileInfo/);
});

test("tải TỪNG tệp: chờ trạng thái thật trước tệp kế; kẹt thì xoá, nạp lại một lần; hỏng thì báo, không ghi nhớ", () => {
  const verify = fill.indexOf("let outcome = ok ? await uploadOutcome(file.name, firstTicks)");
  const retry = fill.indexOf('if (outcome === "timeout") {');
  const fail = fill.indexOf('if (outcome === "error" || outcome === "timeout") {');
  const remember = fill.indexOf("rememberAttached({ hash, name: file.name, row: rowKey })");
  assert.ok(verify > 0 && retry > verify && fail > retry && remember > fail, "kiểm → nạp lại → báo lỗi → mới ghi nhớ");
  assert.match(fill, /op: "removeUploads", name: file\.name, statuses: \["pending", "uploading"\]/);
  // Lý do theo toast cổng: chỉ toast nói dung lượng mới báo dung lượng; "Upload file thất bại" thì không.
  assert.match(fill, /toastsBefore\.has\(msg\)\) \|\| ""/);
  assert.match(fill, /tệp quá lớn \(cổng chỉ nhận tệp dưới 2 MB\)/);
  assert.match(fill, /đính kèm file thất bại/);
  assert.doesNotMatch(fill, /thường do tệp quá lớn/);
  assert.match(fill, /cổng không ghi nhận tệp sau khi tải/);
  assert.match(fill, /op: "removeUploads", statuses: \["error", "pending", "uploading"\] \}, 30000/);
  assert.match(fill, /if \(!last\) return "unknown";/);
  assert.doesNotMatch(fill, /uploading\.push\(/);
});
