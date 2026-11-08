// Khôi phục hồ sơ đang làm dở (supportsResume): BE gợi ý khi chọn lại đúng thủ tục rồi đưa lại giấy tờ + dữ liệu từng
// bước bằng các lệnh sẵn có — resume_upload_session (gắn lại phiên giấy tờ cũ), fill_owner_fields, fill_fields,
// attach_plan. Extension chỉ khai cờ; các lệnh trên mà mất thì khôi phục hỏng lặng lẽ. BE: chat/resume/.
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const strip = (src) => src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const sidebar = strip(fs.readFileSync(path.resolve(__dirname, "..", "sidebar.js"), "utf8"));

test("sidebar khai supportsResume", () => {
  assert.match(sidebar, /supportsResume: true/);
});

test("lệnh BE dùng để khôi phục vẫn được sidebar xử lý", () => {
  assert.match(sidebar, /a\.type === "resume_upload_session" && a\.session_id[\s\S]{0,400}setUploadSession\(a\.session_id\)[\s\S]{0,80}subscribeUploadSession\(a\.session_id\)/);
  for (const type of ["fill_owner_fields", "fill_fields", "attach_plan"]) {
    assert.match(sidebar, new RegExp(`a\\.type === "${type}"`), type);
  }
});

test("bấm sang bước sau: đọc ô chủ hồ sơ TRƯỚC khi bấm rồi gửi kèm báo cáo", () => {
  assert.match(sidebar, /a\.type === "guided_click_next"[\s\S]{0,300}a\.readOwnerFields[\s\S]{0,200}runGuidedNext\(phase, expect, ownerFields\)/);
  const run = sidebar.slice(sidebar.indexOf("async function runGuidedNext("));
  const read = run.indexOf('action: "readOwnerFields", fields: ownerFields');
  const press = run.indexOf('action: "guidedClickNext"');
  assert.ok(read > 0 && read < press, "sang bước sau là form chủ hồ sơ không còn để đọc");
  assert.match(run.slice(0, run.indexOf("async function", 10)),
    /guided_step_report[\s\S]{0,200}ownerFields: owner\.values/);
});
