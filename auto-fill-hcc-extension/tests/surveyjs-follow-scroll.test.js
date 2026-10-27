// Trang nộp hồ sơ mới (SurveyJS): trang phải CUỘN THEO việc trợ lý đang làm — điền tới ô nào cuộn
// tới ô đó, đính dòng nào cuộn tới dòng đó, đính xong cả lượt thì về đầu trang.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const src = fs.readFileSync(path.join(__dirname, "..", "content", "fill-surveyjs.js"), "utf8");
const fill = src.slice(src.indexOf("async function fillFormSurveyJs("), src.indexOf("function uploadRows()"));
const attach = src.slice(src.indexOf("async function attachSurveyJsByPlan("), src.indexOf("function readSurveyJsValue("));

test("điền: lướt qua từng ô vừa điền, cả lượt tối đa ~3 giây", () => {
  assert.match(fill, /const delay = followDelay\(fields\.length\);/);
  assert.match(fill, /markField\(field, r\.ok\);\s*followTo\(questionEl\(field\.name\)\);\s*await sleep\(delay\);/);
  assert.match(src, /const FOLLOW_TOTAL_MS = 3000;/);
  assert.match(src, /el\?\.scrollIntoView\?\.\(\{ block: "center", behavior: "smooth" \}\)/);
});

test("đính kèm: cuộn tới dòng trước khi tải lên; xong cả lượt thì về đầu trang", () => {
  assert.match(attach, /followTo\(row\);\s*await sleep\(250\);[^\n]*\n\s*let portalError = "";/);
  assert.match(attach, /finally \{\s*await callMain\(\{ op: "suppressPicker", on: false \}, 5000\);\s*backToTop\(\);/);
  assert.match(src, /window\.scrollTo\(\{ top: 0, behavior: "smooth" \}\)/);
});
