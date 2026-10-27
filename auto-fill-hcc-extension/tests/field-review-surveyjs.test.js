// Bổ sung ô còn trống trên trang nộp một trang (Cổng DVC quốc gia mới, form SurveyJS): cùng giao thức
// fieldReview* với tờ khai eForm nhưng đọc/ghi qua model survey ở MAIN world.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8").replace(/^\s*\/\/.*$/gm, "");
const adapter = read("content/field-review-surveyjs.js");
const main = read("content/surveyjs-main.js");
const legacy = read("content/field-review.js");
const sidebar = read("sidebar.js");

test("manifest nạp bộ bổ sung ô SurveyJS sau engine trang một trang", () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));
  const js = manifest.content_scripts.find((c) => c.js.includes("content/fill-surveyjs.js")).js;
  assert.ok(js.indexOf("content/field-review-surveyjs.js") > js.indexOf("content/fill-surveyjs.js"));
  assert.ok(js.indexOf("content/field-review-surveyjs.js") > js.indexOf("content/field-review.js"));
});

test("sidebar khai cờ và chuyển nguyên bộ quy tắc ô của BE cho cả lượt tô lẫn lượt tìm ô", () => {
  assert.match(sidebar, /supportsFieldReviewSurvey: true,/);
  assert.match(sidebar, /sendToContent\(\{ \.\.\.a\.fieldReview, action: "fieldReviewMark" \}\)/);
  assert.match(sidebar, /sendToContent\(\{ \.\.\.a, action: "fieldReviewNext" \}\)/);
});

test("ô cổng để sẵn 0 (số lượng bản sao): còn 0 mà công dân chưa trả lời thì tô đỏ và hỏi", () => {
  assert.match(adapter, /zero\.has\(baseName\(q\.name\)\) && q\.value !== "" && Number\(q\.value\) === 0 && !answered\.has\(q\.name\)\) q\.value = "";/);
  assert.match(adapter, /if \(ok\) answered\.add\(msg\.apply\.key\);/);
});

test("chỉ form SurveyJS trả lời; tờ khai eForm vẫn do field-review.js", () => {
  assert.match(adapter, /if \(H\.detectFormKind\?\.\(\) !== "surveyjs" \|\| typeof H\.callSurveyJs !== "function"\) return;/);
  assert.match(legacy, /if \(H\.detectFormKind\?\.\(\) !== "legacy" \|\| !document\.querySelector\(SLOT_SELECTOR\)\) return;/);
  assert.match(legacy, /H\.fieldReviewPointer = \{ focus: focusBox, unfocus \};/);
});

test("chỉ hỏi câu đang hiện, sửa được; câu ẩn của model (visible:false) và ô khoá không tính", () => {
  assert.match(main, /if \(!node\.getClientRects\(\)\.length\) continue;/);
  assert.match(main, /if \(!q \|\| seen\.has\(q\.name\) \|\| !q\.isVisible \|\| q\.isReadOnly\) continue;/);
  assert.match(main, /required: !!q\.isRequired \|\| labelMarksRequired\(q\),/);
  assert.match(adapter, /filter\(\(q\) => !skip\.has\(baseName\(q\.name\)\)\)/);
});

test("ba lệnh MAIN world của vòng bổ sung có trong bộ điều phối", () => {
  assert.match(main, /payload\.op === "reviewList"\) result = reviewList\(\);/);
  assert.match(main, /payload\.op === "reviewChoices"\) result = await reviewChoices\(/);
  assert.match(main, /payload\.op === "reviewSet"\) \{/);
});

test("danh sách Xã rỗng: bấm Làm mới, rồi chọn lại tỉnh; vẫn rỗng thì báo tỉnh cho BE mời tải lại", () => {
  assert.match(main, /querySelector\('button\[title="Làm mới"\]'\)/);
  assert.match(main, /province\.value = undefined;\s*await sleep\(300\);\s*province\.value = value;/);
  assert.match(adapter, /\.\.\.\(province \? \{ optionsFailed: true, province \} : \{\}\)/);
});

test("tô màu và viền ô đang hỏi bằng thuộc tính (React vẽ lại là ghi đè class)", () => {
  assert.match(adapter, /const MARK_ATTR = "data-tlnd-mark";/);
  assert.match(adapter, /el\.setAttribute\(ASKING_ATTR, "1"\);/);
  assert.match(adapter, /const kind = q\.value \? "filled" : q\.required \? "not-filled" : "optional";/);
});

test("ô ngày dạng chữ (khai tử): báo BE là ô ngày nhận tháng-năm / năm, ghi vào cổng dạng chữ", () => {
  assert.match(adapter, /if \(q\.kind === "text" && textDates\.has\(baseName\(q\.name\)\)\) \{ q\.kind = "date"; q\.textDate = true; \}/);
  assert.match(adapter, /partialDate: !!q\.textDate,/);
  assert.match(adapter, /kind: target\.textDate \? "text" : target\.kind,/);
});

test("ô tra cứu CSDL: điền xong chờ cổng đổ dữ liệu rồi mới tìm ô kế tiếp", () => {
  assert.match(adapter, /const LOOKUP_WAIT_MS = 2500;/);
  assert.match(adapter, /await sleep\(lookup \? LOOKUP_WAIT_MS : 350\);/);
});
