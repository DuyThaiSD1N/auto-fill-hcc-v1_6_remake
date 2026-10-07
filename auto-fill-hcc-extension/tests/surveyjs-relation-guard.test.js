// Trích lục / cải chính (Cổng DVC quốc gia mới): khối người được cấp khai resetValueIf theo ô "Quan hệ…"
// → mỗi lần đổi quan hệ, SurveyJS xoá trắng khối. Engine chụp rồi ghi lại khối; khai sinh / khai tử không đụng.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const src = fs.readFileSync(path.join(__dirname, "..", "content", "surveyjs-main.js"), "utf8");

test("chỉ giữ khối cho ô quan hệ của trích lục và cải chính", () => {
  assert.match(src, /const RELATION_GUARD_NAMES = \["citizenQuanhe", "citizenQuanhevsngcaichinhhotich1"\];/);
  assert.doesNotMatch(src, /RELATION_GUARD_NAMES = \[[^\]]*(citizenmoiquanhe|Quanhevoinguoiduockhaisinh)/);
});

test("khối lấy đúng các ô có resetValueIf trỏ tới ô quan hệ", () => {
  assert.match(src, /String\(q\.resetValueIf \|\| ""\)\.includes\(`\{\$\{relation\.name\}\}`\)/);
});

test("đổi sang Bản thân thì lưu ảnh; rời Bản thân ghi lại đúng ảnh, không có ảnh thì để cổng xoá", () => {
  assert.match(src, /if \(isSelf\(opt\.value\) && !isSelf\(opt\.oldValue\)\) beforeSelf = pending\.snap;/);
  assert.match(src, /if \(!change \|\| isSelf\(opt\.value\)\) return;/);
  assert.match(src, /if \(isSelf\(change\.from\)\) \{\s*snap = beforeSelf;\s*beforeSelf = null;\s*if \(!snap\) return;/);
});

test("lượt điền của engine không bị chụp / ghi lại", () => {
  assert.match(src, /toolWriting = true;\s*try \{\s*return await setValuesCore\(survey, fields\);\s*\} finally \{\s*toolWriting = false;/);
  assert.match(src, /if \(toolWriting\) \{ pending = null; return; \}/);
});
