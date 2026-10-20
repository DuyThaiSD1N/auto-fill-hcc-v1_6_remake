// Trang nộp một trang — luồng bản 2: thẻ tiến trình nhiều bước do BE điều khiển (pipeline_steps), tắt chú giải màu
// cũ (noLegend), và báo BE mỗi khi số ô trống đổi lúc công dân tự gõ trên cổng (__event:field_review_status).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8").replace(/^\s*\/\/.*$/gm, "");
const sidebar = read("sidebar.js");
const css = fs.readFileSync(path.join(root, "sidebar.css"), "utf8");
const adapter = read("content/field-review-surveyjs.js");
const main = read("content/surveyjs-main.js");

test("sidebar khai cờ luồng bản 2", () => {
  assert.match(sidebar, /supportsFlowV2: true,/);
});

test("action pipeline_steps dựng / cập nhật thẻ tiến trình tại chỗ", () => {
  assert.match(sidebar, /\} else if \(a\.type === "pipeline_steps"\) \{\s*renderStepsCard\(a\);/);
  assert.match(sidebar, /if \(Array\.isArray\(a\.steps\) && a\.steps\.length\) \{/);
  assert.match(sidebar, /const state = done \|\| i < active \? "done" : i === active \? \(failed \? "failed" : "active"\) : "todo";/);
  assert.match(sidebar, /`✅ Đã hoàn thành \$\{total\} bước`/);
});

test("thanh tiến trình không tự đầy trước mốc thật", () => {
  assert.match(sidebar, /const ceiling = \(100 \* \(active \+ 1\)\) \/ total - 4;/);
  assert.match(sidebar, /if \(done\) \{\s*stepsBarTo\(100\);/);
});

test("có thẻ nhiều bước thì không dựng card một dòng cũ; về bước nhận giấy tờ thì thẻ báo lỗi", () => {
  assert.match(sidebar, /if \(\(d\.actions \|\| \[\]\)\.some\(\(a\) => a\.type === "pipeline_steps"\)\) return;/);
  assert.match(sidebar, /if \(st === "collecting_docs" \|\| st === "qr_waiting"\) failStepsCard\(\);/);
});

test("noLegend tắt chú giải màu đếm từ payload", () => {
  assert.match(sidebar, /if \(!a\.noLegend\) renderFillLegend\(a\.fields, res\);/);
});

test("các khung nối tiếp của thẻ tiến trình xếp hàng lời đọc, không cắt câu trước", () => {
  assert.match(sidebar, /const stepsTail = \(d\.actions \|\| \[\]\)\.some\(\(a\) => a\.type === "pipeline_steps"\);/);
  assert.match(sidebar, /\|\| stepsTail\s*\|\| voiceCfg\?\.finishSentenceBeforeNext === true\);/);
});

test("công dân tự gõ trên form: MAIN world báo đổi giá trị, content đếm lại + tô lại, sidebar báo BE", () => {
  assert.match(main, /survey\.onValueChanged\.add\(\(\) => document\.dispatchEvent\(new CustomEvent\(CHANGED_EVENT\)\)\);/);
  assert.match(main, /payload\.op === "reviewWatch"\) result = reviewWatch\(\);/);
  assert.match(adapter, /await watch\(msg\);\s*sendResponse\(\{ ok: true, stats \}\);/);
  assert.match(adapter, /const \{ stats \} = await markAll\(watchRules\);\s*if \(lastStatsKey === before\) return;/);
  assert.match(adapter, /chrome\.runtime\.sendMessage\(\{ __tlnd: "fieldReviewStats", stats \}/);
  assert.match(sidebar, /msg\?\.__tlnd !== "fieldReviewStats" \|\| String\(sender\?\.tab\?\.id \|\| ""\) !== String\(TAB_ID\)/);
  assert.match(sidebar, /ask\(`__event:field_review_status:\$\{JSON\.stringify\(\{ stats: msg\.stats \}\)\}`, "system"\);/);
});

test("thẻ tiến trình có hiệu ứng và tắt khi máy đặt giảm chuyển động", () => {
  assert.match(css, /\.steps-item\[data-state="active"\] \.steps-ic::before \{/);
  assert.match(css, /@keyframes steps-pop/);
  assert.match(css, /@keyframes steps-sheen/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\) \{[\s\S]*\.steps-orb, \.steps-bar > i::after/);
});

test("tờ khai form cũ (eForm): công dân tự gõ thì tô lại màu, đếm lại và báo sidebar khi số ô đổi", () => {
  const legacy = read("content/field-review.js");
  assert.match(legacy, /document\.addEventListener\("input", onFormEdited, true\);/);
  assert.match(legacy, /document\.addEventListener\("change", onFormEdited, true\);/);
  assert.match(legacy, /if \(!watchRequired \|\| !document\.querySelector\(SLOT_SELECTOR\)\) return;/);
  assert.match(legacy, /const \{ stats \} = markAll\(watchRequired\);\s*if \(lastStatsKey === before\) return;/);
  assert.match(legacy, /watchRequired = msg\.required \|\| \[\];/);
  assert.match(legacy, /chrome\.runtime\.sendMessage\(\{ __tlnd: "fieldReviewStats", stats \}/);
});

test("requiredFirst: tìm ô kế tiếp lấy ô bắt buộc trống trước, rồi mới tới ô không bắt buộc (cả eForm lẫn SurveyJS)", () => {
  const legacy = read("content/field-review.js");
  assert.match(legacy, /\|\| \(msg\.requiredFirst && list\.find\(\(s\) => !s\.value\(\) && s\.required && !skip\.has\(s\.key\)\)\)\s*\|\| list\.find\(\(s\) => !s\.value\(\) && !skip\.has\(s\.key\)\);/);
  assert.match(adapter, /\|\| \(msg\.requiredFirst && list\.find\(\(x\) => !x\.value && x\.required && !skip\.has\(x\.name\)\)\)\s*\|\| list\.find\(\(x\) => !x\.value && !skip\.has\(x\.name\)\);/);
});
