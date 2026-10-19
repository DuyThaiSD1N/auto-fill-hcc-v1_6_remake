// Trang nộp hồ sơ mới (SurveyJS) — ENGINE NHẸ cho máy quầy cấu hình thấp (5 thủ tục khai sinh, khai tử, trích lục,
// cải chính, xác nhận TTHN): không lướt từng ô, điền xong nhảy thẳng tới ô đỏ đầu tiên; đính nhảy tới dòng đang tải,
// xong cả lượt về đầu trang; không cuộn mượt. MAIN world tắt hiệu ứng survey và chờ khung hình thay vì mốc giờ.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const read = (file) => fs.readFileSync(path.join(__dirname, "..", file), "utf8");
const src = read("content/fill-surveyjs.js");
const main = read("content/surveyjs-main.js");
const fill = src.slice(src.indexOf("async function fillFormSurveyJs("), src.indexOf("function uploadRows()"));
const attach = src.slice(src.indexOf("async function attachSurveyJsByPlan("), src.indexOf("function readSurveyJsValue("));

test("điền: không lướt từng ô, dò ô một lần cho cả lượt, xong nhảy tới ô đỏ đầu tiên", () => {
  assert.doesNotMatch(src, /followDelay|FOLLOW_TOTAL_MS/);
  assert.match(fill, /const find = questionIndex\(\);/);
  assert.match(fill, /markField\(field, r\.ok, find\);\s*\}/);
  assert.match(fill, /followTo\(document\.querySelector\(`\[\$\{MARK_ATTR\}="not-filled"\]`\)\);\s*return result;/);
  assert.match(src, /el\?\.scrollIntoView\?\.\(\{ block: "center", behavior: "auto" \}\)/);
  assert.doesNotMatch(src, /behavior: "smooth"/);
});

test("đính kèm: nhảy tới dòng trước khi tải lên, dò trạng thái mỗi 400 ms; xong cả lượt thì về đầu trang", () => {
  assert.match(attach, /followTo\(row\);\s*await sleep\(250\);[^\n]*\n\s*let portalError = "";/);
  assert.match(attach, /finally \{\s*await callMain\(\{ op: "suppressPicker", on: false \}, 5000\);\s*backToTop\(\);/);
  assert.match(src, /window\.scrollTo\(\{ top: 0, behavior: "auto" \}\)/);
  assert.match(src, /const UPLOAD_TICK_MS = 400;/);
  // Tổng thời gian chờ mỗi tệp giữ như cũ: 10 giây + 5 giây mỗi MB, trần 60 giây.
  assert.match(attach, /Math\.min\(60000, 10000 \+ sizeMb \* 5000\) \/ UPLOAD_TICK_MS/);
});

test("không còn công tắc / nhánh chế độ: engine nhẹ là engine duy nhất", () => {
  assert.doesNotMatch(src, /liteMode|LITE_MODE_KEY|\blite\b/);
  assert.doesNotMatch(main, /liteRun|payload\.lite/);
  assert.doesNotMatch(read("settings.js"), /lite_mode|LiteMode/);
  assert.doesNotMatch(read("settings.html"), /sjsLiteModeSetting/);
});

test("MAIN world: tắt hiệu ứng survey trong lượt điền, chờ khung hình sau mỗi ô chọn", () => {
  assert.match(main, /const resumeAnimations = pauseAnimations\(survey\);/);
  assert.match(main, /toolWriting = false;\s*resumeAnimations\?\.\(\);/);
  assert.match(main, /field\.comp === "sjs-radio"\)\) await settle\(150\);/);
  assert.match(main, /requestAnimationFrame/);
  // Khối địa chỉ: chờ tới khi ô tỉnh hiện (trần 3 giây), không đoán mốc giờ.
  assert.match(main, /while \(!ready\(candidates\) && Date\.now\(\) - t0 < 3000\);/);
});
