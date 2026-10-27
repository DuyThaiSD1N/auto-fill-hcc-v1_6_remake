// Cổng DVC quốc gia mới (SurveyJS): chỉ MỘT engine điền + đính kèm (content/fill-surveyjs.js +
// content/surveyjs-main.js). Merge từng để lại engine thứ hai chặn trước engine chung và một dòng
// toán tử ba ngôi trùng làm content.js lỗi cú pháp — mọi cổng mất extension.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");

test("content.js biên dịch được", () => {
  assert.doesNotThrow(() => new vm.Script(read("content.js"), { filename: "content.js" }));
});

test("chỉ một engine SurveyJS: điền + đính kèm đi qua fill-surveyjs.js", () => {
  const content = read("content.js");
  const manifest = JSON.parse(read("manifest.json"));
  const scripts = manifest.content_scripts.flatMap((entry) => entry.js);
  assert.ok(scripts.includes("content/fill-surveyjs.js"));
  assert.ok(scripts.includes("content/surveyjs-main.js"));
  assert.ok(!scripts.includes("content/fill-survey-main.js"));
  assert.match(content, /formKind === "surveyjs" \? H\.fillFormSurveyJs/);
  assert.match(content, /detectFormKind\(\) === "surveyjs" && typeof H\.attachSurveyJsByPlan === "function"/);
  assert.doesNotMatch(content, /return "survey";/);
  assert.doesNotMatch(content, /attachDvcqgByPlan\(/);
});
