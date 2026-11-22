// Cổng DVC quốc gia mới: chọn "Bản thân" thì cổng chép giấy tờ tùy thân / nơi cư trú của tài khoản vào khối người được
// cấp rồi KHOÁ các ô đó. BE gửi khối này với onlyIfEmpty → ô đã có giá trị phải "giữ nguyên" (kept) TRƯỚC khi xét ô chỉ
// đọc; xét chỉ đọc trước thì ô đúng giá trị bị báo "không điền được" và tô đỏ.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const src = fs.readFileSync(path.join(__dirname, "..", "content", "surveyjs-main.js"), "utf8")
  .replace(/\/\/[^\n]*/g, "");

test("setOne: ô onlyIfEmpty đã có giá trị được giữ nguyên trước khi chặn ô chỉ đọc", () => {
  const start = src.indexOf("async function setOne(");
  assert.ok(start >= 0, "không thấy setOne");
  const body = src.slice(start, src.indexOf("\n  }\n", start));
  const keep = body.indexOf("field.onlyIfEmpty && !q.isEmpty?.()");
  const readonly = body.indexOf("q.isReadOnly");
  assert.ok(keep > 0 && readonly > 0, "thiếu nhánh giữ nguyên hoặc nhánh chỉ đọc");
  assert.ok(keep < readonly, "nhánh giữ nguyên phải đứng trước nhánh chỉ đọc");
  assert.match(body, /if \(q\.isReadOnly\) return \{ ok: false, reason: "readonly" \};/,
    "ô chỉ đọc mà còn trống vẫn phải báo không điền được");
});
